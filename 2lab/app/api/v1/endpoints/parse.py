from fastapi import APIRouter, Depends, BackgroundTasks
from app.schemas.parse import ParseWebsiteRequest, ParseStatusResponse
from app.tasks.celery import parse_website_task, celery_app, parse_website_task
from celery.result import AsyncResult
from app.services.parser import WebsiteParser
from app.models.user import User
from app.core.security import get_current_user


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
    current_user: User = Depends(get_current_user),
):
    task = parse_website_task.delay(
        user_id=current_user.email,
        url=request.url,
        max_depth=request.max_depth,
        format=request.format
    )
    return {"task_id": task.id}

@router.get("/parse_status/", response_model=ParseStatusResponse)
async def parse_status(task_id: str):
    task = parse_website_task.AsyncResult(task_id)
    return {
        "status": task.status,
        "progress": task.info.get("progress", 0) if task.info else 0,
        "result": task.result if task.ready() else None
    }


@router.get("/parse_status/")
def parse_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == "PENDING":
        return {"status": "pending", "progress": 0}
    elif task_result.state == "PROGRESS":
        return {
            "status": "in progress",
            "progress": task_result.info.get("progress", 0)
        }
    elif task_result.state == "SUCCESS":
        result = task_result.result
        if result.get("status") == "completed":
            return {
                "status": "completed",
                "result": result["result"]
            }
        else:
            return {
                "status": "failed",
                "error": result.get("error", "Unknown error")
            }
    return {"status": task_result.state}