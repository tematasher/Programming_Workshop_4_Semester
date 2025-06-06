from fastapi import FastAPI
from app.api.v1.router import router as api_router
from app.db.base import Base
from app.db.session import engine
from app.models.user import User
from app.core.config import settings


print(f"Loaded SECRET_KEY: {settings.SECRET_KEY}")


def create_tables():
    Base.metadata.create_all(bind=engine)


app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_tables()


app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Website Parser API"}


