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
    
    # Password must be at least 8 characters and max 72 for bcrypt
    password: str = Field(..., min_length=8, max_length=72)

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
            
        # THIS WAS MISSING! We must return the password.
        return value

    # ==========================================
    # Catch common email typos
    # ==========================================
    @field_validator('email')
    @classmethod
    def catch_common_email_typos(cls, value):
        # Convert the Pydantic Email object to a normal string
        email_str = str(value).lower()
        
        # A list of common typos you want to block
        blocked_domains = {
            "gmnail.com": "gmail.com",
            "gamil.com": "gmail.com",
            "gmai.com": "gmail.com",
            "yahaoo.com": "yahoo.com",
            "hotmial.com": "hotmail.com"
        }
        
        # Extract the domain part of the email (everything after the @)
        domain = email_str.split('@')[1]
        
        if domain in blocked_domains:
            correct_domain = blocked_domains[domain]
            raise ValueError(f"Invalid domain '{domain}'. Did you mean '{correct_domain}'?")
            
        return value

# ==========================================
# LOGIN SCHEMA (The chill bouncer)
# ==========================================
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# ==========================================
# TOKEN SCHEMA
# ==========================================
class Token(BaseModel):
    access_token: str
    token_type: str

# ==========================================
# OTP VERIFICATION SCHEMA (V2)
# ==========================================
class OTPVerify(BaseModel):
    email: EmailStr
    # Forces the OTP to be exactly 6 characters
    otp_code: str = Field(..., min_length=6, max_length=6) 

# ==========================================
# USER RESPONSE SCHEMA (V2)
# ==========================================
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    
    # This config tells Pydantic it's okay to read data directly 
    # from a SQLAlchemy model object.
    class Config:
        from_attributes = True