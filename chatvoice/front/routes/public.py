from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Request, HTTPException, Depends
from ...core.dependencies.paths import RuntimeContext, get_runtime_context
from ...utils.markdown import render_markdown_page

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def main(
    request: Request,
    ctx: RuntimeContext = Depends(get_runtime_context) # Single injection
) -> HTMLResponse:
    """Principal"""
    print(ctx)
    return render_markdown_page("main", request, ctx, is_main=True)


@router.get("/page/{view}", response_class=HTMLResponse)
async def page(
    view: str,
    request: Request,
    ctx: RuntimeContext = Depends(get_runtime_context) # Single injection
) -> HTMLResponse:
    """Páginas de contenido"""
    return render_markdown_page(view, request, ctx)
