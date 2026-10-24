#!/usr/bin/env python3
from contextlib import asynccontextmanager
from fastapi import FastAPI
from physio_chat.schema import ChatQuery, ChatResponse
from .routers import web, chat

from .chat_model.model import Model

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = Model()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(web.router)
app.include_router(chat.router)

@app.get('/health')
async def server_on():
    pass


