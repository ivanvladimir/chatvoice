from sqlalchemy import select, insert, update
from datetime import datetime, UTC
from typing import Any
from ..models import KB
from ..core.db.database_sync import get_db_ctx


class SqlAlchemyMemoryStore:
    def remember(self, user_id: int, project_path: str, variable: str, value: Any):
        with get_db_ctx() as db:
            result = db.execute(
                select(KB).filter_by(
                    user_id=user_id,
                    project_path=project_path,
                    is_deleted=False,
                )
            )
            kb = result.scalar_one_or_none()

            if not kb:
                stmt = insert(KB).values(
                    user_id=user_id,
                    project_path=project_path,
                    payload={variable: value},
                    created_at=datetime.now(UTC),
                )
                db.execute(stmt)
            else:
                payload = dict(kb.payload)
                payload.update({variable: value})
                stmt = (
                    update(KB)
                    .where(KB.id == kb.id)
                    .values(payload=payload, updated_at=datetime.now(UTC))
                )
                db.execute(stmt)
            db.flush()
