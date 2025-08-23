from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import EmailStr
from . import models, schemas, utils
from .database import SessionLocal, get_db

router = APIRouter()

@router.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=utils.hash_password(user.password),
        oauth_provider=""
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User created successfully"}

@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not utils.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = utils.create_token({"sub": db_user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": db_user.email,
            "username": db_user.username
        }
    }

@router.post("/forgot-password")
def forgot_password(email: EmailStr, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    token = utils.create_reset_token(email)

    from os import getenv
    frontend_url = getenv("FRONTEND_RESET_URL", "http://localhost:8080/reset-password")
    reset_link = f"{frontend_url}?token={token}"

    background_tasks.add_task(utils.send_reset_email, email, reset_link)
    return {"msg": "Password reset email sent"}

@router.post("/reset-password")
def reset_password(data: schemas.ResetPassword, db: Session = Depends(get_db)):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    email = utils.verify_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = utils.hash_password(data.new_password)
    db.commit()
    return {"msg": "Password reset successful"}
