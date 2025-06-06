import os
import json
from app.websocket.manager import manager
from datetime import datetime
import logging
from celery import Celery, shared_task
from redis import Redis
from app.core.config import settings
from app.services.parser import WebsiteParser
from app.db.session import SessionLocal
from app.crud.parse import create_parse_history, update_parse_history
import networkx as nx

logger = logging.getLogger(__name__)


celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)


celery_app.conf.update(
    task_track_started=True,
    result_extended=True
)
    

@celery_app.task
def test_task():
    return "Celery is working!"


@celery_app.task(bind=True)
def parse_website_task(self, user_id, url, max_depth, format):
    db = SessionLocal()
    try:
        # Создаем запись в истории
        history = create_parse_history(db, user_id, url, max_depth)
        task_id = self.request.id
        
        # Обновляем состояние задачи
        self.update_state(state='PROGRESS', meta={
            'progress': 0,
            'history_id': history.id  # сохраняем ID истории в meta
        })
        
        # Парсинг (существующая логика)
        parser = WebsiteParser(url, max_depth)
        graph = parser.parse()
        
        # Сохраняем результат в файл
        filename = f"graph_{task_id}.{format}"
        filepath = os.path.join("results", filename)
        os.makedirs("results", exist_ok=True)
        if format == "graphml":
            nx.write_graphml(graph, filepath)
        elif format == "gexf":
            nx.write_gexf(graph, filepath)
        
        # Обновляем запись в истории
        update_parse_history(db, history.id, "COMPLETED", filepath)
        
        return {"status": "completed", "result": filepath, "total_pages": len(graph.nodes)}
    except Exception as e:
        # Обновляем статус при ошибке
        if history:
            update_parse_history(db, history.id, "FAILED")
        raise e
    finally:
        db.close()