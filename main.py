from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
from Routers.auth_router import router
from Routers import roles
from Routers import role_permissions
from Routers import projects
from Routers import client_router
from Routers import task_router
from Routers import comment_router
from Routers import attachment_router
from Routers import client_bulk_router
from configurations.database import Database
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Database.init()
    yield
app = FastAPI(title="Project Management System", lifespan=lifespan)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.include_router(router)
app.include_router(roles.router)
app.include_router(role_permissions.router)
app.include_router(client_router.router)
app.include_router(projects.router)
app.include_router(task_router.router)
app.include_router(comment_router.router)
app.include_router(attachment_router.router)
app.include_router(client_bulk_router.router)

@app.get("/")
async def health():
    return {"status": "ok"}



