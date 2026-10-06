# Views list fields by column name; starlette-admin accepts that, but annotates
# `fields` as BaseField instances only.
# mypy: disable-error-code="list-item"
import dataclasses
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette_admin import PasswordField
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.exceptions import FormValidationError
from starlette_admin.helpers import on_commit

from ..core.security import get_password_hash
from ..models.kb import KB
from ..models.project import Project
from ..models.tier import Tier
from ..models.user import User


class DataclassModelView(ModelView):
    """
    ModelView for the app's `MappedAsDataclass` models.

    starlette-admin builds new rows with `self.model()`, but dataclass models
    require their non-defaulted fields as constructor arguments. This builds the
    instance from the form data instead; everything else follows the stock
    `ModelView.create` (async sessions only, as the app uses an async engine).

    Fields should be listed explicitly, so relationships don't need views of
    their own, and fields filled by a `default_factory` (uuid, created_at) kept
    out of the create form so the factory runs.
    """

    def _new_instance(self, data: dict[str, Any]) -> Any:
        kwargs = {}
        for field in dataclasses.fields(self.model):
            if not field.init:
                continue
            if field.name in data:
                kwargs[field.name] = data[field.name]
            elif (
                field.default is dataclasses.MISSING
                and field.default_factory is dataclasses.MISSING
            ):
                kwargs[field.name] = None
        obj = self.model(**kwargs)
        # A relationship defaulted to None (e.g. KB.user) would null its foreign
        # key on flush, overriding the id set from the form; leave it unset.
        state = inspect(obj)
        for rel in state.mapper.relationships:
            if rel.key in state.dict and state.dict[rel.key] is None:
                del state.dict[rel.key]
        return obj

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        session: AsyncSession = request.state.session
        try:
            data = await self._arrange_data(request, data)
            await self.validate(request, data)
            async with session.begin_nested():
                obj = await self._populate_obj(request, self._new_instance(data), data)
                await self._emit_before_create(request, data, obj)
                session.add(obj)
                await session.flush()
            await session.refresh(obj, self._refresh_attr_names(request))
            await self._emit_after_create(request, obj)
            on_commit(request, lambda: self._emit_after_create_committed(request, obj))
            return obj
        except Exception as e:
            return await self.handle_exception(request, e)


class UserView(DataclassModelView):
    fields = [
        "id",
        "name",
        "username",
        "email",
        PasswordField(
            "password",
            label="Contraseña",
            help_text="Al editar, dejar vacío para conservar la actual.",
            exclude_from_list=True,
            exclude_from_detail=True,
            exclude_from_export=True,
            exclude_from_import=True,
        ),
        "role",
        "institution",
        "description",
        "is_verified",
        "is_deleted",
        "tier_id",
        "uuid",
        "created_at",
    ]
    exclude_fields_from_create = ["id", "uuid", "created_at"]
    exclude_fields_from_edit = ["id", "uuid", "created_at"]
    searchable_fields = ["name", "username", "email", "institution"]

    async def before_create(
        self, request: Request, data: dict[str, Any], obj: Any
    ) -> None:
        if not data.get("password"):
            raise FormValidationError({"password": "La contraseña es obligatoria."})
        obj.hashed_password = get_password_hash(data["password"])

    async def before_edit(
        self, request: Request, data: dict[str, Any], obj: Any
    ) -> None:
        if data.get("password"):
            obj.hashed_password = get_password_hash(data["password"])


class KBView(DataclassModelView):
    fields = [
        "id",
        "user_id",
        "project_path",
        "payload",
        "is_deleted",
        "created_at",
        "updated_at",
    ]
    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]


class ProjectView(DataclassModelView):
    fields = [
        "id",
        "name",
        "project_name",
        "owner_id",
        "description",
        "is_active",
        "is_deleted",
        "source_url",
        "import_status",
        "import_error",
        "uuid",
        "created_at",
    ]
    exclude_fields_from_create = ["id", "uuid", "created_at"]
    exclude_fields_from_edit = ["id", "uuid", "created_at"]


class TierView(DataclassModelView):
    fields = ["id", "name", "created_at"]
    exclude_fields_from_create = ["id", "created_at"]
    exclude_fields_from_edit = ["id", "created_at"]


def register_admin_views(admin: Admin) -> None:
    """Register every model managed from the admin interface."""
    admin.add_view(UserView(User, icon="fa fa-users", menu_label="Usuarios"))
    admin.add_view(KBView(KB, key="kb", icon="fa fa-database", menu_label="KB"))
    admin.add_view(ProjectView(Project, icon="fa fa-folder", menu_label="Proyectos"))
    admin.add_view(TierView(Tier, icon="fa fa-layer-group", menu_label="Tiers"))
