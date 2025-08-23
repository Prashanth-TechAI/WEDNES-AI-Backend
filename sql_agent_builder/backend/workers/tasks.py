from celery import Celery

celery_app = Celery("agent_builder", broker="redis://localhost:6379/0")

@celery_app.task
def example_task():
    return "Task completed successfully!"
