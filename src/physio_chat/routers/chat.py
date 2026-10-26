#!/usr/bin/env python3
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from ..schema import ChatQuery, ChatResponse, ChatID, ChatMessage, ChatMessages, Status, ChatOptions

from ..chat_model.model import Model
# from ..chat_model.test_model import Model

router = APIRouter()

def get_model(request: Request) -> Model:
    return request.app.state.model


def initialize_chat(model: Model):
    model.status = Status.INITIALIZING
    try:
        model.start_chat_agent()
        model.status = Status.READY

    except Exception:
        model.status = Status.FAILED
        raise


@router.get('/chat', response_model=list[ChatID])
async def list_chats(model: Model = Depends(get_model)):
    chat_id = model.list_chats()
    return [ChatID(**chat) for chat in chat_id]


@router.post('/chat/params')
async def change_model_parameters(options: ChatOptions, model: Model = Depends(get_model)):
    model.set_options(options)


@router.post('/chat')
async def create_chat(
    background_tasks: BackgroundTasks,
    model: Model = Depends(get_model)
):
    chat_id = model.create_empty_chat()
    background_tasks.add_task(initialize_chat, model)
    return {
        "id": chat_id,
        "status": Status.INITIALIZING
    }

@router.get('/chat/{chat_id}', response_model=ChatMessages)
async def get_chat(chat_id: int, model: Model = Depends(get_model)):
    model.set_chat(chat_id)
    messages =  [ChatMessage(**i) for i in model.get_messages()]
    return ChatMessages(id=chat_id, status=Status.READY, messages=messages)

 
@router.post('/chat/{chat_id}/message', response_model=ChatResponse)
async def message_chat(
        chat_id: int,
        query: ChatQuery,
        model: Model = Depends(get_model)
):
    response = model.get_response(query.query)
    return ChatResponse(query=query.query, response=response)

@router.delete('/chat/{chat_id}')
async def delete_chat(chat_id: int, model: Model = Depends(get_model)):
    model.delete_chat()

