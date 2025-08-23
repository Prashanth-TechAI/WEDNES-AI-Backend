from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.database import get_db
from auth.utils import get_current_user
from auth import models
from pydantic import BaseModel
import uuid, os, datetime

router = APIRouter()

class PipelineCreate(BaseModel):
    name: str
    agent_type: str  # "rag" or "sql"

@router.post("/pipelines", tags=["Agent"])
def create_pipeline(payload: PipelineCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(models.Pipeline).filter_by(user_id=user.id, name=payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent name already exists")

    session_id = str(uuid.uuid4())
    new_pipeline = models.Pipeline(
        user_id=user.id,
        name=payload.name,
        agent_type=payload.agent_type,
        config="{}",
        session_id=session_id,
        created_at=datetime.datetime.utcnow()
    )
    db.add(new_pipeline)
    db.commit()

    builder_root = os.path.join(os.getcwd(), f"{payload.agent_type}_agent_builder")
    os.makedirs(os.path.join(builder_root, "generated_agents", session_id), exist_ok=True)

    return {"msg": "Agent created", "session_id": session_id}

@router.get("/pipelines", tags=["Agent"])
def get_user_pipelines(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.Pipeline).filter_by(user_id=user.id).all()
