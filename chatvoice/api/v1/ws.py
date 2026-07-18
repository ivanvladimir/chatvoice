from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, Response
from fastapi.responses import JSONResponse
from datetime import timedelta
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor



from typing import Annotated

from ..dependencies import get_current_user, get_ws_session
from ...core.interpreter import Interpreter
from ...core.security import create_ws_session_token, TokenType
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
async def establish_ws_session(
    script: str,
    request: Request,
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)]
):
    # 1. Generate your token
    interpreter = Interpreter(
        Path(f"conversations/{script}"),
        user_id=current_user['id'],
        settings={"_name_system": "hola"},
        llm_client=request.app.state.llm_client,
    )

    session=request.app.state.transport.create_session(current_user['id'], interpreter)
    ws_token = create_ws_session_token(
        data={
            "sub": session.session_id,     # User's ID
            "username": current_user["username"],
            "type": TokenType.WS_SESSION             # Prevent using this token for normal API routes
        },
        expires_delta=timedelta(minutes=15) # Short lifespan!
    )
 
    response = JSONResponse({"message": "Session created", "status":"ok"})
 
    # 2. Set the cookie with path="/" !!!
    response.set_cookie(
        key="ws_session",  # Whatever your cookie key is
        value=ws_token, 
        path="/",         # <--- THIS IS THE CRITICAL FIX
        httponly=True,
        samesite="lax",
        secure=False # Set to True in production with HTTPS
    )

    return response


# Create a thread pool outside the endpoint
executor = ThreadPoolExecutor(max_workers=4)

@router.websocket("/ws/{script}")
async def websocket_endpoint(
    websocket: WebSocket,
    script: str,
    session: ChatSession = Depends(get_ws_session)
):
    await websocket.accept()
    
    try:
        while True:
            # Run the synchronous blocking function in a thread
            m = await asyncio.get_event_loop().run_in_executor(executor, session.recv)
            
            if m is None:
                break
                
            if m["cmd"] == "say" and len(m['args']) > 0:
                for msg in m['args']:
                    await websocket.send_json({"user":"hola","message": msg})
            
            elif m["cmd"] == "listen":
                # If you need to wait for user input, you MUST use asyncio.wait_for
                # or websocket.receive_text() here, NOT a synchronous input()
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                    session.send(data)
                except asyncio.TimeoutError:
                    pass
                    
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up the session if needed
        pass
