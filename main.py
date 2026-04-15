from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

# V2 File Imports
import models
import schemas
import security
import utils          # NEW: For OTP generation
import dependencies   # NEW: The Security Guard
from database import engine, get_db

# Create the database tables if they don't exist yet
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hawkman Auth API V2")

# ==========================================
# MIDDLEWARE SETUP
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.get("/")
def read_root():
    return {"status": "Hawkman Auth API V2 is running smoothly!"}


# ==========================================
# 1. REGISTER ENDPOINT (Now with OTP)
# ==========================================
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Step 1: Check if the email exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Step 2: Hash the password
    hashed_password = security.get_password_hash(user.password)

    # Step 3: Generate the OTP (Expires in 10 minutes)
    otp_code = utils.generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Step 4: Create the user (is_verified defaults to False)
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        otp_code=otp_code,
        otp_expires_at=otp_expiry
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Step 5: Send the simulated email
    utils.send_otp_email(email=new_user.email, otp_code=otp_code)

    return {
        "message": "User registered. Please check your email for the OTP.", 
        "email": new_user.email
    }


# ==========================================
# 2. VERIFY OTP ENDPOINT (NEW)
# ==========================================
@app.post("/api/auth/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(payload: schemas.OTPVerify, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Account is already verified."}
    
    # Check if OTP matches and is not expired
    if user.otp_code != payload.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    
    # Ensure datetime comparison is timezone aware
    if user.otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # Success! Mark user as verified and clear the OTP
    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()

    return {"message": "Email verified successfully! You can now log in."}


# ==========================================
# 3. LOGIN ENDPOINT (Now checks verification)
# ==========================================
@app.post("/api/auth/login", response_model=schemas.Token)
def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    if not user or not security.verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

    # V2 Bank Check: Are they verified?
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    # V2 Bank Check: Are they deactivated?
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    # Generate JWT VIP pass
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# ==========================================
# 4. GET PROFILE (Protected Route Example)
# ==========================================
# Notice the Depends(dependencies.get_current_user)! 
# The security guard checks the token before this code ever runs.
@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_profile(current_user: models.User = Depends(dependencies.get_current_user)):
    return current_user


# ==========================================
# 5. DEACTIVATE ACCOUNT (Soft Delete)
# ==========================================
@app.delete("/api/auth/me", status_code=status.HTTP_200_OK)
def deactivate_account(
    current_user: models.User = Depends(dependencies.get_current_user), 
    db: Session = Depends(get_db)
):
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully."}