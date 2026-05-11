from celery import Celery

def create_celery_app():
    """Создание и настройка Celery приложения"""
    celery = Celery(
        'upscale_service',
        broker='redis://redis:6379/0',
        backend='redis://redis:6379/0'
    )
    
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    
    return celery
