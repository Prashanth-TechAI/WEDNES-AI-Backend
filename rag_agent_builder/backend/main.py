from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables (from .env)
load_dotenv()

# Import routers
from .routers import config_flow, build, preview, download

# Create FastAPI app
app = FastAPI(title="RAG Agent Builder")

# Register all routers
app.include_router(config_flow.router)
app.include_router(build.router)
app.include_router(preview.router)
app.include_router(download.router)
