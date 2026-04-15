from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

import models
import security
from database import get_db

# This tells FastAPI where the frontend goes to get a token.
# Magic trick: This single line creates the "Authorize" padlock button in your Swagger UI!
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    The main security guard. It intercepts the request, reads the JWT token
    from the header, and checks if it's valid and if the user still exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Crack open the token using our secret key
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        
        # 2. Extract the email (we saved it as "sub" during login)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
    except JWTError:
        # If the token is expired, fake, or corrupted, block them immediately
        raise credentials_exception

    # 3. Look up the user in the database
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception

    # 4. Bank-Grade Check: Are they deactivated?
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This account has been deactivated."
        )

    # If they pass all checks, hand the user object to the endpoint
    return user