from app.tasks.celery import test_task


result = test_task.delay()


print(result.get(timeout=5))