from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ResetPassword(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class UserUpdate(BaseModel):
    full_name: Optional[str]
    phone_number: Optional[str]
    bio: Optional[str]
    profile_picture_url: Optional[str]

class APIKeyCreate(BaseModel):
    provider: str
    key: str

class APIKeyOut(BaseModel):
    id: int
    provider: str
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()  # ✅ convert datetime to string
        }

class UserProfile(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    phone_number: Optional[str]
    bio: Optional[str]
    profile_picture_url: Optional[str]
    created_at: Optional[datetime]
    
    class Config:
        orm_mode = True
