from pydantic import BaseModel


class LoginParam(BaseModel):
    login_id: str
    password: str


class ChatTextRequest(BaseModel):
    previous_prompt: str
    ai_prompt: str
    user_prompt: str
    previous_prompt: str
    user: str


class ChatTextResponse(BaseModel):
    response: str
    conversation_id: str


class MediaTypes:
    json: str = "application/json"