from fastcrud import FastCRUD

from ..models.kb import KB
from ..schemas.kb import KBCreate, KBUpdate, KBDelete, KBRead, KBUpdateInternal

CRUDKB = FastCRUD[KB, KBCreate, KBUpdate, KBUpdateInternal, KBDelete, KBRead]
crud_kbs = CRUDKB(KB)
