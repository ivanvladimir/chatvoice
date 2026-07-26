from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.dependencies.paths import RuntimeContext, get_project_context, get_default_context
from ...utils.markdown import markdown_page, render_markdown_page

router = APIRouter(tags=["public"])

@router.get("/page/{view}", response_class=HTMLResponse)
async def page(
    view: str,
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
) -> HTMLResponse:
    """Páginas de contenido"""
    return render_markdown_page(view, "public/page.html", request, ctx.templates_front, ctx.content_dir)

@router.get("/page/{username}/{script}/{view}", response_class=HTMLResponse)
async def page(
    view: str,
    username: str,
    script: str,
    request: Request,
    ctx: RuntimeContext = Depends(get_project_context),  # Single injection
) -> HTMLResponse:
    """Páginas de contenido"""
    return render_markdown_page(view, "public/page.html", request, ctx.templates_front, ctx.content_dir)
