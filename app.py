from datetime import timedelta

import aiohttp
import openai
import ujson
from fastapi import Depends, FastAPI, Response
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from sqlalchemy.orm import Session

from classes import Token, CreateUser
from config import Config
from custom_class import MediaTypes, LoginParam, ChatTextRequest, ChatTextResponse
from database import get_session
from database.actions import actions
from verify import hash_password, verify_password

openai.api_key = "YOUR_API_KEY"

manager = LoginManager(
    Config.secret,
    Config.token_url,
    cookie_name="oai",
    use_cookie=True,
    default_expiry=timedelta(hours=6)
)
app = FastAPI()


@app.post(Config.token_url)
async def login(param: LoginParam, database: Session = Depends(get_session)):
    user = await actions.get_user_by_login_id(param.login_id, database)
    hash_pwd = hash_password(param.password)
    if user is None:
        raise InvalidCredentialsException

    if not verify_password(param.password, hash_pwd):
        raise InvalidCredentialsException

    return Response(
        content=ujson.dumps(
            Token(access_token=manager.create_access_token(data={"sub": user.login_id}), token_type="bearer").__dict__
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
        "temperature": 0.8,
        "max_tokens": req.length,
        "stop": None,
        "n": 1,
        "logprobs": None,
        "echo": False,
        "user": req.user or ""
    }

    openai_request_url = f"https://api.openai.com/v1/engines/{req.model}/completions"
    import uuid
    uuid = (uuid.uuid4()).__str__()
    if req.user == "":
        # Start a new conversation
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    openai_request_url,
                    headers=headers,
                    json=payload,
            ) as response:
                response_json = await response.json()
                payload["user"] = response_json["id"]

        # Send the first prompt to the AI
        payload["prompt"] = f"{req.user_prompt}\nAI:"
        create_chat_room = await actions.create_chat_list(prompt=req.user_prompt, uuid=uuid, db=database)
        if create_chat_room.result is False:
            return Response(content=ujson.dumps(create_chat_room.data.__dict__), media_type=MediaTypes.json)

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

            # Extract the text from the AI response
            text = completions[0]["text"].strip()

            # Get the conversation id from the response (if it has changed)
            new_conversation_id = messages["id"]
            old_conversation_id = payload["user"]
            history = payload["prompt"] + " " + text
            create_or_update = await actions.create_chat_history(uuid=uuid, history=history, db=database)
            if create_or_update.result is False:
                return Response(content=ujson.dumps(create_or_update.json()), media_type=MediaTypes.json)

    # Return the response as a JSON object
    return Response(
        content=ujson.dumps(ChatTextResponse(response=text, previous_conversation_id=old_conversation_id, conversation_id=new_conversation_id).__dict__),
        media_type=MediaTypes.json,
    )