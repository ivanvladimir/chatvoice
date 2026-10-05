import math
import re
import statistics
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, delete, func, select
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
from ..dependencies import get_current_project_viewer, get_current_user

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

    if current_user["role"] not in ("editor", "admin", "observer"):
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
    current_user: dict = Depends(get_current_project_viewer),
    page: int = Form(1, ge=1),
    items_per_page: int = Form(12, ge=1, le=50),
):
    """
    HTMX endpoint: lists ALL conversations for a project (any user who ran
    one), gated to editor/admin/observer role AND project ownership/membership.
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


def _min_max_avg(values: list[float]) -> dict:
    """Min, max, mean and sample standard deviation (None with fewer than 2 values)."""
    if not values:
        return {"min": None, "max": None, "avg": None, "std": None}
    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "std": statistics.stdev(values) if len(values) > 1 else None,
    }


def _text_stats(texts: list[str]) -> dict:
    """Total/unique text count plus min/max/std word count, for one turn role."""
    if not texts:
        return {
            "total": 0,
            "unique": 0,
            "words_min": None,
            "words_max": None,
            "words_std": None,
        }
    word_counts = [len(t.split()) for t in texts]
    return {
        "total": len(texts),
        "unique": len(set(texts)),
        "words_min": min(word_counts),
        "words_max": max(word_counts),
        "words_std": statistics.stdev(word_counts) if len(word_counts) > 1 else None,
    }


@router.post("/project/{project_uuid}/stats", response_class=HTMLResponse)
async def project_conversation_stats_htmx(
    request: Request,
    project_uuid: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_project_viewer),
    username_regex: str = Form(""),
    min_turns: int = Form(10, ge=0),
    searched: bool = Form(False),
):
    """
    HTMX endpoint: aggregate stats + full turn listing for a project's
    conversations, filtered by a regex on the conversation owner's username
    and a minimum turn count. Gated the same way as the project's conversation
    list (editor/admin/observer AND project ownership/membership).

    Nothing is computed until `searched` is set (the filter form only sends it
    once rendered) -- a project can have far too many turns to dump by default.
    """
    project = await crud_projects.get(db, uuid=project_uuid, is_deleted=False)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _check_project_access(db, project, current_user)

    username_regex = username_regex.strip()
    regex_error: str | None = None
    pattern: re.Pattern | None = None
    if username_regex:
        try:
            pattern = re.compile(username_regex)
        except re.error as e:
            regex_error = str(e)

    stats = None
    rows: list[dict] = []

    if regex_error is None and searched:
        result = await db.execute(
            select(ConversationLog, User.username, User.name)
            .join(User, User.id == ConversationLog.user_id)
            .where(ConversationLog.project_id == project["id"])
            .order_by(ConversationLog.started_at.desc())
        )
        matched = [
            (log, username, name)
            for log, username, name in result.all()
            if pattern is None or pattern.search(username)
        ]

        turns_by_log: dict[int, list[ConversationTurn]] = {}
        log_ids = [log.id for log, _, _ in matched]
        if log_ids:
            turns_result = await db.execute(
                select(ConversationTurn)
                .where(ConversationTurn.conversation_log_id.in_(log_ids))
                .order_by(
                    ConversationTurn.conversation_log_id, ConversationTurn.sequence
                )
            )
            for turn in turns_result.scalars().all():
                turns_by_log.setdefault(turn.conversation_log_id, []).append(turn)

        turn_counts: list[int] = []
        durations: list[float] = []
        user_response_seconds: list[float] = []
        system_response_seconds: list[float] = []
        conversations_by_user: dict[str, int] = {}
        role_texts: dict[str, list[str]] = {"user": [], "assistant": []}

        for log, username, name in matched:
            turns = turns_by_log.get(log.id, [])
            if len(turns) < min_turns:
                continue

            turn_counts.append(len(turns))
            conversations_by_user[username] = conversations_by_user.get(username, 0) + 1

            if turns:
                end_time = log.ended_at or turns[-1].created_at
                duration = (end_time - log.started_at).total_seconds()
                if duration >= 0:
                    durations.append(duration)

            prev_turn: ConversationTurn | None = None
            for turn in turns:
                if prev_turn is not None:
                    delta = (turn.created_at - prev_turn.created_at).total_seconds()
                    if delta >= 0:
                        if turn.role == "user":
                            user_response_seconds.append(delta)
                        elif turn.role == "assistant":
                            system_response_seconds.append(delta)
                prev_turn = turn

                if turn.role in role_texts:
                    role_texts[turn.role].append(turn.text)

                rows.append(
                    {
                        "conversation_uuid": log.uuid,
                        "username": username,
                        "name": name,
                        "started_at": log.started_at,
                        "sequence": turn.sequence,
                        "role": turn.role,
                        "text": turn.text,
                        "created_at": turn.created_at,
                    }
                )

        unique_users = len(conversations_by_user)
        top_user = None
        if conversations_by_user:
            top_username, top_count = max(
                conversations_by_user.items(), key=lambda kv: kv[1]
            )
            top_user = {"username": top_username, "count": top_count}

        stats = {
            "num_conversations": len(turn_counts),
            "total_turns": sum(turn_counts),
            "turns": _min_max_avg([float(c) for c in turn_counts]),
            "duration_seconds": _min_max_avg(durations),
            "user_turn_seconds": _min_max_avg(user_response_seconds),
            "system_turn_seconds": _min_max_avg(system_response_seconds),
            "unique_users": unique_users,
            "avg_conversations_per_user": (
                len(turn_counts) / unique_users if unique_users else None
            ),
            "top_user": top_user,
            "user_text": _text_stats(role_texts["user"]),
            "system_text": _text_stats(role_texts["assistant"]),
        }

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/conversation_stats_content.html",
        context={
            "request": request,
            "project": project,
            "username_regex": username_regex,
            "min_turns": min_turns,
            "regex_error": regex_error,
            "searched": searched,
            "stats": stats,
            "rows": rows,
        },
    )


def _compile_username_regex(
    username_regex: str,
) -> tuple[re.Pattern | None, str | None]:
    """Returns (pattern, error); pattern is None when the regex is empty or invalid."""
    if not username_regex:
        return None, None
    try:
        return re.compile(username_regex), None
    except re.error as e:
        return None, str(e)


async def _project_conversation_metrics(
    db: AsyncSession, project_id: int, pattern: re.Pattern | None, min_turns: int
) -> list[dict]:
    """
    Per-conversation turn count and duration for a project, filtered like the
    stats view: username regex and minimum turn count. Duration runs from
    `started_at` to `ended_at` (or the last turn), and is None for
    conversations without turns or with inconsistent timestamps.
    """
    result = await db.execute(
        select(
            User.username,
            ConversationLog.id,
            ConversationLog.started_at,
            ConversationLog.ended_at,
            func.count(ConversationTurn.id),
            func.max(ConversationTurn.created_at),
        )
        .select_from(ConversationLog)
        .join(User, User.id == ConversationLog.user_id)
        .outerjoin(
            ConversationTurn,
            ConversationTurn.conversation_log_id == ConversationLog.id,
        )
        .where(ConversationLog.project_id == project_id)
        .group_by(ConversationLog.id, User.username)
    )

    metrics = []
    for username, log_id, started_at, ended_at, turns, last_turn_at in result.all():
        if turns < min_turns or (pattern is not None and not pattern.search(username)):
            continue
        duration = None
        if turns:
            seconds = ((ended_at or last_turn_at) - started_at).total_seconds()
            if seconds >= 0:
                duration = seconds
        metrics.append({"log_id": log_id, "turns": turns, "duration_seconds": duration})
    return metrics


async def _response_seconds(
    db: AsyncSession, log_ids: list[int], role: str
) -> list[float]:
    """
    Per-turn response times for `role` ("user" or "assistant"): seconds
    between each of its turns and the turn right before it, as in the stats view.
    """
    if not log_ids:
        return []
    result = await db.execute(
        select(
            ConversationTurn.conversation_log_id,
            ConversationTurn.role,
            ConversationTurn.created_at,
        )
        .where(ConversationTurn.conversation_log_id.in_(log_ids))
        .order_by(ConversationTurn.conversation_log_id, ConversationTurn.sequence)
    )

    seconds: list[float] = []
    prev_log_id = prev_created_at = None
    for log_id, turn_role, created_at in result.all():
        if log_id == prev_log_id and turn_role == role:
            delta = (created_at - prev_created_at).total_seconds()
            if delta >= 0:
                seconds.append(delta)
        prev_log_id, prev_created_at = log_id, created_at
    return seconds


async def _turn_texts(db: AsyncSession, log_ids: list[int], role: str) -> list[str]:
    """Texts of every `role` turn ("user" or "assistant") in the given conversations."""
    if not log_ids:
        return []
    result = await db.execute(
        select(ConversationTurn.text).where(
            ConversationTurn.conversation_log_id.in_(log_ids),
            ConversationTurn.role == role,
        )
    )
    return list(result.scalars().all())


def _nice_bin_width(span: float, max_bins: int) -> float:
    """Smallest 1/2/2.5/5 x 10^k width that covers `span` in at most `max_bins` bins."""
    rough = max(span, 1e-9) / max_bins
    magnitude = 10 ** math.floor(math.log10(rough))
    for factor in (1, 2, 2.5, 5, 10):
        if factor * magnitude >= rough:
            return factor * magnitude
    return 10 * magnitude


def _fmt_bin_edge(value: float) -> str:
    return f"{value:g}"


def _histogram_series(series: list[dict], integer: bool, max_bins: int = 30) -> dict:
    """
    Buckets one or more series (`{"name", "values", "mean"}`) into the same
    at most `max_bins` equal-width bins. Returns shared `labels`, plus
    `first_center` and `bin_width` so the front-end can place each mean on the
    binned axis, and per-series `counts`.

    Integer bins cover whole values (label "3" or "9–17"); continuous bins are
    half-open intervals [a, b) labelled "a–b".
    """
    all_values = [v for item in series for v in item["values"]]
    if not all_values:
        return {"labels": [], "bin_width": 1, "first_center": 0, "series": []}

    lo, hi = min(all_values), max(all_values)
    if integer:
        width: float = max(1, math.ceil((hi - lo + 1) / max_bins))
        low = lo
    else:
        width = _nice_bin_width(hi - lo, max_bins)
        low = math.floor(lo / width) * width
    num_bins = int((hi - low) // width) + 1

    binned = []
    for item in series:
        counts = [0] * num_bins
        for v in item["values"]:
            counts[min(int((v - low) // width), num_bins - 1)] += 1
        binned.append({"name": item["name"], "counts": counts, "mean": item["mean"]})

    labels = []
    for i in range(num_bins):
        start = low + i * width
        if integer:
            end = start + width - 1
            labels.append(
                str(int(start)) if start == end else f"{int(start)}–{int(end)}"
            )
        else:
            labels.append(f"{_fmt_bin_edge(start)}–{_fmt_bin_edge(start + width)}")

    return {
        "labels": labels,
        "bin_width": width,
        # Value at the center of the first bin (integer bins span whole values)
        "first_center": low + ((width - 1) / 2 if integer else width / 2),
        "series": binned,
    }


def _histogram(values: list[float], mean: float | None, integer: bool) -> dict:
    """Single-series histogram (see `_histogram_series`)."""
    return _histogram_series(
        [{"name": None, "values": values, "mean": mean}], integer=integer
    )


def _fmt_seconds(value: float | None) -> str:
    """Python twin of the stats template's `fmt_seconds` macro."""
    if value is None:
        return "—"
    total = round(value, 1)
    if total >= 3600:
        return f"{int(total // 3600)}h {int((total % 3600) // 60)}m"
    if total >= 60:
        return f"{int(total // 60)}m {round(total % 60)}s"
    return f"{total}s"


