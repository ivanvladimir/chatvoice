from fastapi import APIRouter

from .routes import public  # , user
from .routes import project  # , user

router = APIRouter()
router.include_router(public.router, tags=["public"])
router.include_router(project.router, tags=["project"])
# router.include_router(user.router, tags=['user'])
