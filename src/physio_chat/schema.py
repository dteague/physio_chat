#!/usr/bin/env python3
from pydantic import BaseModel
from enum import Enum

class Status(str, Enum):
    READY = "ready"
    WORKING = "working"
    INITIALIZING = 'initializing'
    FAILED = "failed"

class ChatID(BaseModel):
    id: int
    title: str

class ChatQuery(BaseModel):
    query: str

class ChatResponse(BaseModel):
    query: str
    response: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatMessages(BaseModel):
    id: int
    status: Status
    messages: list[ChatMessage]
