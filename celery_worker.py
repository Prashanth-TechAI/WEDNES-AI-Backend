from celery import Celery

# Create a unified Celery app
celery_app = Celery(
    "wednes_ai",
    broker="redis://localhost:6379/0",  # Or read from .env
    backend="redis://localhost:6379/0"
)

# Auto-discover tasks from both pipelines
celery_app.autodiscover_tasks([
    "rag_agent_builder.backend.workers.tasks",
    "sql_agent_builder.backend.workers.tasks"
])

if __name__ == "__main__":
    celery_app.worker_main()
