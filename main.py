from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

#file imports 
import models
import schemas
import security
from database import engine, get_db

# Create the database tables if they don't exist yet
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hawkman Auth API")


@app.get("/")
def read_root():
    return {"status": "Hawkman Auth API is running smoothly!"}


# ==========================================
# 1. REGISTER ENDPOINT
# ==========================================

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Takes a new user's details, hashes the password, and saves them to the DB.
    """
    # Step 1: Check if the email is already in the database
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        # If they exist, throw a 400 Bad Request error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Step 2: Hash the plain text password using our security vault
    hashed_password = security.get_password_hash(user.password)

    # Step 3: Create the database model (The Blueprint)
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )

    # Step 4: Add them to the database and hit 'save' (commit)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Return a success message (defnitely not the hash!)
    return {"message": "User created successfully", "user_id": new_user.id, "username": new_user.username}


# ==========================================
# 2. LOGIN ENDPOINT
# ==========================================

@app.post("/api/auth/login", response_model=schemas.Token)
def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Verifies an email/password and returns a JWT VIP pass if they match.
    """
    # Step 1: Look up the user by their email
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    # Step 2: If the user doesn't exist, throw a 401 Unauthorized error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: Check if the password they typed matches the hash in the DB
    password_matches = security.verify_password(user_credentials.password, user.password_hash)
    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 4: They passed! Generate their JWT VIP pass
    # We embed their email in the token so the frontend knows who logged in
    access_token = security.create_access_token(data={"sub": user.email})

    # Return the token exactly how the frontend expects it
    return {"access_token": access_token, "token_type": "bearer"}

