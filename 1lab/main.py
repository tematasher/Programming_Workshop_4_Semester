import sys

from server import Server
from client import Client

def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python main.py --server     # Запустить сервер")
        print("  python main.py --client     # Запустить клиент")
        sys.exit(1)

    if sys.argv[1] == '--server':
        server = Server()
        server.start()
    elif sys.argv[1] == '--client':
        client = Client()
        client.run()
    else:
        print("Неизвестный аргумент:", sys.argv[1])
        print("Допустимые аргументы: --server, --client")

if __name__ == '__main__':
    main()
