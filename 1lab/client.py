import socket
import struct
import json
import sys


try:
    from tabulate import tabulate
    USE_TABULATE = True
except ImportError:
    USE_TABULATE = False


class Client:
    def __init__(self, host='localhost', port=7777):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def authenticate(self):
        print("\n🔐 Вход в систему.")
        while True:
            username = input("👤 Логин: ").strip()
            password = input("🔑 Пароль: ").strip()

            if not username or not password:
                print("⚠️ Поля не могут быть пустыми.")
                continue

            # Переподключение, если сокет закрыт
            if self.socket.fileno() == -1:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connect()

            try:
                auth_data = json.dumps({'username': username, 'password': password})
                self.send_message(auth_data)
                response = json.loads(self.recv_message())

                if response.get("status") == "ok":
                    print("✅ Успешный вход!")
                    return True
                else:
                    print("❌ Ошибка аутентификации:", response.get("message"))
                    retry = input("🔁 Повторить попытку? (y/n): ").lower().strip()
                    if retry != 'y':
                        return False

            except (ConnectionResetError, json.JSONDecodeError) as e:
                print("🔌 Ошибка связи с сервером:", e)
                return False
            

    def connect(self):
        try:
            self.socket.connect((self.host, self.port))
        except ConnectionRefusedError:
            print("❌ Не удалось подключиться к серверу. Убедитесь, что сервер запущен.")
            sys.exit(1)


    def send_message(self, message: str):
        encoded = message.encode('utf-8')
        length = struct.pack('!I', len(encoded))
        self.socket.sendall(length + encoded)


    def register_user(self):
        print("📝 Регистрация нового пользователя.")
        while True:
            try:
                username = input("👤 Новый логин: ").strip()
                password = input("🔑 Новый пароль: ").strip()
                if not username or not password:
                    print("⚠️ Поля не могут быть пустыми.")
                    continue
                if ' ' in username or ' ' in password:
                    print("⚠️ Логин и пароль не должны содержать пробелов.")
                    continue

                # ереподключение к серверу
                if self.socket.fileno() == -1:  # проверка, закрыт ли сокет
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.connect()

                cmd_data = json.dumps({'command': 'ADD_USER', 'username': username, 'password': password})
                self.send_message(cmd_data)
                response = json.loads(self.recv_message())

                if response.get("status") == "ok":
                    print("🎉 Успешная регистрация! Теперь войдите в систему.")
                    return True
                else:
                    print("❌ Ошибка:", response.get("message"))
                    retry = input("🔁 Повторить попытку? (y/n): ").strip().lower()
                    if retry != 'y':
                        return False

            except (ConnectionResetError, BrokenPipeError) as e:
                print("🔌 Соединение с сервером потеряно. Попытка переподключения...")
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connect()


    def print_help(self):
        print("\n📘 Доступные команды:")
        print("  ▶ SQL-запрос: например, SELECT * FROM people WHERE age >= 25")
        print("  ▶ GET_STRUCTURE — показать структуру базы данных")
        print("  ▶ EXIT — завершить работу\n")


    def recv_message(self) -> str:
        raw_length = self.socket.recv(4)
        if not raw_length:
            return None
        length = struct.unpack('!I', raw_length)[0]
        data = b''
        while len(data) < length:
            packet = self.socket.recv(length - len(data))
            if not packet:
                break
            data += packet
        return data.decode('utf-8')


    def run(self):
        try:
            print("📡 Подключение к серверу...")
            self.connect()

            print("\n🔓 Добро пожаловать! Выберите действие:")
            print("  [1] Вход")
            print("  [2] Регистрация")
            choice = input("👉 Ваш выбор (1/2): ").strip()

            if choice == '2':
                if not self.register_user():
                    print("❌ Регистрация не выполнена. Завершение работы.")
                    return
                # После регистрации автоматически выполняем вход
                print("\n🔁 Автоматический вход после регистрации...")
                if not self.authenticate():
                    self.socket.close()
                    return
            elif choice == '1':
                if not self.authenticate():
                    self.socket.close()
                    return
            else:
                print("❌ Неверный выбор. Завершение работы.")
                self.socket.close()
                return

            self.print_help()

            while True:
                cmd = input("sql> ").strip()

                if not cmd:
                    print("⚠️ Пустой ввод. Введите команду или 'EXIT'.")
                    continue

                if cmd.upper() == "EXIT":
                    self.send_message("EXIT")
                    print("👋 Отключение от сервера.")
                    break

                if cmd.upper() == "HELP":
                    self.print_help()
                    continue

                self.send_message(cmd)
                response = self.recv_message()

                if not response:
                    print("🔌 Соединение с сервером разорвано.")
                    break

                response_data = json.loads(response)

                if response_data.get('status') == 'error':
                    print("⚠️ Ошибка:", response_data.get('message'))

                elif cmd.upper() == "GET_STRUCTURE":
                    print("\n📊 Структура базы данных:")
                    for table, columns in response_data.get('structure', {}).items():
                        print(f"  📁 {table}: {', '.join(columns)}")

                else:
                    result = response_data.get('result', [])
                    if not result:
                        print("📭 Запрос выполнен. Результатов нет.")
                    else:
                        print("📥 Результаты запроса:")
                        headers = result[0].keys()
                        rows = [[row[col] for col in headers] for row in result]

                        if USE_TABULATE:
                            print(tabulate(rows, headers, tablefmt="grid"))
                        else:
                            print(", ".join(headers))
                            for row in rows:
                                print(", ".join(str(cell) for cell in row))

                        if response_data.get('cached'):
                            print("🧠 [Результат получен из кэша]")

        except Exception as e:
            print("❗ Ошибка:", e)
        finally:
            self.socket.close()
