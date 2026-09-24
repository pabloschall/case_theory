from celery import Celery  # type: ignore[import-untyped]

from app.config.settings import get_settings

settings = get_settings()
celery_app = Celery("eillen", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_hijack_root_logger=False,
    imports=("app.auth.tasks", "app.cases.tasks", "app.integrations.fbi.tasks"),
    task_always_eager=settings.environment == "test",
)


@celery_app.task(name="system.healthcheck")  # type: ignore[untyped-decorator]
def healthcheck() -> str:
    return "ok"
