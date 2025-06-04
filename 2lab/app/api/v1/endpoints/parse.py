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
    task_result = AsyncResult(task_id)
    
    try:
        if task_result.ready():
            result = task_result.result
            if result and result.get("status") == "completed":
                return {
                    "status": "completed",
                    "progress": 100,
                    "result": result.get("result")
                }
            elif result and result.get("status") == "failed":
                return {
                    "status": "failed",
                    "progress": 0,
                    "result": result.get("error")
                }
        else:
            # Возвращаем статус в процессе выполнения
            return {
                "status": "in_progress",
                "progress": 50,
                "result": None
            }
    except Exception as e:
        return {
            "status": "error",
            "progress": 0,
            "result": str(e)
        }