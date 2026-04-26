from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.game import router as game_router

app = FastAPI(title="AI Time-Travel Explorer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)
