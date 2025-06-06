from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket.manager import manager
from app.core.security import get_current_user_ws
from app.schemas.token import TokenData
from app.tasks.celery import parse_website_task
from db.session import get_db
from sqlalchemy.orm import Session
import json

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    await websocket.accept()
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=1008)
        return
    await manager.connect(user.email, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                command = json.loads(data)
                if command.get("command") == "parse":
                    task = parse_website_task.delay(
                        user_id=user.email,
                        url=command["url"],
                        max_depth=command.get("max_depth", 2),
                        format=command.get("format", "graphml")
                    )
                    # Отправляем подтверждение клиенту
                    await websocket.send_json({
                        "status": "TASK_STARTED",
                        "task_id": task.id
                    })
            except json.JSONDecodeError:
                pass
            
            except WebSocketDisconnect:
                await manager.disconnect(user.email, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(user.email, websocket)
