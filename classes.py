from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateUser(BaseModel):
    login_id: str
    password: str
    user_name: str