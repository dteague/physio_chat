from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

router = APIRouter()

router.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@router.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request, name="test.html")

@router.get('/favicon.ico')
async def favicon():
    return FileResponse('static/favicon.ico')
