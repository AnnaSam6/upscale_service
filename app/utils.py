import uuid
from datetime import datetime

# Хранилище изображений в памяти (в production - Redis или S3)
image_storage = {}

def generate_file_id() -> str:
    """Генерация уникального ID для файла"""
    return str(uuid.uuid4())

def store_image(image_bytes: bytes) -> str:
    """Сохранение изображения в памяти"""
    file_id = generate_file_id()
    image_storage[file_id] = {
        'data': image_bytes,
        'created_at': datetime.now()
    }
    return file_id

def get_image(file_id: str) -> bytes:
    """Получение изображения из памяти"""
    if file_id not in image_storage:
        return None
    return image_storage[file_id]['data']

def validate_image_file(file) -> tuple:
    """
    Валидация загруженного файла.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Проверка расширения
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    
    if not file.filename:
        return False, "No file selected"
    
    if '.' not in file.filename:
        return False, "Invalid file format"
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        return False, f"Invalid file extension: {ext}. Allowed: {allowed_extensions}"
    
    # Проверка размера (максимум 16MB)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > 16 * 1024 * 1024:
        return False, "File too large. Maximum size is 16MB"
    
    return True, None