def _fmt_num(value: float | None) -> str:
    return "—" if value is None else f"{round(value, 1)}"


def _fmt_int(value: float | None) -> str:
    return "—" if value is None else str(int(value))


def _duration_unit(max_seconds: float) -> tuple[str, str, float]:
    """(abbreviation, label, divisor) giving readable bin edges for the duration axis."""
    if max_seconds < 180:
        return "s", "segundos", 1
    if max_seconds < 3 * 3600:
        return "min", "minutos", 60
    return "h", "horas", 3600


# Per-conversation (or per-turn) histograms linked from the stats page.
# `x_label` for time metrics gets the chosen unit appended, e.g. "(minutos)";
# `count_noun` names what each bar counts (y axis: "Frecuencia (<count_noun>)").
HISTOGRAM_VIEWS = {
    "turns": {
        "title": "Turnos por conversación",
        "x_label": "Número de turnos por conversación",
        "file_base": "turnos_por_conversacion",
        "count_noun": "conversaciones",
    },
    "duration": {
        "title": "Duración de conversación",
        "x_label": "Duración de la conversación",
        "file_base": "duracion_de_conversacion",
        "count_noun": "conversaciones",
    },
    "user_response": {
        "title": "Tiempo de respuesta del usuario",
        "x_label": "Tiempo de respuesta del usuario",
        "file_base": "tiempo_de_respuesta_usuario",
        "count_noun": "respuestas",
        "role": "user",
    },
    "system_response": {
        "title": "Tiempo de respuesta del sistema",
        "x_label": "Tiempo de respuesta del sistema",
        "file_base": "tiempo_de_respuesta_sistema",
        "count_noun": "respuestas",
        "role": "assistant",
    },
    "user_text": {
        "title": "Textos de usuario",
        "x_label": "Palabras por turno del usuario",
        "file_base": "palabras_por_turno_usuario",
        "count_noun": "textos",
        "role": "user",
    },
    "system_text": {
        "title": "Textos de sistema",
        "x_label": "Palabras por turno del sistema",
        "file_base": "palabras_por_turno_sistema",
        "count_noun": "textos",
        "role": "assistant",
    },
    "text_compare": {
        "title": "Textos de usuario y sistema",
        "x_label": "Palabras por turno",
        "file_base": "palabras_por_turno_usuario_y_sistema",
        "count_noun": "textos",
    },
}

