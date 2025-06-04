from celery import Celery
from app.core.config import settings
from app.services.parser import WebsiteParser


celery = Celery(
    __name__,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True
)


@celery.task(bind=True)
def parse_website_task(self, url, max_depth, format):
    try:
        parser = WebsiteParser(url, max_depth)
        graph = parser.parse()
        
        if format == "graphml":
            result = parser.to_graphml()
        else:
            result = str(graph)
        
        return {"status": "completed", "result": result}
    
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    

@celery.task
def test_task():
    return "Celery is working!"
