from pydantic import BaseModel


class LoginParam(BaseModel):
    login_id: str
    password: str


class ChatTextRequest(BaseModel):
    ai_prompt: str
    user_prompt: str
    previous_prompt: str
    model: str
    length: int
    user: str


class ChatTextResponse(BaseModel):
    response: str
    conversation_id: str


class MediaTypes:
    json: str = "application/json"