HistogramMetric = Literal[
    "turns",
    "duration",
    "user_response",
    "system_response",
    "user_text",
    "system_text",
    "text_compare",
]


def _seconds_histogram(seconds: list[float]) -> tuple[dict, str]:
    """Histogram of durations in a readable unit; returns it with the unit label."""
    agg = _min_max_avg(seconds)
    _, unit_label, divisor = _duration_unit(agg["max"] or 0)
    histogram = _histogram(
        [s / divisor for s in seconds],
        agg["avg"] / divisor if agg["avg"] is not None else None,
        integer=False,
    )
    return histogram, unit_label


def _seconds_card(title: str, seconds: list[float]) -> dict:
    agg = _min_max_avg(seconds)
    return {
        "title": title,
        "value": _fmt_seconds(agg["avg"]),
        "desc": f"min {_fmt_seconds(agg['min'])} · max {_fmt_seconds(agg['max'])} · σ {_fmt_seconds(agg['std'])}",
    }


@router.post("/project/{project_uuid}/stats/{metric}", response_class=HTMLResponse)
async def project_conversation_histogram_htmx(
    request: Request,
    project_uuid: UUID,
    metric: HistogramMetric,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    ctx: RuntimeContext = Depends(get_default_context),
    current_user: dict = Depends(get_current_project_viewer),
    username_regex: str = Form(""),
    min_turns: int = Form(1, ge=0),
):
    """
    HTMX endpoint: histogram of one metric over a project's conversations --
    turns per conversation, conversation duration, user/system response time
    per turn, or user/system words per turn (separately or side by side) -- filtered by a regex on the conversation owner's username
    and a minimum turn count. Metrics are computed as in the stats view, and
    access is gated the same way.
    """
    project = await crud_projects.get(db, uuid=project_uuid, is_deleted=False)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _check_project_access(db, project, current_user)

    username_regex = username_regex.strip()
    pattern, regex_error = _compile_username_regex(username_regex)

    view = {**HISTOGRAM_VIEWS[metric], "metric": metric}
    histogram = None
    cards: list[dict] = []
    if regex_error is None:
        metrics = await _project_conversation_metrics(
            db, project["id"], pattern, min_turns
        )
        cards.append({"title": "Conversaciones", "value": str(len(metrics))})

        if metric == "turns":
            turns = [float(m["turns"]) for m in metrics]
            agg = _min_max_avg(turns)
            histogram = _histogram(turns, agg["avg"], integer=True)
            cards += [
                {"title": "Turnos totales", "value": str(int(sum(turns)))},
                {
                    "title": "Turnos por conversación",
                    "value": _fmt_num(agg["avg"]),
                    "desc": f"min {_fmt_int(agg['min'])} · max {_fmt_int(agg['max'])} · σ {_fmt_num(agg['std'])}",
                },
            ]
        elif metric in ("user_text", "system_text"):
            texts = await _turn_texts(db, [m["log_id"] for m in metrics], view["role"])
            # Same word count as the stats view's min/max palabras/turno
            words = [float(len(t.split())) for t in texts]
            agg = _min_max_avg(words)
            histogram = _histogram(words, agg["avg"], integer=True)
            cards += [
                {
                    "title": "Textos",
                    "value": str(len(texts)),
                    "desc": f"{len(set(texts))} únicos",
                },
                {
                    "title": "Palabras por turno",
                    "value": _fmt_num(agg["avg"]),
                    "desc": f"min {_fmt_int(agg['min'])} · max {_fmt_int(agg['max'])} · σ {_fmt_num(agg['std'])}",
                },
            ]
        elif metric == "text_compare":
            log_ids = [m["log_id"] for m in metrics]
            series = []
            for name, role in (("Usuario", "user"), ("Sistema", "assistant")):
                texts = await _turn_texts(db, log_ids, role)
                words = [float(len(t.split())) for t in texts]
                agg = _min_max_avg(words)
                series.append({"name": name, "values": words, "mean": agg["avg"]})
                cards.append(
                    {
                        "title": f"Palabras por turno ({name.lower()})",
                        "value": _fmt_num(agg["avg"]),
                        "desc": f"{len(texts)} textos · min {_fmt_int(agg['min'])} · max {_fmt_int(agg['max'])} · σ {_fmt_num(agg['std'])}",
                    }
                )
            histogram = _histogram_series(series, integer=True)
        else:
            if metric == "duration":
                seconds = [
                    m["duration_seconds"]
                    for m in metrics
                    if m["duration_seconds"] is not None
                ]
                count_title = "Con duración válida"
            else:
                seconds = await _response_seconds(
                    db, [m["log_id"] for m in metrics], view["role"]
                )
                count_title = "Turnos medidos"
            histogram, unit_label = _seconds_histogram(seconds)
            view["x_label"] = f"{view['x_label']} ({unit_label})"
            cards += [
                {"title": count_title, "value": str(len(seconds))},
                _seconds_card(view["title"], seconds),
            ]

    return ctx.templates_api.TemplateResponse(
        request=request,
        name="projects/conversation_histogram_content.html",
        context={
            "request": request,
            "project": project,
            "view": view,
            "username_regex": username_regex,
            "min_turns": min_turns,
            "regex_error": regex_error,
            "histogram": histogram,
            "cards": cards,
            # Unique per render: htmx "settles" elements whose id survives a swap
            # by re-applying their attributes, which resets a canvas and blanks
            # the freshly drawn chart.
            "chart_id": f"histogram-chart-{uuid4().hex}",
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
