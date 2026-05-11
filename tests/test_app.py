import pytest
import io
import base64
import json
import cv2
import numpy as np
from unittest.mock import patch, MagicMock

from app.main import app
from app.upscale import upscale_from_bytes, load_model

@pytest.fixture
def client():
    """Тестовый клиент Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def sample_image_bytes():
    """Создание тестового изображения в байтах"""
    # Создаем простое изображение
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:] = (255, 0, 0)  # Синий квадрат
    
    _, buffer = cv2.imencode('.png', img)
    return buffer.tobytes()

@pytest.fixture
def sample_image_base64(sample_image_bytes):
    """Тестовое изображение в base64"""
    return base64.b64encode(sample_image_bytes).decode('utf-8')

def test_load_model_once():
    """Тест: модель загружается только один раз"""
    with patch('app.upscale.dnn_superres.DnnSuperResImpl_create') as mock_create:
        mock_scaler = MagicMock()
        mock_create.return_value = mock_scaler
        
        # Первый вызов - должен создать модель
        load_model('test_model.pb')
        assert mock_create.call_count == 1
        
        # Второй вызов - не должен создавать новую
        load_model('test_model.pb')
        assert mock_create.call_count == 1

def test_upscale_from_bytes(sample_image_bytes):
    """Тест функции апскейлинга из байтов"""
    with patch('app.upscale.load_model') as mock_load:
        mock_scaler = MagicMock()
        # Мокаем результат апскейлинга (2x размер)
        mock_scaler.upsample.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
        mock_load.return_value = mock_scaler
        
        result = upscale_from_bytes(sample_image_bytes)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_scaler.upsample.assert_called_once()

def test_upscale_endpoint(client, sample_image_bytes):
    """Тест эндпоинта /upscale"""
    data = {
        'file': (io.BytesIO(sample_image_bytes), 'test.png')
    }
    
    response = client.post(
        '/upscale',
        data=data,
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 202
    data = json.loads(response.data)
    assert 'task_id' in data
    assert data['status'] == 'Task created'

def test_upscale_no_file(client):
    """Тест: запрос без файла"""
    response = client.post('/upscale')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_upscale_invalid_file(client):
    """Тест: неверный формат файла"""
    data = {
        'file': (io.BytesIO(b'not an image'), 'test.txt')
    }
    
    response = client.post(
        '/upscale',
        data=data,
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 400

def test_task_status_pending(client):
    """Тест: статус несуществующей задачи"""
    response = client.get('/tasks/nonexistent-id')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'pending'

def test_processed_file_not_found(client):
    """Тест: запрос несуществующего файла"""
    response = client.get('/processed/nonexistent-id')
    assert response.status_code == 404

def test_health_check(client):
    """Тест: проверка здоровья"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_validate_image_file():
    """Тест: валидация файла"""
    from app.utils import validate_image_file
    
    # Создаем мок файла
    class MockFile:
        def __init__(self, filename, size):
            self.filename = filename
            self._size = size
            self._pos = 0
        
        def seek(self, pos, whence=0):
            if whence == 2:
                self._pos = self._size
            else:
                self._pos = pos
        
        def tell(self):
            return self._pos
    
    # Валидный файл
    valid_file = MockFile('test.png', 1000)
    is_valid, error = validate_image_file(valid_file)
    assert is_valid == True
    
    # Неверное расширение
    invalid_file = MockFile('test.txt', 1000)
    is_valid, error = validate_image_file(invalid_file)
    assert is_valid == False
    
    # Слишком большой файл
    large_file = MockFile('test.png', 17 * 1024 * 1024)
    is_valid, error = validate_image_file(large_file)
    assert is_valid == False
