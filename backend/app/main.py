from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.access import board_role
from app.core.config import settings
from app.core.ratelimit import limiter
from app.core.security import decode_access_token
from app.core.ws import manager
from app.db.database import Base, SessionLocal, engine
from app.models import Board, Card, Column, User
from app.routers import auth, boards, cards

Base.metadata.create_all(bind=engine)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas requisições. Tente novamente mais tarde."},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Dados de entrada inválidos"})


app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
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


@app.websocket("/ws/board/{board_id}")
async def board_websocket(websocket: WebSocket, board_id: int, token: str = ""):
    user_id = _websocket_user_id(token)
    if user_id is None:
        await websocket.close(code=1008)
        return
    with SessionLocal() as db:
        user = db.get(User, user_id)
        board = db.get(Board, board_id)
        if user is None or board is None or board_role(db, board, user) is None:
            await websocket.close(code=1008)
            return
    await manager.connect(board_id, websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(board_id, websocket)
    except Exception:
        manager.disconnect(board_id, websocket)


def _websocket_user_id(token: str) -> int | None:
    payload = decode_access_token(token)
    if payload is None:
        return None
    subject = payload.get("sub")
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None
