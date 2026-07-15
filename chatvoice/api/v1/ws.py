from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta
import json
from pathlib import Path


from typing import Annotated, Optional

from ..dependencies import get_current_user, get_ws_user
from ...core.interpreter import Interpreter

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

    print(current_user)

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
    username: str = Depends(get_ws_user) # Inject the dependency
):
    # If we reach this line, Depends() succeeded. NOW we accept the connection.
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"user": username, "message": data})
            
    except WebSocketDisconnect:
        # Optional: Clean up session on disconnect if you want it to be single-use
        # del active_sessions[ws_session] 
        pass
