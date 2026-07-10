from typing import Annotated

from crudadmin import CRUDAdmin
from crudadmin.admin_interface.model_view import PasswordTransformer
from pydantic import BaseModel, Field

from ..core.security import get_password_hash
#from ..models.task import Task
from ..models.tier import Tier
from ..models.user import User
#from ..schemas.task import TaskUpdate, TaskCreate, TaskCreateInternal
from ..schemas.tier import TierCreate, TierUpdate
from ..schemas.user import UserCreate, UserCreateInternal, UserUpdate

from enum import Enum as PyEnum

class TaskStatus(PyEnum):
    """Enum for task status"""
    STARTING = "starting"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"

class TaskCreateAdmin(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=500, examples=["This is my task"])]
    status: Annotated[TaskStatus, Field(default=TaskStatus.STARTING)]
    created_by_user_id: int

def register_admin_views(admin: CRUDAdmin) -> None:
    """Register all models and their schemas with the admin interface.

    This function adds all available models to the admin interface with appropriate
    schemas and permissions.
    """

    password_transformer = PasswordTransformer(
        password_field="password",
        hashed_field="hashed_password",
        hash_function=get_password_hash,
        required_fields=["name", "username", "email", "role"],
    )

    admin.add_view(
        model=User,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        update_internal_schema=UserCreateInternal,
        password_transformer=password_transformer,
        allowed_actions={"view", "create", "update","delete"},
    )

    admin.add_view(
        model=Tier,
        create_schema=TierCreate,
        update_schema=TierUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

#    admin.add_view(
#        model=Task,
#        create_schema=TaskCreate,
#        update_schema=TaskUpdate,
#        update_internal_schema=TaskCreateInternal,
#        allowed_actions={"view", "create", "update", "delete"},
#    )
