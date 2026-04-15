from pydantic import BaseModel, EmailStr

# This is what the data frontend sends us when a user registers
class UserCreate(BaseModel):
    username: str
    email: str 
    password: str

# This is what the data the frontend must  send us when a user logs in
class UserLogin(BaseModel):
    email: str
    password: str

# This is what we will send BACK to the frontend upon successful login
class Token(BaseModel):
    access_token: str
    token_type: str