from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.dependencies.paths import (
    RuntimeContext,
    get_default_context,
    get_project_context,
)
from ...utils.markdown import markdown_page

router = APIRouter(tags=["main"])


@router.get("/", response_class=HTMLResponse)
async def main(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
) -> HTMLResponse:
    """Principal"""
    md, notlogged_content = markdown_page("main_notlogged", ctx.content_dir)

    context = {
        "notlogged_content": notlogged_content,
        "metadata": md.Meta,
        "active_page": md.Meta.get("active_page", [None])[0],
        "active_menu": md.Meta.get("active_menu", [None])[0],
    }

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/main.html",
        context=context,
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
) -> HTMLResponse:
    """Profile page: view and edit your own account info."""
    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/profile.html",
        context={
            "active_page": "profile",
            "active_menu": None,
        },
    )


@router.get("/conversations", response_class=HTMLResponse)
async def conversations_page(
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
) -> HTMLResponse:
    """My conversations: past chat sessions the current user has had."""
    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/conversations.html",
        context={
            "active_page": "conversations",
            "active_menu": None,
        },
    )


@router.get("/conversations/{conversation_uuid}", response_class=HTMLResponse)
async def conversation_view(
    request: Request,
    conversation_uuid: UUID,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
) -> HTMLResponse:
    """Read-only transcript of a single past conversation."""
    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/conversation_view.html",
        context={
            "conversation_uuid": conversation_uuid,
            "active_page": "conversations",
            "active_menu": None,
        },
    )


@router.get("/chat/{script}", response_class=HTMLResponse)
@router.get("/chat/{username}/{script}", response_class=HTMLResponse)
async def chat(
    request: Request,
    script: str,
    ctx: RuntimeContext = Depends(get_project_context),  # Single injection
    username: str = None,
) -> HTMLResponse:
    """Chat interface"""

    return ctx.templates_front.TemplateResponse(
        request=request,
        name="user/chatbot.html",
        context={
            "script": script,
            "username": username,
            "active_page": "main",
            "active_menu": None,
            "url_start": request.url_for(
                "establish_ws_session", script=script, username=username
            )
            if username
            else request.url_for("establish_ws_session_", script=script),
            "url_ws": request.url_for(
                "websocket_endpoint", script=script, username=username
            )
            if username
            else request.url_for("websocket_endpoint_", script=script),
            # Configure these from your database or settings
            "chat_room_name": "Consulta",  # Custom room name
            "show_debug": True,  # Disable debug button
            "show_export": False,  # Disable download button
            "enable_user_typing": True,  # Enable typing animation
            "user_typing_speed": 30,  # Speed in ms per character
        },
    )
