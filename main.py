from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import calendar

# V2 File Imports
import models
import schemas
import security
import utils          # For OTP generation
import dependencies   # The Security Guard
from database import engine, get_db

# Create the database tables if they don't exist yet
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hawkman Auth API")

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
    return {"status": "Hawkman Auth API is running smoothly!"}


# ==========================================
# 1. REGISTER ENDPOINT
# ==========================================
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(
    user: schemas.UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            existing_user.password_hash = security.get_password_hash(user.password)
            otp_code = utils.generate_otp()
            existing_user.otp_code = otp_code
            existing_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            db.commit()
            
            background_tasks.add_task(utils.send_otp_email, email=existing_user.email, otp_code=otp_code)
            
            return {
                "message": "Unverified account found. New OTP sent to email.", 
                "email": existing_user.email
            }

    hashed_password = security.get_password_hash(user.password)
    otp_code = utils.generate_otp()
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

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

    background_tasks.add_task(utils.send_otp_email, email=new_user.email, otp_code=otp_code)

    return {
        "message": "User registered. Please check your email for the OTP.", 
        "email": new_user.email
    }


# ==========================================
# 2. VERIFY OTP ENDPOINT
# ==========================================
@app.post("/api/auth/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(payload: schemas.OTPVerify, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Account is already verified."}
    
    if user.otp_code != payload.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    
    if user.otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()

    return {"message": "Email verified successfully! You can now log in."}


# ==========================================
# 3. LOGIN ENDPOINT
# ==========================================
@app.post("/api/auth/login", response_model=schemas.Token)
def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    if not user or not security.verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# ==========================================
# 4. GET PROFILE
# ==========================================
@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_profile(current_user: models.User = Depends(dependencies.get_current_user)):
    return current_user


# ==========================================
# 5. DEACTIVATE ACCOUNT
# ==========================================
@app.delete("/api/auth/me", status_code=status.HTTP_200_OK)
def deactivate_account(
    current_user: models.User = Depends(dependencies.get_current_user), 
    db: Session = Depends(get_db)
):
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully."}


# ==========================================
# 6. UPDATE PROGRESS & STREAK (The Dashboard Engine)
# ==========================================
@app.post("/api/progress/update", response_model=schemas.ProgressUpdateResponse)
def update_user_progress(
    payload: schemas.ProgressUpdateCreate, 
    current_user: models.User = Depends(dependencies.get_current_user), 
    db: Session = Depends(get_db)
):
    today = datetime.now(timezone.utc).date()
    last_active = current_user.last_activity_date.date() if current_user.last_activity_date else None

    # Calculate Streak
    if last_active != today:
        if last_active == today - timedelta(days=1):
            current_user.current_streak += 1
        else:
            current_user.current_streak = 1
        current_user.last_activity_date = datetime.now(timezone.utc)

    # UPSERT Logic: Update if exists, otherwise create
    existing_progress = db.query(models.UserProgress).filter(
        models.UserProgress.user_id == current_user.id,
        models.UserProgress.course_id == payload.course_id
    ).first()

    if existing_progress:
        existing_progress.progress_percent = payload.progress_percent
        existing_progress.last_updated = datetime.now(timezone.utc)
    else:
        new_progress = models.UserProgress(
            user_id=current_user.id, 
            course_id=payload.course_id,
            progress_percent=payload.progress_percent
        )
        db.add(new_progress)
    
    db.commit()

    return {
        "success": True, 
        "new_streak": current_user.current_streak, 
        "badges_unlocked": [] 
    }

# ==========================================
# 7. GET DASHBOARD STATS (Dynamically Calculated)
# ==========================================
@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch actual progress
    user_progress_records = db.query(models.UserProgress).filter(
        models.UserProgress.user_id == current_user.id
    ).all()

    course_progress_array = [
        {
            "course_id": record.course_id, 
            "progress_percent": record.progress_percent
        }
        for record in user_progress_records
    ]

    completed_count = sum(p.progress_percent >= 100 for p in user_progress_records)
    
    # --- DYNAMIC BADGE CALCULATION ---
    # We calculate achievements based on existing stats instead of an empty DB table
    unlocked_badges = []
    
    streak = current_user.current_streak or 0 
    
    if streak >= 1:
        unlocked_badges.append("First Steps")
    if streak >= 5:
        unlocked_badges.append("Speed Learner")
    if streak >= 7:
        unlocked_badges.append("Week Warrior")
    if streak >= 10:
        unlocked_badges.append("Finisher")
    if completed_count >= 1:
        unlocked_badges.append("Course Master")
        
    # Estimate XP based on badges
    total_xp = len(unlocked_badges) * 50

    # --- BASIC TIME TRACKING (Until you implement a real session logger) ---
    # We map estimated minutes to the current day of the week
    current_day_index = datetime.now(timezone.utc).weekday()
    weekly_minutes = [0, 0, 0, 0, 0, 0, 0]
    
    # If they are active today, give them some estimated minutes based on their courses
    if current_user.last_activity_date and current_user.last_activity_date.date() == datetime.now(timezone.utc).date():
        active_courses = len(user_progress_records)
        estimated_mins = active_courses * 15 if active_courses > 0 else 10
        weekly_minutes[current_day_index] = estimated_mins

    hours_this_week = round(sum(weekly_minutes) / 60, 1)

    return {
            "streak": streak,                 
            "best_streak": streak,             
            "courses_enrolled": len(user_progress_records),
            "completed_courses": completed_count,
            "total_available_courses": 4, 
            "course_progress": course_progress_array,
            "badges_unlocked": unlocked_badges,
            "total_xp": total_xp,
            "weekly_minutes": weekly_minutes,
            "hours_this_week": hours_this_week,
            "recent_activity": [] 
        }