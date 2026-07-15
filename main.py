from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List

# V2 File Imports
import models
import schemas
import security
import utils
import dependencies
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hawkman Auth API")

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
# 6. HELPER FUNCTIONS FOR PROGRESS
# ==========================================
def get_completed_days(db: Session, user_id: int, course_id: int) -> List[int]:
    records = db.query(models.DayProgress.day_id).filter(
        models.DayProgress.user_id == user_id,
        models.DayProgress.course_id == course_id
    ).all()
    return [r[0] for r in records]


def calculate_unlocked_level(db: Session, user_id: int, course_id: int, total_days: int) -> int:
    completed = get_completed_days(db, user_id, course_id)
    level = 1
    while level in completed and level <= total_days:
        level += 1
    return level


# ==========================================
# 7. COURSE PROGRESS (Day Completion)
# ==========================================
@app.post("/api/progress/{course_id}", response_model=schemas.CourseProgressResponse)
def update_course_progress(
    course_id: int,
    payload: schemas.CourseProgressUpdate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(timezone.utc).date()

    user = db.query(models.User).filter(models.User.id == current_user.id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_day = db.query(models.DayProgress).filter(
        models.DayProgress.user_id == user.id,
        models.DayProgress.course_id == course_id,
        models.DayProgress.day_id == payload.completed_day
    ).first()

    if not existing_day:
        # ─── STREAK LOGIC ───
        last_active_date = user.last_activity_date.date() if user.last_activity_date else None

        if last_active_date is None:
            user.current_streak = 1
            user.last_activity_date = datetime.now(timezone.utc)
        elif last_active_date == today:
            pass  # already updated today
        elif last_active_date == today - timedelta(days=1):
            user.current_streak = (user.current_streak or 0) + 1
            user.last_activity_date = datetime.now(timezone.utc)
        else:
            user.current_streak = 1
            user.last_activity_date = datetime.now(timezone.utc)

        if user.current_streak > (user.best_streak or 0):
            user.best_streak = user.current_streak

        user.total_xp = (user.total_xp or 0) + 10

        new_day = models.DayProgress(
            user_id=user.id,
            course_id=course_id,
            day_id=payload.completed_day,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(new_day)
        db.commit()
        db.refresh(user)

    # You should fetch total_days from the courses table or a config.
    # Hardcoded 28 for now – replace with real data.
    total_days = 28
    unlocked_level = calculate_unlocked_level(db, user.id, course_id, total_days)
    completed_days = get_completed_days(db, user.id, course_id)

    return {
        "streak_count": user.current_streak,
        "total_xp": user.total_xp,
        "unlocked_level": unlocked_level,
        "completed_days": completed_days
    }


# ==========================================
# 8. PROGRESS UPDATE (Percentage)
# ==========================================
@app.post("/api/progress/update", response_model=schemas.ProgressUpdateResponse)
def update_user_progress(
    payload: schemas.ProgressUpdateCreate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(models.UserProgress).filter(
        models.UserProgress.user_id == current_user.id,
        models.UserProgress.course_id == payload.course_id
    ).first()

    if existing:
        existing.progress_percent = payload.progress_percent
        existing.last_updated = datetime.now(timezone.utc)
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
# 9. DASHBOARD STATS
# ==========================================
@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    current_user: models.User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
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

    completed_courses = sum(1 for p in user_progress_records if p.progress_percent >= 100)

    # Badges
    unlocked_badges = []
    streak = current_user.current_streak or 0

    # Streak-based badges
    if streak >= 1:
        unlocked_badges.append({
            "name": "First Steps",
            "tier": "bronze",
            "color": "#CD7F32",
            "icon": "🥉",
            "requirement": "1 day streak"
        })
    if streak >= 5:
        unlocked_badges.append({
            "name": "Speed Learner",
            "tier": "silver",
            "color": "#C0C0C0",
            "icon": "🥈",
            "requirement": "5 day streak"
        })
    if streak >= 7:
        unlocked_badges.append({
            "name": "Week Warrior",
            "tier": "gold",
            "color": "#FFD700",
            "icon": "🥇",
            "requirement": "7 day streak"
        })
    if streak >= 10:
        unlocked_badges.append({
            "name": "Finisher",
            "tier": "platinum",
            "color": "#E5E4E2",
            "icon": "💎",
            "requirement": "10 day streak"
        })

    # Course-based badges
    if completed_courses >= 1:
        unlocked_badges.append({
            "name": "Course Master",
            "tier": "diamond",
            "color": "#B9F2FF",
            "icon": "👑",
            "requirement": "1 course completed"
        })
    if completed_courses >= 3:
        unlocked_badges.append({
            "name": "Learning Legend",
            "tier": "diamond",
            "color": "#B9F2FF",
            "icon": "👑",
            "requirement": "3 courses completed"
        })
    if completed_courses >= 5:
        unlocked_badges.append({
            "name": "AI Scholar",
            "tier": "diamond",
            "color": "#B9F2FF",
            "icon": "👑",
            "requirement": "5 courses completed"
        })

    total_xp = current_user.total_xp or 0

    # Weekly minutes (estimate)
    total_progress_pct = sum(p.progress_percent for p in user_progress_records)
    total_estimated_minutes = int(total_progress_pct * 1.5)
    current_day_index = datetime.now(timezone.utc).weekday()
    weekly_minutes = [0, 0, 0, 0, 0, 0, 0]
    if current_user.last_activity_date and current_user.last_activity_date.date() == datetime.now(timezone.utc).date():
        weekly_minutes[current_day_index] = min(total_estimated_minutes, 240)
    hours_this_week = round(sum(weekly_minutes) / 60, 1)

    return {
        "streak": streak,
        "best_streak": current_user.best_streak or 0,
        "courses_enrolled": len(user_progress_records),
        "completed_courses": completed_courses,
        "total_available_courses": 4,
        "course_progress": course_progress_array,
        "badges_unlocked": unlocked_badges,
        "total_xp": total_xp,
        "weekly_minutes": weekly_minutes,
        "hours_this_week": hours_this_week,
        "recent_activity": []
    }