import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from auth import auth as auth_router
from routes import agent as agent_router
from routes import user as user_router
from routes import apikey as apikey_router
from rag_agent_builder.backend.main import app as rag_app
from sql_agent_builder.backend.main import app as sql_app
from img_pipeline.fastapi_app import app as img_app


app = FastAPI(title="Wednes AI - Unified Agent Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(agent_router.router, tags=["Agent"])
app.include_router(user_router.router, tags=["User"])
app.include_router(apikey_router.router, tags=["API Keys"])
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")

app.mount("/rag", rag_app)
app.mount("/sql", sql_app)
app.mount("/img", img_app)

@app.get("/")
def root():
    return {
        "message": "Wednes AI Unified API",
        "routes": {
            "auth": "/auth/docs",
            "rag": "/rag/docs",
            "sql": "/sql/docs"
        }
    }
