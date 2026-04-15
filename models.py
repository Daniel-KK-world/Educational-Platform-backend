from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"

    # id: The primary key, auto-increments automatically
    id = Column(Integer, primary_key=True, index=True)
    
    # username: Standard string
    username = Column(String, index=True)
    
    # email: Must be unique (no duplicate accounts allowed)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # password_hash: We never store the real password, only the hashed version
    password_hash = Column(String, nullable=False)