from typing import Callable, Iterator, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from sqlalchemy import and_
from database.models import User, ChatList, ChatHistory
from response_classe import CommonResponse
from verify import hash_password


async def get_user_by_login_id(
        login_id: str,
        db: Optional[Session] = None,
        session_provider: Callable[[], Iterator[Session]] = None
) -> Optional[User]:

    if db is None and session_provider is None:
        raise ValueError("db and session_provider cannot both be None.")

    if db is None:
        db = next(session_provider())

    user: Optional[User] = db.query(User).filter(and_(User.login_id == login_id)).first()
    print(user)

    return user


async def create_user(login_id: str, name: str, password: str, db: Session) -> CommonResponse:
    """
    Creates and commits a new user object to the database
    Args:
        login_id: user's login id
        name: The name of the user
        password: The plaintext password
        db: The active db session
    Returns:
        The newly created user.
    """
    hashed_pw = hash_password(password)
    user = User(login_id=login_id, user_name=name, password=hashed_pw)
    try:
        db.begin()
        db.add(user)
        db.flush()
        return CommonResponse(data=user, result=True)
    except OperationalError:
        db.rollback()
        db.close()
        return CommonResponse(data=user, result=False)


async def create_chat_list(prompt: str, uuid: str, db: Session) -> CommonResponse:
    chat = ChatList(id=uuid, name=prompt, user_id="")
    try:
        db.begin()
        db.add(chat)
        db.flush()
        db.close()
        return CommonResponse(data=chat, result=True)
    except OperationalError:
        db.rollback()
        db.close()
        return CommonResponse(data=chat, result=False)


async def create_chat_history(uuid: str, history: str, db: Session) -> CommonResponse:
    db.begin()
    data = None
    select_chat_list = db.query(ChatList).filter(and_(ChatList.id == uuid)).first()
    if select_chat_list:
        select_result = db.query(ChatHistory).filter(and_(ChatHistory.chat_id == select_chat_list.id)).first()
        if select_result:
            select_result.history = history
            data = CommonResponse(data=ChatHistory(id=select_result.id, history=history, chat_id=select_result.chat_id),
                                  result=None)

        if not select_result:
            new_history = ChatHistory(id=None, history=history, chat_id=select_result.id)
            data = CommonResponse(data=new_history, result=None)
            db.add(new_history)

        try:
            db.flush()
            data.result = True
        except OperationalError:
            db.rollback()
            data.result = False
        finally:
            db.close()
    if not select_chat_list:
        db.close()
        return CommonResponse(data=None, result=False)

    return data

