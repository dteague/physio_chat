#!/usr/bin/env python3
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from physio_chat.schema import ChatQuery, ChatResponse
from .routers import web, chat

app = FastAPI()

origins = [
    "http://localhost",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from .chat_model.model import Model
# from .chat_model.test_model import Model

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = Model()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(web.router)
app.include_router(chat.router)

@app.get('/health')
async def server_on():
    return True


