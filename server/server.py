from config import DATA_DIR, ENDPOINT, BACKUP_FILE
from flask import Flask, request
from pathlib import Path
import pika
import time

RETRY_CNT = 10

def create_app() -> Flask:
    """
    Create flask application
    """
    app = Flask(__name__)
    app.cnt = 0
    app.connection = None
    app.channel = None
    app.wasError = True

    app.backup = Path(BACKUP_FILE)
    if app.backup.exists():
        app.cnt = int(app.backup.read_text())
    else:
        app.backup.write_text(str(app.cnt))
    print(f'Started with app.cnt: {app.cnt}')

    @app.route(ENDPOINT, methods=['POST'])
    def add_image():
        data = request.get_json(force=True)
        id = app.cnt
        app.cnt += 1
        message = f"{id} {data['url1']} {data['url2']} {DATA_DIR}"

        if app.wasError:
            for i in range(RETRY_CNT):
                try:
                    # app.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost')) # for local tests
                    app.connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq')) # for docker compose
                    app.channel = app.connection.channel()
                    app.channel.queue_declare(queue='task_queue', durable=True)
                    app.channel.confirm_delivery()
                    print('Got connection to task_queue')
                    app.wasError = False
                    break
                except Exception as e:
                    time.sleep(1)
                    print('Waiting for connection to task_queue')
        if app.wasError:
            return {'error': 'No connection to task_queue'}, 504

        try:
            app.channel.basic_publish(
                exchange='',
                routing_key='task_queue',
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2, # persistent message
                )
            )
            app.wasError = False
            app.backup.write_text(str(app.cnt))
            return {"request_id": id}
        except Exception as e:
            app.wasError = True
            return {'error': 'Message not delivered to task_queue'}, 504

    @app.route(ENDPOINT, methods=['GET'])
    def get_request_ids():
        lst = list()
        dir = Path(DATA_DIR)
        for item in dir.iterdir():
            if item.name[:-4] != 'backup':
                lst.append(int(item.name[:-4]))
        return {"request_ids": lst}

    @app.route(f'{ENDPOINT}/<string:request_id>', methods=['GET'])
    def get_processing_result(request_id):
        file = Path(f"{DATA_DIR}/{request_id}.txt")
        if file.exists():
            data = file.read_text().split()
            if len(data) == 1:
                return {"found": "True"}
            else:
                return {
                    "found": "True",
                    "lenght": data[1],
                    "path": ' '.join(data[2:])
                }
        return {}, 404
    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
