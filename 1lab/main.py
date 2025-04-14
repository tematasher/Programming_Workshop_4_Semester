import threading
import time
from server import Server
from client import Client


def run_server():
    Server().start()


def run_client():
    Client().run()


if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("[MAIN] Сервер запускается...")
    time.sleep(2)

    run_client()

    # ожидание завершения всех потоков
    server_thread.join(timeout=1)
