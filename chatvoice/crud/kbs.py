from fastcrud import FastCRUD

from ..models.kb import KB
from ..schemas.kb import KBInternal, KBDelete, KBRead, KNUpdate, KBUpdateInternal

CRUDKB = FastCRUD[KB, KBCreate, UserUpdate, KBUpdateInternal, KBDelete, KBRead]
crud_kbs = CRUDKB(KB)
