from sqlalchemy import Integer, Column, String, TEXT, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    login_id = Column(String, unique=True, index=True)
    password = Column(String)
    user_name = Column(String)


class SearchLog(Base):
    __tablename__ = "search_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer)
    use_token = Column(Integer)


class ChatList(Base):
    __tablename__ = "chat_lists"
    id = Column(String(36), primary_key=True, index=True, nullable=False)
    name = Column(String(255), index=True)
    user_id = Column(String(255))
    history = relationship("ChatHistory", back_populates="chatList")


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    history = Column(TEXT)
    chat_id = Column(String(36), ForeignKey("chat_lists.id"))
    chatList = relationship("ChatList", back_populates="history")
