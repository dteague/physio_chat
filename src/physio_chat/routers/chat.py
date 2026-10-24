#!/usr/bin/env python3
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..chat_model.model import Model

router = APIRouter()

def get_model(request: Request) -> Model:
    return request.app.state.model


@router.post('/chats')
async def create_chat(model: Model = Depends(get_model)):
    print(model.LANG_MODEL)
    return model.LANG_MODEL
    #

@router.get('/chats/{chat_id}')
async def get_chat(chat_id: int, model: Model = Depends(get_model)):
    pass
 
@router.post('/chats/{chat_id}')
async def return_to_chat(chat_id: int, model: Model = Depends(get_model)):
    pass


@router.post('/chats/{chat_id}/messages')
async def message_chat(chat_id: int, model: Model = Depends(get_model)):
    pass

@router.post('/chats/{chat_id}')
async def delete_chat(chat_id: int, model: Model = Depends(get_model)):
    pass

