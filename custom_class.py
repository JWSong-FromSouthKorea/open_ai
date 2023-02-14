from pydantic import BaseModel
from typing import Optional


class LoginParam(BaseModel):
    login_id: str
    password: str


class TextRequest(BaseModel):
    prompt: str
    model: str
    length: int


class ChatTextRequest(BaseModel):
    ai_prompt: str
    user_prompt: str
    model: str
    length: int
    user: str


class TextResponse(BaseModel):
    response: str


class ChatTextResponse(BaseModel):
    response: str
    conversation_id: str


class MediaTypes:
    json: str = "application/json"
