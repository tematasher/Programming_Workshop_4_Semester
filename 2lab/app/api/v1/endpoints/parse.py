from fastapi import APIRouter, Depends, BackgroundTasks
from app.schemas.parse import ParseWebsiteRequest, ParseStatusResponse
from app.tasks.celery import parse_website_task, celery_app, parse_website_task
from celery.result import AsyncResult
from app.services.parser import WebsiteParser
from app.models.user import User
from app.crud.user import get_current_user_ws


router = APIRouter()


@router.post("/test_parser/")
def test_parser(request: ParseWebsiteRequest):
    parser = WebsiteParser(request.url, request.max_depth)
    graph = parser.parse()
    return {
        "nodes": list(graph.nodes),
        "edges": list(graph.edges)
    }


@router.post("/parse_website/")
async def parse_website(
    request: ParseWebsiteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_ws),
):
    task = parse_website_task.delay(
        user_id=current_user.email,
        url=request.url,
        max_depth=request.max_depth,
        format=request.format
    )
    return {"task_id": task.id}


@router.get("/parse_status/", response_model=ParseStatusResponse)
def parse_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    response_data = {
        "status": task_result.state,
        "progress": 0,
        "result": None
    }
    
    if task_result.state == "PROGRESS":
        response_data["progress"] = task_result.info.get("progress", 0)
    elif task_result.state == "SUCCESS":
        result = task_result.result
        if isinstance(result, dict) and result.get("status") == "completed":
            response_data["result"] = result.get("result")
        elif isinstance(result, str):
            response_data["result"] = result
        else:
            response_data["result"] = str(result)
    
    return response_data
