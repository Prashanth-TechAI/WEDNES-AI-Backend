from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.database import get_db
from auth.models import ApiKey
from auth.utils import get_current_user, encrypt_api_key, decrypt_api_key
from auth.schemas import APIKeyCreate, APIKeyOut

router = APIRouter()

@router.post("/apikeys", response_model=dict)
def store_api_key(payload: APIKeyCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    encrypted = encrypt_api_key(payload.key)

    db_key = ApiKey(user_id=user.id, provider=payload.provider, key=encrypted)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)

    return {"msg": "API key stored successfully", "id": db_key.id}

@router.get("/apikeys", response_model=list[APIKeyOut])
def list_api_keys(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(ApiKey).filter(ApiKey.user_id == user.id).all()

@router.delete("/apikeys/{key_id}", response_model=dict)
def delete_api_key(key_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(api_key)
    db.commit()
    return {"msg": "API key deleted"}
