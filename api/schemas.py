from pydantic import BaseModel


# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    chat_history: list[ChatMessage]
    conversation_id: str | None
    username: str
    top_k_rerank: int = 5
    is_first_message: bool = False

class RegisterRequest(BaseModel):
    username: str
    hashed_password: str
    
class NewConversationRequest(BaseModel):
    username: str
    title: str

class DeleteConversationRequest(BaseModel):
    username: str
    conversation_id: str

class UpdateTitleRequest(BaseModel):
    username: str
    conversation_id: str
    new_title: str