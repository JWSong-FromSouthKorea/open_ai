from typing import Callable, Iterator, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import get_session
from database.models import User
from verify import hash_password, manager


@manager.user_loader(session_provider=get_session)
async def get_user_by_login_id(
        login_id: str,
        db: Optional[Session] = None,
        session_provider: Callable[[], Iterator[Session]] = None
) -> Optional[User]:
    """
    Queries the database for a user with the given name
    Args:
        login_id: The name of the user
        db: The currently active database session
        session_provider: Optional method to retrieve a session if db is None (provided by our LoginManager)
    Returns:
        The user object or none
    """

    if db is None and session_provider is None:
        raise ValueError("db and session_provider cannot both be None.")

    if db is None:
        db = next(session_provider())

    return db.query(User).filter(and_(User.login_id == login_id)).first()


async def create_user(login_id: str, name: str, password: str, db: Session) -> User:
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
    db.add(user)
    db.commit()
    return user
