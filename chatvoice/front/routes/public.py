from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Request, HTTPException, Depends
from ...core.dependencies.paths import RuntimeContext, get_runtime_context
from ...utils.markdown import markdown_page, render_markdown_page

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def main(
    request: Request,
    ctx: RuntimeContext = Depends(get_runtime_context) # Single injection
) -> HTMLResponse:
    """Principal"""
    md, notlogged_content=markdown_page("main_notlogged", ctx)
    _, protected_content=markdown_page("main_protected", ctx)

    context = {
        "notlogged_content": notlogged_content,
        "protected_content": protected_content,
        "metadata": md.Meta,
        "scope": "public",
        "active_page": md.Meta.get("active_page", [None])[0],
        "active_menu": md.Meta.get("active_menu", [None])[0],
    }

    return ctx.templates_engine.TemplateResponse(
        request=request,
        name="public/main.html",
        context=context,
    )

@router.get("/page/{view}", response_class=HTMLResponse)
async def page(
    view: str,
    request: Request,
    ctx: RuntimeContext = Depends(get_runtime_context) # Single injection
) -> HTMLResponse:
    """Páginas de contenido"""
    return render_markdown_page(view, "public/page.html", request, ctx)
