from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.crud.user import get_user_by_email, create_user
from app.schemas.user import UserCreate, User
from app.schemas.token import Token
from app.core.security import verify_password, create_access_token
from app.db.session import get_db

router = APIRouter()

@router.post("/sign-up/", response_model=User)
def sign_up(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    created_user = create_user(db, user)
    token = create_access_token(data={"sub": created_user.email})
    return {
        "id": created_user.id,
        "email": created_user.email,
        "token": token
    }

@router.post("/login/", response_model=User)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(data={"sub": db_user.email})
    return {
        "id": db_user.id,
        "email": db_user.email,
        "token": token
    }