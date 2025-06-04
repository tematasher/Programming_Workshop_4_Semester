from fastapi import APIRouter, Query, BackgroundTasks
from app.schemas.parse import ParseWebsiteRequest, ParseStatusResponse
from app.tasks.celery import parse_website_task
from celery.result import AsyncResult

router = APIRouter()

@router.post("/parse_website/")
def parse_website(request: ParseWebsiteRequest):
    task = parse_website_task.delay(
        url=request.url,
        max_depth=request.max_depth,
        format=request.format
    )
    return {"task_id": task.id}


@router.get("/parse_status/", response_model=ParseStatusResponse)
def parse_status(task_id: str = Query(..., alias="task_id")):
    from celery.result import AsyncResult
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {
            "status": "pending",
            "progress": 0,
            "result": None
        }
    elif task_result.state == 'PROGRESS':
        return {
            "status": "in_progress",
            "progress": task_result.info.get('progress', 50),
            "result": None
        }
    elif task_result.state == 'SUCCESS':
        result = task_result.result
        return {
            "status": "completed",
            "progress": 100,
            "result": result.get("result")
        }
    else:  # FAILURE или другие состояния
        return {
            "status": "failed",
            "progress": 0,
            "result": str(task_result.info)  # Информация об ошибке
        }