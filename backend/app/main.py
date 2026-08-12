from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import Base, engine
from app.models import Board, Card, Column, User
from app.routers import auth, boards, cards

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(boards.router, prefix="/api/boards", tags=["boards"])
app.include_router(cards.router, prefix="/api", tags=["cards"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
