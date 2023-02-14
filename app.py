import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Response
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from sqlalchemy.orm import Session

from config import Config
from classes import Token, CreateUser
from custom_class import MediaTypes, LoginParam, TextRequest, TextResponse, ChatTextRequest, ChatTextResponse
from verify import hash_password, verify_password
from database import get_session
from database.actions import actions
from datetime import timedelta
from common_func.to_json import to_json
import ujson
import openai
import aiohttp

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
        content=ujson.dumps(to_json(result)),
        media_type=MediaTypes.json
    )


@app.post("/chat")
async def chat(req: TextRequest):
    prompt = req.prompt
    model = req.model
    length = req.length
    response = await generate_text(prompt, model, length)
    return Response(
        content=ujson.dumps(TextResponse(response=response).__dict__),
        media_type=MediaTypes.json
    )


@app.post("/chat-message")
async def handle_chat_message(req: ChatTextRequest):
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
    if req.user == "":
        # Start a new conversation
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    openai_request_url,
                    headers=headers,
                    json=payload,
            ) as response:
                response_json = await response.json()
                print(response_json)
                payload["user"] = response_json["id"]

        # Send the first prompt to the AI
        payload["prompt"] = f"{req.user_prompt}\nAI:"

    async with aiohttp.ClientSession() as session:
        async with session.post(
                openai_request_url,
                headers=headers,
                json=payload,
                params={"stream": "true"},
        ) as response:

            # Retrieve messages from the conversation
            messages = await response.json()
            print("message: ", messages)
            completions = messages["choices"]

            # Extract the text from the AI response
            text = completions[0]["text"].strip()

            # Get the conversation id from the response (if it has changed)
            new_conversation_id = messages["id"]
            old_conversation_id = payload["user"]

    # Return the response as a JSON object
    return Response(
        content=ujson.dumps(ChatTextResponse(response=text, previous_conversation_id=old_conversation_id, conversation_id=new_conversation_id).__dict__),
        media_type=MediaTypes.json,
    )


# Define async function to generate text
async def generate_text(prompt, model, length):
    import copy
    completions = []
    headers = {
        "Content-Type": MediaTypes.json,
        "Authorization": f"Bearer {openai.api_key}",
    }
    json = {
        "prompt": prompt,
        "max_tokens": length,
        "n": 1,
        "stop": None
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"https://api.openai.com/v1/engines/{model}/completions",
                headers=headers,
                json=json,
        ) as response:
            response = await response.json()
            completions.append(response["choices"][0]["text"])
            while "incomplete" in response["choices"][0]:
                text = response["choices"][0]["text"]
                prompt = text[text.rfind("\n") + 1:]
                copied_json = copy.deepcopy(json)
                copied_json["prompt"] = prompt
                print(prompt)
                async with session.post(
                        "https://api.openai.com/v1/engines/" + model + "/completions",
                        headers=headers,
                        json=copied_json,
                ) as response:
                    response = await response.json()
                    completions.append(response["choices"][0]["text"])
    return "".join(completions)