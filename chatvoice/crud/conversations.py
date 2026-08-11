from fastcrud import FastCRUD

from ..models.conversation import (
    ConversationDocument,
    ConversationLog,
    ConversationTurn,
)
from ..schemas.conversation import (
    ConversationDocumentCreateInternal,
    ConversationDocumentDelete,
    ConversationDocumentRead,
    ConversationDocumentUpdate,
    ConversationDocumentUpdateInternal,
    ConversationLogCreateInternal,
    ConversationLogDelete,
    ConversationLogListItem,
    ConversationLogUpdate,
    ConversationLogUpdateInternal,
    ConversationTurnCreateInternal,
    ConversationTurnDelete,
    ConversationTurnRead,
    ConversationTurnUpdate,
)

CRUDConversationLog = FastCRUD[
    ConversationLog,
    ConversationLogCreateInternal,
    ConversationLogUpdate,
    ConversationLogUpdateInternal,
    ConversationLogDelete,
    ConversationLogListItem,
]
crud_conversation_logs = CRUDConversationLog(ConversationLog)

# Turns are written from the interpreter thread via the sync
# ConversationLogStore (see chatvoice/store/conversation_store.py); this CRUD
# instance is only used for reading them back in the transcript API view.
CRUDConversationTurn = FastCRUD[
    ConversationTurn,
    ConversationTurnCreateInternal,
    ConversationTurnUpdate,
    ConversationTurnUpdate,
    ConversationTurnDelete,
    ConversationTurnRead,
]
crud_conversation_turns = CRUDConversationTurn(ConversationTurn)

CRUDConversationDocument = FastCRUD[
    ConversationDocument,
    ConversationDocumentCreateInternal,
    ConversationDocumentUpdate,
    ConversationDocumentUpdateInternal,
    ConversationDocumentDelete,
    ConversationDocumentRead,
]
crud_conversation_documents = CRUDConversationDocument(ConversationDocument)
