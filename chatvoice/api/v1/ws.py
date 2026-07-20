import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Annotated

import markdown
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse

from ...core.interpreter import Interpreter
from ...core.logger import get_logger
from ...core.security import TokenType, create_ws_session_token, decode_ws_token
from ...sessions.session import ChatSession
from ...transport.ws import WS
from ..dependencies import get_current_user, get_session_transport, get_ws_session

router = APIRouter(tags=["health"])

log = get_logger(__name__)


@router.post("/ws-session/{script}")
async def establish_ws_session(
    script: str,
    request: Request,
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    # Validate script exists to fail fast
    script_path = Path(f"conversations/{script}")
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Script '{script}' not found")

    user_id = current_user["id"]

    # 1. CLEANUP: Kill any previous sessions for this user + script
    request.app.state.transport.cleanup_user_script_sessions(user_id, script)

    # 2. Create new session
    interpreter = Interpreter(
        script_path,
        user_id=user_id,
        settings={"_name_system": "hola"},
        llm_client=request.app.state.llm_client,
    )

    session = request.app.state.transport.create_session(user_id, interpreter)

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


@router.websocket("/ws/{script}")
async def websocket_endpoint(
    websocket: WebSocket,
    script: str,
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
