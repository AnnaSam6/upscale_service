import base64
import io
from flask import Flask, request, jsonify, send_file
from celery.result import AsyncResult

from .tasks import upscale_image_task
from .utils import validate_image_file, store_image, get_image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

@app.route('/upscale', methods=['POST'])
def upscale():
    """
    Загрузка изображения для апскейлинга.
    
    Request:
        - file: изображение (multipart/form-data)
    
    Response:
        - task_id: ID задачи
    """
    # Проверка наличия файла
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Валидация файла
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        # Читаем файл в байты
        image_bytes = file.read()
        
        # Кодируем в base64 для передачи в Celery
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Запускаем задачу
        task = upscale_image_task.delay(image_base64)
        
        return jsonify({
            'task_id': task.id,
            'status': 'Task created',
            'message': 'Image processing started'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """
    Получение статуса задачи.
    
    Returns:
        - status: статус задачи
        - download_url: ссылка на результат (если выполнена)
    """
    task = upscale_image_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'pending',
            'message': 'Task is waiting in queue'
        }
    elif task.state == 'STARTED':
        response = {
            'status': 'processing',
            'message': 'Task has started'
        }
    elif task.state == 'PROCESSING':
        response = {
            'status': 'processing',
            'message': 'Image is being processed'
        }
    elif task.state == 'SUCCESS':
        # Получаем результат
        result = task.result
        
        # Декодируем изображение из base64
        image_bytes = base64.b64decode(result['image_base64'])
        
        # Сохраняем в памяти и получаем ID
        file_id = store_image(image_bytes)
        
        response = {
            'status': 'completed',
            'message': 'Image processed successfully',
            'download_url': f'/processed/{file_id}',
            'original_size': result.get('original_size'),
            'result_size': result.get('result_size')
        }
    elif task.state == 'FAILURE':
        response = {
            'status': 'error',
            'message': str(task.info)
        }
    elif task.state == 'RETRY':
        response = {
            'status': 'retry',
            'message': 'Task is being retried'
        }
    else:
        response = {
            'status': task.state,
            'message': 'Unknown state'
        }
    
    return jsonify(response)

@app.route('/processed/<file_id>', methods=['GET'])
def get_processed_file(file_id: str):
    """
    Получение обработанного файла.
    
    Args:
        file_id: ID файла из ответа /tasks/<task_id>
    """
    image_bytes = get_image(file_id)
    
    if image_bytes is None:
        return jsonify({'error': 'File not found or expired'}), 404
    
    # Отправляем файл
    return send_file(
        io.BytesIO(image_bytes),
        mimetype='image/png',
        as_attachment=True,
        download_name=f'upscaled_{file_id}.png'
    )

@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности сервиса"""
    return jsonify({
        'status': 'healthy',
        'service': 'Upscale Service',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
