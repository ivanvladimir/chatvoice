from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Request,
    Response,
)
from fastapi.responses import JSONResponse
from datetime import timedelta
from pathlib import Path
import asyncio
import markdown
import json
from concurrent.futures import ThreadPoolExecutor


from typing import Annotated

from ..dependencies import get_current_user, get_ws_session
from ...core.interpreter import Interpreter
from ...core.security import create_ws_session_token, TokenType
from ...sessions.session import ChatSession

router = APIRouter(tags=["health"])


# --- 1. JWT Configuration
SECRET_KEY = (
    "YOUR_SUPER_SECRET_KEY_CHANGE_THIS_IN_PRODUCTION"  # Use env vars in production!
)
ALGORITHM = "HS256"

# Mock database of users
fake_users_db = {"alice": {"username": "alice"}, "bob": {"username": "bob"}}


@router.post("/ws-session/{script}")
async def establish_ws_session(
    script: str,
    request: Request,
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    # 1. Generate your token
    interpreter = Interpreter(
        Path(f"conversations/{script}"),
        user_id=current_user["id"],
        settings={"_name_system": "hola"},
        llm_client=request.app.state.llm_client,
    )

    session = request.app.state.transport.create_session(
        current_user["id"], interpreter
    )
    ws_token = create_ws_session_token(
        data={
            "sub": session.session_id,  # User's ID
            "username": current_user["username"],
            "type": TokenType.WS_SESSION,  # Prevent using this token for normal API routes
        },
        expires_delta=timedelta(minutes=15),  # Short lifespan!
    )

    response = JSONResponse({"message": "Session created", "status": "ok"})

    # 2. Set the cookie with path="/" !!!
    response.set_cookie(
        key="ws_session",  # Whatever your cookie key is
        value=ws_token,
        path="/",  # <--- THIS IS THE CRITICAL FIX
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
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
    websocket: WebSocket, script: str, session: ChatSession = Depends(get_ws_session)
):
    await websocket.accept()
    md = markdown.Markdown(extensions=["meta", "tables", "fenced_code", "footnotes"])
 
    try:
        while True:
            # Run the synchronous blocking function in a thread
            m = await asyncio.get_event_loop().run_in_executor(executor, session.recv)

            if m is None:
                break

            if m["cmd"] == "say" and len(m["args"]) > 0:
                _name_system = session.interpreter.settings['_name_user']
                for msg in m["args"]:
                    html_msg = md.convert(msg)
                    await websocket.send_json({"type": "message", "user": _name_system, "message": html_msg})
            if m["cmd"] == "info" and len(m["args"]) > 0:
                json_message=tuples_to_json_string(m["args"])
                await websocket.send_json({"type": "tags", "message": json_message})
            if m["cmd"] == "tag" and len(m["args"]) > 0:
                await websocket.send_json({"type": "divider", "message": m['args'][0]})
            elif m["cmd"] == "listen":
                # If you need to wait for user input, you MUST use asyncio.wait_for
                # or websocket.receive_text() here, NOT a synchronous input()
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=60.0
                    )
                    session.send(data)
                except asyncio.TimeoutError:
                    pass

    except WebSocketDisconnect:
        pass
    finally:
        # Clean up the session if needed
        pass
