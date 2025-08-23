from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from auth import schemas, models
from auth.database import get_db
from auth.utils import get_current_user
import os
from uuid import uuid4

router = APIRouter()

UPLOAD_DIR = "static/uploads"

@router.get("/users/me", tags=["User"], response_model=schemas.UserProfile)
def get_profile(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return user

@router.put("/users/me", tags=["User"])
def update_profile(
    full_name: str = Form(...),
    phone_number: str = Form(None),
    bio: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    # Save uploaded image if provided
    if file:
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            buffer.write(file.file.read())
        user.profile_picture_url = f"/{UPLOAD_DIR}/{filename}"

    user.full_name = full_name
    user.phone_number = phone_number
    user.bio = bio
    db.commit()

    return JSONResponse(content={"msg": "Profile updated successfully"})
