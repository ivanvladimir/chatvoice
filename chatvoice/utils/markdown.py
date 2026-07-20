import time
from pathlib import Path

import markdown
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from ..core.dependencies.paths import RuntimeContext


def markdown_page(
    view_name: str,
    ctx: RuntimeContext,  # We now pass the single aggregate object
) -> HTMLResponse:
    safe_filename = f"{Path(view_name).stem}.md"
    file_path = (ctx.content_path / safe_filename).resolve()

    if not str(file_path).startswith(str(ctx.content_path)):
        raise HTTPException(status_code=400, detail="Invalid page name")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Page not found")

    try:
        content_text = file_path.read_text(encoding="utf-8")
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading page content")

    md = markdown.Markdown(extensions=["meta", "tables", "fenced_code", "footnotes"])
    content_html = md.convert(content_text)
    return md, content_html


def render_markdown_page(
    view_name: str,
    template_file: Path,
    request: Request,
    ctx: RuntimeContext,  # We now pass the single aggregate object
    is_main: bool = False,
) -> HTMLResponse:
    start_time = time.time()

    md, content_html = markdown_page(view_name, ctx)

    context = {
        "content": content_html,
        "metadata": md.Meta,
        "scope": "public",
        "active_page": "main" if is_main else md.Meta.get("active_page", [None])[0],
        "active_menu": None if is_main else md.Meta.get("active_menu", [None])[0],
        "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
    }

    return ctx.templates_engine.TemplateResponse(
        request=request,
        name=template_file,
        context=context,
    )
