from sqlalchemy import Integer, Column, String
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login_id = Column(String, unique=True, index=True)
    password = Column(String)
    user_name = Column(String)


class SearchLog(Base):
    __tablename__ = "search_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    use_token = Column(Integer)
