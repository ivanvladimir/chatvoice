from fastcrud import FastCRUD

from ..models.project import Project
from ..schemas.project import (
    ProjectCreateInternal,
    ProjectDelete,
    ProjectRead,
    ProjectUpdate,
    ProjectUpdateInternal,
)

CRUDProject = FastCRUD[
    Project,
    ProjectCreateInternal,
    ProjectUpdate,
    ProjectUpdateInternal,
    ProjectDelete,
    ProjectRead,
]
crud_projects = CRUDProject(Project)
