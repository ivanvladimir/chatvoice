import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.dependencies.paths import RuntimeContext, get_default_context
from ...crud.conversations import (
    crud_conversation_documents,
    crud_conversation_logs,
    crud_conversation_turns,
)
from ...crud.projects import crud_projects
from ...crud.users import crud_users
from ...models.conversation import (
    ConversationDocument,
    ConversationLog,
    ConversationTurn,
)
from ...models.project import ProjectMember
from ...models.user import User
from ...schemas.conversation import (
    ConversationDocumentCreateInternal,
    ConversationDocumentRead,
    ConversationLogUpdateInternal,
)
from ...schemas.user import UserBrief
from ...utils.markdown import render_markdown
from ..dependencies import get_current_editor_or_observer, get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _check_conversation_access(
    db: AsyncSession, conversation: dict, current_user: dict
) -> None:
    """
    Raises 403/404 unless current_user had the conversation, or is an
    editor/observer with access to its project. Used to gate viewing the
    transcript and annotating a conversation (tags, documents).
    """
    if conversation["user_id"] == current_user["id"]:
        return

    if current_user["role"] not in ("editor", "observer"):
        raise HTTPException(status_code=403, detail="Not your conversation")

    if not conversation["project_id"]:
        raise HTTPException(status_code=403, detail="Not your conversation")

    project = await crud_projects.get(db, id=conversation["project_id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _check_project_access(db, project, current_user)


async def _attach_documents(db: AsyncSession, conversations: list[dict]) -> None:
    """Attaches a `documents` list (as plain dicts) to each conversation dict, in place."""
    ids = [c["id"] for c in conversations]
    if not ids:
        for conversation in conversations:
            conversation["documents"] = []
        return

    result = await db.execute(
        select(ConversationDocument)
        .where(ConversationDocument.conversation_log_id.in_(ids))
        .order_by(ConversationDocument.created_at)
    )
    documents_by_conversation: dict[int, list[dict]] = {}
    for doc in result.scalars().all():
        documents_by_conversation.setdefault(doc.conversation_log_id, []).append(
            {
                "id": doc.id,
                "title": doc.title,
                "kind": doc.kind,
                "content": doc.content,
                "tags": doc.tags,
                "created_at": doc.created_at,
            }
        )

    for conversation in conversations:
        conversation["documents"] = documents_by_conversation.get(
            conversation["id"], []
        )


@router.post("/mine", response_class=HTMLResponse)
async def list_my_conversations_htmx(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
):
    """HTMX endpoint: lists the current user's own conversations, across all projects."""
    result = await crud_conversation_logs.get_multi(
        db,
        user_id=current_user["id"],
        offset=(page - 1) * items_per_page,
        limit=items_per_page,
        sort_columns=["started_at"],
        sort_orders=["desc"],
    )

    conversations = result.get("data", [])
    for conversation in conversations:
        # Every row here already belongs to current_user (filtered above).
        conversation["can_delete"] = True
    await _attach_documents(db, conversations)
    total_count = result.get("total_count", 0)
    total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/conversations_list.html",
        context={
            "request": request,
            "conversations": conversations,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "items_per_page": items_per_page,
            "list_endpoint": "list_my_conversations_htmx",
            "list_endpoint_kwargs": {},
            "page_title": "Mis conversaciones",
            "empty_message": "Aún no tienes conversaciones.",
            "show_user": False,
        },
    )


async def _check_project_access(
    db: AsyncSession, project: dict, current_user: dict
) -> None:
    """Raises 403 unless current_user owns the project or is a member of it."""
    if project["owner_id"] == current_user["id"]:
        return

    member_stmt = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project["id"],
            ProjectMember.user_id == current_user["id"],
        )
    )
    result = await db.execute(member_stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="You must own this project or be a member to view its conversations.",
        )


