from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependecies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.crud.user import get_users


router = APIRouter()

@router.get("/users/me/", response_model=UserSchema)
def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user


@router.get("/users/", response_model=list[UserSchema])
def read_users(db: Session = Depends(get_db)):
    users = get_users(db)
    return users