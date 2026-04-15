import re
from pydantic import BaseModel, EmailStr, Field, field_validator

# ==========================================
# REGISTER SCHEMA (The strict bouncer)
# ==========================================
class UserCreate(BaseModel):
    # Username must be between 3 and 50 characters
    username: str = Field(..., min_length=3, max_length=50)
    
    # EmailStr automatically checks if it has a @ and a valid domain
    email: EmailStr 
    
    # Password must be at least 8 characters
    password: str = Field(..., min_length=8)

    # Custom Validator for Password Strength
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value):
        """Checks if the password is actually strong."""
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter')
            
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one number')
            
        if not re.search(r'[\W_]', value):
            raise ValueError('Password must contain at least one special character (e.g., !@#$%)')
            
        return value

# ==========================================
# LOGIN SCHEMA (The chill bouncer)
# ==========================================
class UserLogin(BaseModel):
    # We don't need strict validators here, because if they try to log in
    # with a weak password, it just won't match anything in the DB anyway.
    email: EmailStr
    password: str

# ==========================================
# TOKEN SCHEMA
# ==========================================
class Token(BaseModel):
    access_token: str
    token_type: str

