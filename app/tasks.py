import base64
from celery import Task
from . import create_celery_app
from .upscale import upscale_from_bytes

celery = create_celery_app()

class UpscaleTask(Task):
    """Базовый класс задачи с обработкой ошибок"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Обработка ошибок"""
        print(f'Task {task_id} failed: {exc}')

@celery.task(
    bind=True,
    base=UpscaleTask,
    name='upscale_image',
    max_retries=3,
    default_retry_delay=60
)
def upscale_image_task(self, image_data_base64: str) -> dict:
    """
    Задача для апскейлинга изображения.
    
    Args:
        image_data_base64: изображение в формате base64
    
    Returns:
        dict: {
            'status': 'completed',
            'image_base64': обработанное изображение в base64
        }
    """
    try:
        # Обновляем статус
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Processing image...'}
        )
        
        # Декодируем base64
        image_bytes = base64.b64decode(image_data_base64)
        
        # Выполняем апскейлинг
        result_bytes = upscale_from_bytes(image_bytes)
        
        # Кодируем результат в base64
        result_base64 = base64.b64encode(result_bytes).decode('utf-8')
        
        return {
            'status': 'completed',
            'image_base64': result_base64,
            'original_size': len(image_bytes),
            'result_size': len(result_bytes)
        }
        
    except Exception as exc:
        # Пробуем повторить задачу при ошибке
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise
