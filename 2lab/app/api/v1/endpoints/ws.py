from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket.manager import manager
from app.core.security import get_current_user_ws
from app.schemas.token import TokenData


router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
):
    user: TokenData = await get_current_user_ws(token)
    if not user:
        await websocket.close(code=1008)
        return
    
    await manager.connect(user.email, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user.email, websocket)
