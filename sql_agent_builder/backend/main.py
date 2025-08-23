from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import os
# Load environment variables
load_dotenv()

# Import routers
from .routers import config_flow, build, preview, download

# Create FastAPI app
app = FastAPI(title="AI Agent Builder")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/step0.html")

# Register all routers
app.include_router(config_flow.router, prefix="/config", tags=["Config"])
app.include_router(build.router, prefix="/build", tags=["Builder"])
app.include_router(preview.router, prefix="/previews", tags=["Preview"])
app.include_router(download.router, tags=["Download"])
