from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    # Core Identity
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # V2: Status Flags
    is_active = Column(Boolean, default=True)  
    is_verified = Column(Boolean, default=False) 

    # V2: OTP & Security Tracking
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)

    # V3: LMS Progress & Dashboard Tracking
    current_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime(timezone=True), nullable=True)
    
    # ─── NEW: Streak & XP Tracking ───
    best_streak = Column(Integer, default=0)  # Highest streak ever achieved
    total_xp = Column(Integer, default=0)     # Total XP earned from day completions

    # Audit Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  

    # Relationships
    progress = relationship("UserProgress", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    day_progress = relationship("DayProgress", back_populates="user")  # NEW


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    
    # Relationships
    progress_records = relationship("UserProgress", back_populates="course")
    day_progress = relationship("DayProgress", back_populates="course")  # NEW


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    progress_percent = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="progress")
    course = relationship("Course", back_populates="progress_records")


# ─── NEW: Day Progress Table ───
class DayProgress(Base):
    __tablename__ = "day_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    day_id = Column(Integer)  # The day/lesson number within the course
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="day_progress")
    course = relationship("Course", back_populates="day_progress")

    # Prevent duplicate completions for the same user/course/day
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', 'day_id', name='unique_user_course_day'),
    )


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    xp_val = Column(Integer, default=0)


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_id = Column(Integer, ForeignKey("badges.id"))
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge")