from fastcrud import FastCRUD

from ..models.project import Project
from ..schemas.project import (
    ProjectCreateInternal,
    ProjectDelete,
    ProjectListItem,
    ProjectUpdate,
    ProjectUpdateInternal,
)

CRUDProject = FastCRUD[
    Project,
    ProjectCreateInternal,
    ProjectUpdate,
    ProjectUpdateInternal,
    ProjectDelete,
    ProjectListItem,
]
crud_projects = CRUDProject(Project)
