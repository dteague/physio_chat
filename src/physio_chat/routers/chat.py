#!/usr/bin/env python3
from typing_extensions import Annotated
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from ..schema import ChatQuery, ChatResponse, ChatID, ChatMessage, ChatMessages, Status, ChatOptions

from langgraph.graph.state import CompiledStateGraph

from ..graph.chat_service import ChatService
from ..graph.history import HistoryDB

def get_chat_service(request: Request) -> ChatService:
    return request.app.state.service

ChatServiceDep = Annotated[
    ChatService, Depends(get_chat_service)
]

router = APIRouter()


def initialize_chat(chat_id: int, service: ChatServiceDep):
    try:
        service.initialize_chat(chat_id)
    except Exception:
        service.status = Status.FAILED
        raise


@router.get('/chat', response_model=list[ChatID])
async def list_chats(service: ChatServiceDep):
    chat_id = service.list_chats()
    return [ChatID(**chat) for chat in chat_id]


@router.post('/chat/params')
async def change_model_parameters(
    options: ChatOptions,
    service: ChatServiceDep
):
    service.set_options(options)


@router.post('/chat')
async def create_chat(
    background_tasks: BackgroundTasks,
    service: ChatServiceDep
):
    chat_id = service.create_empty_chat()
    background_tasks.add_task(initialize_chat, chat_id, service)
    return {
        "id": chat_id,
        "status": Status.INITIALIZING
    }

@router.get('/chat/{chat_id}', response_model=ChatMessages)
async def get_chat(chat_id: int, service: ChatServiceDep):
    service.set_chat(chat_id)
    messages =  [ChatMessage(**i) for i in service.get_messages(chat_id)]
    return ChatMessages(id=chat_id, status=service.status, messages=messages)

@router.get('/chat/{chat_id}/status')
async def get_chat_status(chat_id: int, service: ChatServiceDep):
    return service.status
 
@router.post('/chat/{chat_id}/message', response_model=ChatResponse)
async def message_chat(
        chat_id: int,
        query: ChatQuery,
        service: ChatServiceDep
):
    response = service.get_response(chat_id, query.query)
    return ChatResponse(query=query.query, response=response)

@router.delete('/chat/{chat_id}')
async def delete_chat(chat_id: int, service: ChatServiceDep):
    service.delete_chat(chat_id)

