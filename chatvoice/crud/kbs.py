from fastcrud import FastCRUD

from ..models.kb import KB
from ..schemas.kb import KBCreate, KBDelete, KBRead, KBUpdate, KBUpdateInternal

CRUDKB = FastCRUD[KB, KBCreate, KBUpdate, KBUpdateInternal, KBDelete, KBRead]
crud_kbs = CRUDKB(KB)