@router.post("/project/{project_uuid}", response_class=HTMLResponse)
async def list_project_conversations_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_editor_or_observer),
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
):
    """
    HTMX endpoint: lists ALL conversations for a project (any user who ran
    one), gated to editor/observer role AND project ownership/membership.
    """
    project = await crud_projects.get(db, uuid=project_uuid, is_deleted=False)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _check_project_access(db, project, current_user)

    result = await crud_conversation_logs.get_multi_joined(
        db,
        project_id=project["id"],
        offset=(page - 1) * items_per_page,
        limit=items_per_page,
        sort_columns=["started_at"],
        sort_orders=["desc"],
        join_model=User,
        join_prefix="user_",
        join_schema_to_select=UserBrief,
    )

    conversations = result.get("data", [])
    is_project_owner = project["owner_id"] == current_user["id"]
    for conversation in conversations:
        # The project owner can clean up any conversation in their project;
        # anyone else can only delete their own.
        conversation["can_delete"] = (
            is_project_owner or conversation.get("user_id") == current_user["id"]
        )
    await _attach_documents(db, conversations)
    total_count = result.get("total_count", 0)
    total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/conversations_list.html",
        context={
            "request": request,
            "conversations": conversations,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "items_per_page": items_per_page,
            "list_endpoint": "list_project_conversations_htmx",
            "list_endpoint_kwargs": {"project_uuid": project_uuid},
            "page_title": f"Conversaciones de {project['name']}",
            "empty_message": "Aún no hay conversaciones en este proyecto.",
            "show_user": True,
        },
    )


@router.post("/{conversation_uuid}/transcript", response_class=HTMLResponse)
async def get_conversation_transcript_htmx(
    request: Request,
    conversation_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
    """
    HTMX endpoint: renders a conversation's turns as a read-only, chatbot-style
    transcript. Viewable by whoever had the conversation, or by an editor/observer
    who owns or is a member of its project.
    """
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _check_conversation_access(db, conversation, current_user)

    turns_result = await crud_conversation_turns.get_multi(
        db,
        conversation_log_id=conversation["id"],
        sort_columns=["sequence"],
        sort_orders=["asc"],
        limit=1000,
    )
    # Assistant turns may contain markdown (say-able templates); render+sanitize
    # them the same way live `say` messages are rendered in the WS transport.
    # User turns are shown as plain text -- their input shouldn't be interpreted
    # as markdown/HTML.
    turns = [
        {
            **turn,
            "html": render_markdown(turn["text"])[1]
            if turn["role"] == "assistant"
            else None,
        }
        for turn in turns_result.get("data", [])
    ]

    conversation_user = await crud_users.get(db, id=conversation["user_id"])
    await _attach_documents(db, [conversation])

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/conversation_transcript.html",
        context={
            "request": request,
            "conversation": conversation,
            "turns": turns,
            "conversation_user": conversation_user,
        },
    )


@router.delete("/{conversation_uuid}", response_class=Response)
async def delete_conversation_htmx(
    conversation_uuid: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_user),
):
    """
    HTMX endpoint: deletes a conversation (and its turns). Allowed for whoever
    had the conversation, or the owner of its project.
    """
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    can_delete = conversation["user_id"] == current_user["id"]
    if not can_delete and conversation["project_id"]:
        project = await crud_projects.get(db, id=conversation["project_id"])
        if project:
            can_delete = project["owner_id"] == current_user["id"]

    if not can_delete:
        raise HTTPException(
            status_code=403, detail="You cannot delete this conversation."
        )

    # Explicit two-step delete rather than relying on ON DELETE CASCADE:
    # SQLite doesn't enforce FK constraints unless PRAGMA foreign_keys=ON is
    # set per-connection, so a raw DELETE here could otherwise orphan turns.
    await db.execute(
        delete(ConversationTurn).where(
            ConversationTurn.conversation_log_id == conversation["id"]
        )
    )
    await db.execute(
        delete(ConversationDocument).where(
            ConversationDocument.conversation_log_id == conversation["id"]
        )
    )
    await db.execute(
        delete(ConversationLog).where(ConversationLog.id == conversation["id"])
    )
    await db.commit()

    # Not 204: htmx never swaps content on a 204 response, even with
    # swap:'delete', so the card removal on the client would silently no-op.
    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "conversationDeleted"
    return response


