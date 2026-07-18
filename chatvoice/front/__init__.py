from fastapi import APIRouter

from .routes import public  # , user

router = APIRouter()
router.include_router(public.router, tags=["public"])
# router.include_router(user.router, tags=['user'])
