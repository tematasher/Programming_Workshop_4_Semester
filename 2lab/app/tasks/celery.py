import time
import json
from app.websocket.manager import manager
from datetime import datetime
import logging
from celery import Celery, shared_task
from redis import Redis
from app.core.config import settings
from app.services.parser import WebsiteParser


rl = Redis(settings.REDISLITE_PATH)

logger = logging.getLogger(__name__)

celery_app = Celery(
    "tasks",
    broker=rl,
    backend=rl,
)


celery_app.conf.update(
    task_track_started=True,
    result_extended=True,
    broker_transport_options={"visibility_timeout": 3600},
)


@celery_app.task(bind=True)
def parse_website_task(self, url, max_depth, format):
    logger.info(f"Starting parsing task for: {url}")
    try:
        self.update_state(state='PROGRESS', meta={'progress': 10})
        
        parser = WebsiteParser(url, max_depth)
        graph = parser.parse()
        
        self.update_state(state='PROGRESS', meta={'progress': 80})
        
        if format == "graphml":
            result = parser.to_graphml()
        else:
            result = str(graph)
        
        return {"status": "completed", "result": result}
    
    except Exception as e:
        logger.error(f"Parsing failed: {str(e)}")
        return {"status": "failed", "error": str(e)}
    

@celery_app.task
def test_task():
    return "Celery is working!"


@shared_task(bind=True)
def parse_website_task(self, user_id: str, url: str, max_depth: int, format: str):
    start_time = datetime.now()
    parser = WebsiteParser(url, max_depth)
    total_urls = 0
    processed_urls = 0
    
    manager.send_personal_message(
        user_id,
        {
            "status": "STARTED",
            "task_id": self.request.id,
            "url": url,
            "max_depth": max_depth
        }
    )
    
    def progress_callback(current, total):
        nonlocal processed_urls, total_urls
        processed_urls = current
        total_urls = total
        
        progress = int((current / total) * 100) if total > 0 else 0
        manager.send_personal_message(
            user_id,
            {
                "status": "PROGRESS",
                "task_id": self.request.id,
                "progress": progress,
                "current_url": parser.current_url,
                "pages_parsed": current,
                "total_pages": total,
                "links_found": parser.total_links
            }
        )
    
    parser.set_progress_callback(progress_callback)
    graph = parser.parse()
    
    if format == "graphml":
        result = parser.to_graphml()
    else:
        result = json.dumps(graph)
    
    elapsed_time = datetime.now() - start_time
    elapsed_str = str(elapsed_time).split(".")[0]
    
    manager.send_personal_message(
        user_id,
        {
            "status": "COMPLETED",
            "task_id": self.request.id,
            "total_pages": processed_urls,
            "total_links": parser.total_links,
            "elapsed_time": elapsed_str,
            "result": result[:5000] + "..." if len(result) > 5000 else result
        }
    )
    
    return result
