from fastcrud import FastCRUD

from ..models.project import Project
from ..schemas.project import (
    ProjectCreate,
    ProjectDelete,
    ProjectRead,
    ProjectUpdate,
    ProjectUpdateInternal,
)

CRUDProject = FastCRUD[
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectUpdateInternal,
    ProjectDelete,
    ProjectRead,
]
crud_projects = CRUProject(Project)
