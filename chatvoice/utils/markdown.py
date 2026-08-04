import time
from pathlib import Path

import markdown
import nh3
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Project content/*.md is user-authored (editor role, per-project) and rendered
# with `| safe` on public/authenticated pages, so the converted HTML must be
# sanitized rather than trusted. Extend nh3's default allowlist with id/class
# on a few tags so footnote anchors (footnotes extension) and code-block
# language hints (fenced_code extension) keep working.
_ALLOWED_ATTRIBUTES = {tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
for _tag in ("a", "sup", "div", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6"):
    _ALLOWED_ATTRIBUTES.setdefault(_tag, set())
    _ALLOWED_ATTRIBUTES[_tag] |= {"id", "class"}


def markdown_page(
    view_name: str,
    content_dir: Path,  # We now pass the single aggregate object
) -> HTMLResponse:
    safe_filename = f"{Path(view_name).stem}.md"
    file_path = (content_dir / safe_filename).resolve()

    if not str(file_path).startswith(str(content_dir)):
        raise HTTPException(status_code=400, detail="Invalid page name")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Page not found")

    try:
        content_text = file_path.read_text(encoding="utf-8")
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading page content")

    md = markdown.Markdown(extensions=["meta", "tables", "fenced_code", "footnotes"])
    content_html = md.convert(content_text)
    content_html = nh3.clean(content_html, attributes=_ALLOWED_ATTRIBUTES)
    return md, content_html


def render_markdown_page(
    view_name: str,
    template_file: Path,
    request: Request,
    templates_front: Jinja2Templates,
    content_dir: Path,
    context: dict = {},
    is_main: bool = False,
) -> HTMLResponse:
    start_time = time.time()

    md, content_html = markdown_page(view_name, content_dir)

    context_ = {
        "content": content_html,
        "metadata": md.Meta,
        "scope": "public",
        "active_page": "main" if is_main else md.Meta.get("active_page", [None])[0],
        "active_menu": None if is_main else md.Meta.get("active_menu", [None])[0],
        "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
    }
    context_.update(context)

    return templates_front.TemplateResponse(
        request=request,
        name=template_file,
        context=context_,
    )
