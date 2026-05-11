import cv2
from cv2 import dnn_superres
import numpy as np
import io
import os

# Глобальная переменная для модели (загружается ОДИН раз)
_scaler = None

def load_model(model_path: str = None):
    """
    Загрузка модели один раз.
    Модель загружается при первом вызове и сохраняется в глобальной переменной.
    """
    global _scaler
    
    if _scaler is None:
        if model_path is None:
            # Путь к модели относительно текущего файла
            model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                '..', 
                'model', 
                'EDSR_x2.pb'
            )
        
        _scaler = dnn_superres.DnnSuperResImpl_create()
        _scaler.readModel(model_path)
        _scaler.setModel("edsr", 2)
        
    return _scaler

def upscale_from_bytes(image_bytes: bytes) -> bytes:
    """
    Апскейлинг изображения из байтов (без сохранения на диск).
    
    Args:
        image_bytes: байты изображения
    
    Returns:
        bytes: обработанное изображение в формате PNG
    """
    # Загружаем модель (только при первом вызове)
    scaler = load_model()
    
    # Декодируем байты в numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("Cannot decode image")
    
    # Выполняем апскейлинг
    result = scaler.upsample(image)
    
    # Кодируем результат обратно в байты (без сохранения на диск)
    _, buffer = cv2.imencode('.png', result)
    
    return buffer.tobytes()

def upscale(input_path: str, output_path: str, model_path: str = 'EDSR_x2.pb') -> None:
    """
    Оригинальная функция для обратной совместимости.
    
    :param input_path: путь к изображению для апскейла
    :param output_path: путь к выходному файлу
    :param model_path: путь к ИИ модели
    """
    scaler = load_model(model_path)
    image = cv2.imread(input_path)
    result = scaler.upsample(image)
    cv2.imwrite(output_path, result)

def example():
    """Пример использования"""
    upscale('lama_300px.png', 'lama_600px.png')

if __name__ == '__main__':
    example()
