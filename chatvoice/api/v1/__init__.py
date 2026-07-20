from fastapi import APIRouter

from .default import router as default_router
from .health import router as health_router
from .interface import router as interface_router
from .login import router as login_router
from .ws import router as ws_router
from .project import router as project_router

# from .logout import router as logout_router
# from .oauth import router as oauth_router
# from .posts import router as posts_router
# from .rate_limits import router as rate_limits_router
# from .tasks import router as tasks_router
# from .tiers import router as tiers_router
# from .users import router as users_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(login_router)
router.include_router(ws_router)
router.include_router(default_router)
router.include_router(interface_router)
router.include_router(project_router)
# router.include_router(logout_router)
# router.include_router(oauth_router)
# router.include_router(posts_router)
# router.include_router(rate_limits_router)
# router.include_router(tasks_router)
# router.include_router(tiers_router)
# router.include_router(users_router)
