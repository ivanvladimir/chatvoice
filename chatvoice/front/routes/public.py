from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.dependencies.paths import (
    RuntimeContext,
    get_default_context,
    get_project_context,
)
from ...utils.markdown import render_markdown_page

router = APIRouter(tags=["public"])


@router.get("/page/{view}", response_class=HTMLResponse)
async def page(
    view: str,
    request: Request,
    ctx: RuntimeContext = Depends(get_default_context),  # Single injection
) -> HTMLResponse:
    """Páginas de contenido"""
    return render_markdown_page(
        view, "public/page.html", request, ctx.templates_front, ctx.content_dir
    )


@router.get("/page/{script}/{view}", response_class=HTMLResponse, name="page_project_")
@router.get(
    "/page/{username}/{script}/{view}", response_class=HTMLResponse, name="page_project"
)
async def page_project(
    view: str,
    script: str,
    request: Request,
    ctx: RuntimeContext = Depends(get_project_context),  # Single injection
    username: str = None,
) -> HTMLResponse:
    """Páginas de contenido"""
    return render_markdown_page(
        view,
        "public/page.html",
        request,
        ctx.templates_front,
        ctx.content_dir,
        context={"username": username, "script": script},
    )
