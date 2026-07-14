from fastcrud import FastCRUD

from ..models.project import Project
from ..schemas.user import ProjectCreateInternal, ProjectDelete, ProjectRead, ProjectUpdate, ProjectUpdateInternal

CRUDProject = FastCRUD[Project, ProjectCreate, ProjectUpdate, ProjectUpdateInternal, ProjectDelete, ProjectRead]
crud_projects= CRUDUser(Project)
