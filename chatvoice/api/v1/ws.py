from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta
import json
from pathlib import Path


from typing import Annotated, Optional

from ..dependencies import get_current_user, get_ws_user, get_ws_session
from ...core.interpreter import Interpreter
from ...sessions.session import ChatSession

router = APIRouter(tags=["health"])

# --- 1. JWT Configuration 
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS_IN_PRODUCTION"  # Use env vars in production!
ALGORITHM = "HS256"

# Mock database of users
fake_users_db = {
    "alice": {"username": "alice"},
    "bob": {"username": "bob"}
}

@router.post("/ws-session/{script}")
async def create_ws_session(
    request: Request,
    script: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> JSONResponse:

    interpreter = Interpreter(
        Path(f"conversations/{script}"),
        user_id=current_user['id'],
        settings={"_name_system": "hola"},
        llm_client=request.app.state.llm_client,
    )
    session=request.app.state.transport.create_session(current_user['id'], interpreter)
    
    response = JSONResponse({"message": "Session created"})
    # Set the opaque token as an httpOnly cookie
    response.set_cookie(
        key="ws_session", 
        value=session.session_id, 
        httponly=True, 
        samesite="strict",
        secure=False # Set to True in production with HTTPS
    )
    return response

@router.websocket("/ws/{script}")
async def websocket_endpoint(
    websocket: WebSocket,
    script: str,
    session: ChatSession = Depends(get_ws_session) # Inject the dependency
):
    # If we reach this line, Depends() succeeded. NOW we accept the connection.
    await websocket.accept()
    
    try:
        while True:
            m = session.recv()
            if m is None:
                return
            if m["cmd"] == "say" and len(m['args']) > 0:
                for msg in m['args']:
                    await websocket.send_json({"user_id": user_id, "message": msg})
            elif m["cmd"] == "listen":
                pass
                #input=self.console.input(f"[red]{interpreter.settings['_name_user']}[/]: ")
                #session.send(input)
            elif m["cmd"] == "info" and len(m['args']) > 0:
                for label,info in m['args']:
                    await websocket.send_json({"user_id": 1, "message": f"{label: <10}: {info}"})
 
            
    except WebSocketDisconnect:
        # Optional: Clean up session on disconnect if you want it to be single-use
        # del active_sessions[ws_session] 
        pass
