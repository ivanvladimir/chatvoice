from fastcrud import FastCRUD

from ..models.project import Project
from ..schemas.project import ProjectDelete, ProjectRead, ProjectUpdate, ProjectUpdateInternal, ProjectCreate

CRUDProject = FastCRUD[Project, ProjectCreate, ProjectUpdate, ProjectUpdateInternal, ProjectDelete, ProjectRead]
crud_projects= CRUDUser(Project)