@router.post("/{conversation_uuid}/tags", response_class=HTMLResponse)
async def add_conversation_tag_htmx(
    conversation_uuid: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
    tag: Annotated[str, Form()] = "",
):
    """HTMX endpoint: adds a whole-conversation tag, returns the updated tags fragment."""
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _check_conversation_access(db, conversation, current_user)

    tag = tag.strip()
    tags = list(conversation["tags"])
    if tag and tag not in tags:
        tags.append(tag)
        await crud_conversation_logs.update(
            db, object=ConversationLogUpdateInternal(tags=tags), uuid=conversation_uuid
        )
        conversation["tags"] = tags

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/_conversation_tags.html",
        context={"request": request, "conversation": conversation},
    )


@router.delete("/{conversation_uuid}/tags/{tag}", response_class=HTMLResponse)
async def remove_conversation_tag_htmx(
    conversation_uuid: UUID,
    tag: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: removes a whole-conversation tag, returns the updated tags fragment."""
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _check_conversation_access(db, conversation, current_user)

    tags = [t for t in conversation["tags"] if t != tag]
    if tags != conversation["tags"]:
        await crud_conversation_logs.update(
            db, object=ConversationLogUpdateInternal(tags=tags), uuid=conversation_uuid
        )
        conversation["tags"] = tags

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/_conversation_tags.html",
        context={"request": request, "conversation": conversation},
    )


@router.post("/{conversation_uuid}/documents", response_class=HTMLResponse)
async def create_conversation_document_htmx(
    conversation_uuid: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
    title: Annotated[str, Form()] = "",
    kind: Annotated[str, Form()] = "",
    content: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
):
    """HTMX endpoint: attaches a document (analysis) to a conversation."""
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _check_conversation_access(db, conversation, current_user)

    title = title.strip()
    kind = kind.strip()
    content = content.strip()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if not title or not kind or not content:
        raise HTTPException(
            status_code=422, detail="title, kind and content are required"
        )

    new_document = await crud_conversation_documents.create(
        db,
        ConversationDocumentCreateInternal(
            conversation_log_id=conversation["id"],
            title=title,
            kind=kind,
            content=content,
            tags=tag_list,
            created_by_id=current_user["id"],
        ),
        schema_to_select=ConversationDocumentRead,
    )

    response = ctx.templates_api.TemplateResponse(
        request=request,
        name="user/_conversation_document_create_result.html",
        context={
            "request": request,
            "conversation": conversation,
            "doc": new_document,
        },
    )
    response.headers["HX-Trigger"] = "documentCreated"
    return response


@router.get("/{conversation_uuid}/documents/{document_id}", response_class=HTMLResponse)
async def get_conversation_document_htmx(
    conversation_uuid: UUID,
    document_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: renders a single document's full content for the view modal."""
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _check_conversation_access(db, conversation, current_user)

    document = await crud_conversation_documents.get(
        db, id=document_id, conversation_log_id=conversation["id"]
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    _, html = render_markdown(document["content"])

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="user/_conversation_document_view.html",
        context={"request": request, "doc": document, "html": html},
    )


@router.delete("/{conversation_uuid}/documents/{document_id}", response_class=Response)
async def delete_conversation_document_htmx(
    conversation_uuid: UUID,
    document_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: dict = Depends(get_current_user),
):
    """HTMX endpoint: deletes a document attached to a conversation."""
    conversation = await crud_conversation_logs.get(db, uuid=conversation_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await _check_conversation_access(db, conversation, current_user)

    document = await crud_conversation_documents.get(
        db, id=document_id, conversation_log_id=conversation["id"]
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    await crud_conversation_documents.delete(db, id=document_id)

    # Not 204: htmx never swaps content on a 204 response, even with
    # swap:'delete', so the row removal on the client would silently no-op.
    return Response(status_code=200)
