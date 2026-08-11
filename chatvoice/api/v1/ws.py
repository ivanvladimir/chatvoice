import asyncio
import json
import uuid as uuid_pkg
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Annotated

import markdown
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.dependencies.paths import RuntimeContext, get_project_context
from ...core.interpreter import Interpreter
from ...core.logger import get_logger
from ...core.security import TokenType, create_ws_session_token, decode_ws_token
from ...crud.conversations import crud_conversation_logs
from ...crud.projects import crud_projects
from ...crud.users import crud_users
from ...schemas.conversation import (
    ConversationLogCreateInternal,
    ConversationLogListItem,
)
from ...sessions.session import ChatSession
from ...transport.ws import WS
from ..dependencies import get_current_user, get_session_transport, get_ws_session

router = APIRouter(tags=["health"])

log = get_logger(__name__)


@router.post("/ws-session/{script}", name="establish_ws_session_")
@router.post("/ws-session/{username}/{script}", name="establish_ws_session")
async def establish_ws_session(
    script: str,
    request: Request,
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
    ctx: Annotated[RuntimeContext, Depends(get_project_context)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    username: str = None,
):
    # Validate script exists to fail fast
    if ctx.default:
        if username:
            script_path = ctx.root / username / script
        else:
            script_path = ctx.root / script
    else:
        script_path = ctx.root

    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Script '{script}' not found")

    user_id = current_user["id"]

    # TODO: Recover settings from environment

    # 1. Resolve the owning Project row (if any -- built-in scripts like
    # hello_world have no Project row) and log this run to the DB.
    project_id = None
    if username:
        owner = await crud_users.get(db, username=username, is_deleted=False)
        if owner:
            project = await crud_projects.get(
                db, project_name=script, owner_id=owner["id"], is_deleted=False
            )
            if project:
                project_id = project["id"]

    session_id = str(uuid_pkg.uuid4())
    conversation_log = await crud_conversation_logs.create(
        db,
        ConversationLogCreateInternal(
            user_id=user_id,
            project_id=project_id,
            script_name=script,
            session_id=session_id,
        ),
        schema_to_select=ConversationLogListItem,
    )

    # 2. Create new session
    interpreter = Interpreter(
        script_path,
        user_id=user_id,
        settings={},
        llm_client=request.app.state.llm_client,
        conversation_log_id=conversation_log["id"] if conversation_log else None,
    )

    # Atomically replaces any existing session for this user+script -- see
    # SessionManager.create_replacing for why this can't be a separate
    # cleanup-then-create pair of calls.
    session = request.app.state.transport.create_session_replacing(
        user_id, script, interpreter, session_id=session_id
    )

    # 3. Generate token & set cookie
    ws_token = create_ws_session_token(
        data={
            "sub": session.session_id,
            "username": current_user["username"],
            "type": TokenType.WS_SESSION,
        },
        expires_delta=timedelta(minutes=15),
    )

    response = JSONResponse(
        {
            "message": "Session created",
            "status": "ok",
            "session_id": session.session_id,
        }
    )

    response.set_cookie(
        key="ws_session",
        value=ws_token,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )

    return response


# Create a thread pool outside the endpoint
executor = ThreadPoolExecutor(max_workers=4)


def tuples_to_json(items, sep=":"):
    """
    Converts a list of (label, value) tuples into a dict.

    - If value is a plain (non-dict) type — string, list, number, bool, etc. —
      it's stored as `label: value`.
    - If value is a dict, it gets flattened *internally* (nested keys joined
      with `sep`), and the result is stored under `label` as usual.

    Example:
        [
            ("a", "hello"),
            ("b", [1, 2, 3]),
            ("c", {"x": 1, "y": {"z": 2, "w": [4, 5]}}),
        ]
        ->
        {
            "a": "hello",
            "b": [1, 2, 3],
            "c": {"x": 1, "y:z": 2, "y:w": [4, 5]},
        }
    """

    def _flatten_dict(d, sep):
        flat = {}

        def _walk(prefix, value):
            for k, v in value.items():
                new_key = f"{prefix}{sep}{k}" if prefix else k
                if isinstance(v, dict):
                    _walk(new_key, v)
                else:
                    flat[new_key] = v

        _walk("", d)
        return flat

    result = {}
    for label, value in items:
        if isinstance(value, dict):
            result[label] = _flatten_dict(value, sep)
        else:
            result[label] = value

    return result


def tuples_to_json_string(items, sep=":", **json_kwargs):
    """Same as above, but returns a JSON string."""
    return json.dumps(tuples_to_json(items, sep=sep), **json_kwargs)


@router.websocket("/ws/{script}", name="websocket_endpoint_")
@router.websocket("/ws/{username}/{script}", name="websocket_endpoint")
async def websocket_endpoint(
    websocket: WebSocket,
    script: str,
    username: str = None,
    session: ChatSession = Depends(get_ws_session),
    transport: "WS" = Depends(get_session_transport),
    ws_session: str | None = Cookie(default=None),
):
    if not session:
        await websocket.close(code=1008, reason="Invalid session")
        return

    await websocket.accept()
    md = markdown.Markdown(extensions=["meta", "tables", "fenced_code", "footnotes"])

    try:
        while True:
            m = await asyncio.get_event_loop().run_in_executor(executor, session.recv)

            if m is None:
                break

            cmd = m.get("cmd")
            args = m.get("args", [])

            if cmd == "say" and args:
                _name_system = session.interpreter.settings.get("_name_user", "System")
                for msg in args:
                    html_msg = md.convert(msg)
                    await websocket.send_json(
                        {"type": "message", "user": _name_system, "message": html_msg}
                    )

            elif cmd == "info" and args:
                json_message = tuples_to_json_string(args)
                await websocket.send_json({"type": "tags", "message": json_message})

            elif cmd == "tag" and args:
                await websocket.send_json(
                    {"type": "divider", "tag": args[0], "message": "\n".join(args[1:])}
                )

            elif cmd == "listen":
                await websocket.send_json({"type": "listen"})
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=60.0
                    )
                    session.send(data)
                except asyncio.TimeoutError:
                    session.send("")

            elif cmd == "error":
                await websocket.send_json(
                    {"type": "error", "message": args[0] if args else "Unknown error"}
                )
                break

    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected: {session.session_id}")
    except Exception as e:
        log.exception(f"Unexpected error in WebSocket: {e}")
    finally:
        # Extract session_id from token for cleanup
        if ws_session:
            payload = decode_ws_token(ws_session)
            if payload and payload.get("sub"):
                transport.remove_session(payload["sub"])
