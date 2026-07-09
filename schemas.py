from typing import List
import re
from pydantic import BaseModel, EmailStr, Field, field_validator

# ==========================================
# REGISTER SCHEMA (The strict bouncer)
# ==========================================
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr 
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[\W_]', value):
            raise ValueError('Password must contain at least one special character (e.g., !@#$%)')
        return value

    @field_validator('email')
    @classmethod
    def catch_common_email_typos(cls, value):
        email_str = str(value).lower()
        blocked_domains = {
            "gmnail.com": "gmail.com",
            "gamil.com": "gmail.com",
            "gmai.com": "gmail.com",
            "yahaoo.com": "yahoo.com",
            "hotmial.com": "hotmail.com"
        }
        domain = email_str.split('@')[1]
        if domain in blocked_domains:
            correct_domain = blocked_domains[domain]
            raise ValueError(f"Invalid domain '{domain}'. Did you mean '{correct_domain}'?")
        return value


# ==========================================
# LOGIN SCHEMA
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
# OTP VERIFICATION SCHEMA
# ==========================================
class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


# ==========================================
# USER RESPONSE SCHEMA
# ==========================================
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    
    class Config:
        from_attributes = True


# ==========================================
# PROGRESS SCHEMAS (Dashboard)
# ==========================================
class ProgressUpdateCreate(BaseModel):
    user_id: int
    course_id: int
    progress_percent: float

class ProgressUpdateResponse(BaseModel):
    success: bool
    new_streak: int
    badges_unlocked: list[str] = []


# ==========================================
# COURSE PROGRESS SCHEMAS (NEW - For Day Completion)
# ==========================================
class CourseProgressUpdate(BaseModel):
    """Sent from frontend when a user completes a day/lesson."""
    completed_day: int

class CourseProgressResponse(BaseModel):
    """Returned from backend after processing a day completion."""
    streak_count: int
    total_xp: int
    unlocked_level: int
    completed_days: List[int]   # List of day IDs the user has completed