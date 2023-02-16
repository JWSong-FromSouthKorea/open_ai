from datetime import timedelta

import aiohttp
import openai
import ujson
from fastapi import Depends, FastAPI, Response, Header, HTTPException
from fastapi_login import LoginManager
from sqlalchemy.orm import Session

from classes import Token, CreateUser
from config import Config
from custom_class import MediaTypes, LoginParam, ChatTextRequest, ChatTextResponse
from database import get_session, export_session
from database.actions import actions
from database.models import User
from verify import hash_password, verify_password, get_secret_value

openai.api_key = Config.api_key

manager = LoginManager(
    secret=Config.secret,
    token_url=Config.token_url,
    algorithm="HS256",
    default_expiry=timedelta(hours=6)
)
app = FastAPI()


# define a function to authenticate users
@manager.user_loader
async def load_user(login_id: str, database: Session):
    user = await actions.get_user_by_login_id(login_id, database)
    return user


# add authentication verification to all API routes
@app.middleware("http")
async def auth_middleware(request, call_next):
    import jwt

    request.state.database = export_session()
    path = request.url.path
    if path.startswith("/login"):
        # Skip authentication for the login route
        response = await call_next(request)
        return response
    else:
        # Check for authentication token
        token: str = request.headers.get("Authorization") or request.headers.get("authorization")
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        try:
            decoded_token = jwt.decode(token[7:], get_secret_value(), algorithms=["HS256"])
            login_id = decoded_token.get("sub")
            if not login_id:
                raise HTTPException(status_code=401, detail="Unauthorized")

        except Exception as e:
            raise HTTPException(status_code=401, detail=e)

        # Add the authenticated user to the request
        request.state.login_id = login_id
        response = await call_next(request)
        return response


@app.post(Config.token_url)
async def login(param: LoginParam, database: Session = Depends(get_session)):
    from fastapi_login.exceptions import InvalidCredentialsException

    user = await load_user(param.login_id, database)
    hash_pwd = hash_password(param.password)

    if user is None:
        raise InvalidCredentialsException

    if not verify_password(param.password, hash_pwd):
        raise InvalidCredentialsException

    access_token = manager.create_access_token(data={"sub": user.login_id})

    return Response(
        content=ujson.dumps(
            Token(access_token=access_token, token_type="bearer").__dict__
        ),
        media_type=MediaTypes.json
    )


@app.post("/create_user")
async def create(param: CreateUser, database: Session = Depends(get_session)):
    result = await actions.create_user(param.login_id, param.user_name, param.password, database)
    return Response(
        content=ujson.dumps(result.data.__dict__),
        media_type=MediaTypes.json
    )


@app.post("/chat-message")
async def handle_chat_message(req: ChatTextRequest, database: Session = Depends(get_session)):
    headers = {
        "Content-Type": MediaTypes.json,
        "Authorization": f"Bearer {openai.api_key}",
    }
    payload = {
        "prompt": f"\nAI: {req.ai_prompt}\nUSER: {req.user_prompt}",
        "temperature": Config.api_temperature,
        "max_tokens": Config.api_max_token,
        "stop": None,
        "n": 1,
        "logprobs": None,
        "echo": False,
        "user": req.user or ""
    }

    import uuid
    from common_func.to_json import to_json
    uuid = (uuid.uuid4()).__str__()
    openai_request_url = f"https://api.openai.com/v1/engines/{Config.api_model}/completions"
    if req.user == "":
        # Start a new conversation
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    openai_request_url,
                    headers=headers,
                    json={"prompt": ""},
            ) as response:
                response_json = await response.json()
                print(response_json)
                payload["user"] = response_json["id"]

        # Send the first prompt to the AI
        payload["prompt"] = f"{req.user_prompt}\nAI:"
        create_chat_room = await actions.create_chat_list(prompt=req.user_prompt, uuid=uuid, db=database)
        print(ujson.dumps(to_json(create_chat_room.data)))
        if create_chat_room.result is False:
            return Response(content=ujson.dumps(to_json(create_chat_room.data)), media_type=MediaTypes.json)

    if not payload["prompt"].endswith("AI:"):
        payload["prompt"] = f"\nUSER:{req.user_prompt}\nAI:"

    async with aiohttp.ClientSession() as session:
        async with session.post(
                openai_request_url,
                headers=headers,
                json=payload,
                params={"stream": "true"},
        ) as response:
            # Retrieve messages from the conversation
            messages = await response.json()
            completions = messages["choices"]
            print(messages)

            # Extract the text from the AI response
            text = completions[0]["text"].strip()

            # Get the conversation id from the response (if it has changed)
            new_conversation_id = messages["id"]
            old_conversation_id = payload["user"]
            history = payload["prompt"] + " " + text
            create_or_update = await actions.create_chat_history(uuid=uuid, history=history, db=database)
            if create_or_update.result is False:
                return Response(content=ujson.dumps(to_json(create_or_update.data)), media_type=MediaTypes.json)

    # Return the response as a JSON object
    return Response(
        content=ujson.dumps(ChatTextResponse(response=text, previous_conversation_id=old_conversation_id,
                                             conversation_id=new_conversation_id).__dict__),
        media_type=MediaTypes.json,
    )
