#!/usr/bin/env python3
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from physio_chat.schema import ChatQuery, ChatResponse
from .routers import web, chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from .graph.chat_service import ChatService
from .graph.history import HistoryDB
from .graph.builder import builder

# from .chat_model.test_model import Model
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = builder.compile()
    app.state.history = HistoryDB() 
    app.state.service = ChatService(
        app.state.graph,
        app.state.history
    )
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(web.router)
app.include_router(chat.router)

@app.get('/health')
async def server_on():
    return True


