import socket
import struct
import threading
import logging
import os
import csv
import sys
import json
import hashlib
import re
import operator
from collections import OrderedDict


class Server:
    """
    Основной сервер. Ожидает подключения клиентов,
    запускает обработку в ClientHandler.
    """

    def __init__(self, database_path='./data', host='localhost', port=7777):
        self.host = host
        self.port = port
        self.db_path = database_path

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # менеджеры
        self.logger = Logger()
        self.auth_manager = AuthenticationManager('./users.txt')
        self.cache_manager = CacheManager(max_size=50)
        self.query_executor = QueryExecutor(database_path=self.db_path)
        self.db_structure_builder = DatabaseStructureBuilder(database_path=self.db_path)

        self.running = True

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.logger.log("INFO", f"Сервер запущен на {self.host}:{self.port}")
            self.accept_connections()
        except Exception as e:
            self.logger.log("ERROR", f"Ошибка запуска сервера: {e}")
        finally:
            self.shutdown()

    def accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                self.logger.log("INFO", f"Подключение клиента: {addr}")

                # создаём отдельный поток под клиента
                handler = ClientHandler(
                    conn=conn,
                    addr=addr,
                    database_manager=self.db_structure_builder,
                    auth_manager=self.auth_manager,
                    logger=self.logger
                )
                thread = threading.Thread(target=handler.handle, daemon=True)
                thread.start()

            except Exception as e:
                self.logger.log("ERROR", f"Ошибка при обработке клиента: {e}")

    def shutdown(self):
        self.logger.log("INFO", "Завершение работы сервера...")
        self.server_socket.close()



class ClientHandler:
    """
    Обрабатывает одно соединение с клиентом:
    аутентификация, парсинг и выполнение запроса,
    отправка ответа.
    """

    def __init__(self, conn, addr, database_manager, auth_manager, logger):
        self.conn = conn
        self.addr = addr
        self.db_manager = database_manager
        self.auth_manager = auth_manager
        self.logger = logger

    def recv_message(self) -> str:
        """
        Принимает сообщение от клиента с префиксом длины (4 байта).
        """
        raw_length = self.conn.recv(4)
        if not raw_length:
            return None
        length = struct.unpack('!I', raw_length)[0]
        data = b''
        while len(data) < length:
            packet = self.conn.recv(length - len(data))
            if not packet:
                break
            data += packet
        return data.decode('utf-8')

    def send_message(self, message: str):
        """
        Отправляет сообщение клиенту с заголовком какой-то длины.
        """
        encoded = message.encode('utf-8')
        length = struct.pack('!I', len(encoded))
        self.conn.sendall(length + encoded)

    def handle(self):
        try:
            self.logger.log("INFO", f"Клиент подключен: {self.addr}")

            # аутентификация
            auth_data = self.recv_message()
            if not auth_data:
                self.logger.log("ERROR", f"Не удалось получить аутентификационные данные")
                self.conn.close()
                return

            credentials = json.loads(auth_data)
            username = credentials.get('username')
            password = credentials.get('password')

            if not self.auth_manager.authenticate(username, password):
                self.logger.log("WARNING", f"Аутентификация не удалась для {username}")
                self.send_message(json.dumps({"status": "error", "message": "Authentication failed"}))
                self.conn.close()
                return

            self.send_message(json.dumps({"status": "ok", "message": "Authenticated"}))

            # основной цикл обработки команд
            while True:
                msg = self.recv_message()
                if not msg:
                    break

                if msg.strip().upper() == "EXIT":
                    break

                if msg.strip().upper() == "GET_STRUCTURE":
                    structure = self.db_manager.build()
                    self.send_message(json.dumps({"status": "ok", "structure": structure}))
                    continue

                # SELECT обработка
                try:
                    parsed = SQLParser().parse(msg)
                    query_hash = hashlib.md5(msg.encode()).hexdigest()

                    cached = CacheManager.get(query_hash)
                    if cached is not None:
                        self.logger.log("INFO", f"Запрос из кэша для {self.addr}")
                        self.send_message(json.dumps({"status": "ok", "cached": True, "result": cached}))
                        continue

                    result = QueryExecutor.execute(parsed)
                    CacheManager.set(query_hash, result)

                    self.send_message(json.dumps({"status": "ok", "cached": False, "result": result}))

                except Exception as e:
                    self.logger.log("ERROR", f"Ошибка при выполнении запроса: {e}")
                    self.send_message(json.dumps({"status": "error", "message": str(e)}))

        finally:
            self.logger.log("INFO", f"Клиент отключен: {self.addr}")
            self.conn.close()



class SQLParser:
    """
    Парсит SQL-подобные запросы вида:
    SELECT col1, col2 FROM table WHERE col3 >= 10
    """

    SUPPORTED_OPERATORS = ['>=', '<=', '!=', '=', '<', '>']

    def parse(self, raw_query: str) -> dict:
        query = raw_query.strip().lower()
        pattern = r'^select\s+(?P<columns>[\*\w,\s]+)\s+from\s+(?P<table>\w+)(?:\s+where\s+(?P<condition>.+))?$'
        match = re.match(pattern, query)

        if not match: raise ValueError('Неверный формат запроса.')

        columns = [col.strip() for col in match.group('columns').split(',')]
        table = match.group('table')
        raw_condition = match.group('condition')

        condition = None
        if raw_condition:
            condition = self._parse_condition(raw_condition)
        
        return {
            'table': table,
            'columns': columns,
            'condition': condition
        }
    

    def _parse_condition(self, condition_str: str) -> dict:
        for op in self.SUPPORTED_OPERATORS:
            if op in condition_str:
                parts = condition_str.split(op)
                if len(parts) != 2:
                    raise ValueError('Неверное условие WHERE.')
                
                column = parts[0].strip()
                value = parts[1].strip().strip("'\'")

                if value.isdigit():
                    value = int(value)
                else:
                    try: value = float(value)
                    except ValueError: pass

                return {
                    'column': column,
                    'operator': op,
                    'value': value
                }
        raise ValueError('Неизвестный оператор в WHERE-условии.')
    

class QueryExecutor:
    """ВЫполняет SELECT-запросы по csv таблицам."""

    OPERATORS = {
        '=': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge
    }

    def __init__(self, database_path: str):
        self.db_path = database_path


    def execute(self, query_dict: dict) -> list[dict]:
        table_name = query_dict['table']
        columns = query_dict['columns']
        condition = query_dict['condition']

        table_dir = os.path.join(self.db_path, table_name)
        csv_file = os.path.join(table_dir, 'table.csv')

        if not os.path.isfile(csv_file):
            raise FileNotFoundError(f'Файл таблицы не найден: {csv_file}')

        result = []

        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # применяем условие where
                if condition:
                    col = condition['column']
                    op_str = condition['operator']
                    value = condition['value']

                    if col not in row:
                        continue

                    # преобразуем значения к флоату, если можно
                    row_val = row[col]

                    try: 
                        row_val = float(row_val)
                        value = float(value)

                    except ValueError: pass

                    op_func = self.OPERATORS.get(op_str)
                    if not op_func or not op_func(row_val, value): continue

                # выбираем только нужные колонки
                if columns == ['*']: filtered = row
                else: filtered = {col: row[col] for col in columns if col in row}

                result.append(filtered)

        return result

class CacheManager:
    """
    Кэширует результаты запросов по их хэшам.
    При переполнении удаляет самый старый элемент (FIFO).
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = OrderedDict()


    def get(self, query_hash: str):
        """
        Возвращает результат по хэшу запроса или None.
        """
        return self.cache.get(query_hash)


    def set(self, query_hash, result):
        """
        Сохраянет результат запроса в кэш.
        Удаляет старейший элемент при переполнении.
        """
        if query_hash in self.cache:
            # обновляем порядок
            self.cache.move_to_end(query_hash)
        self.cache[query_hash] = result

        if len(self.cache) > self.max_size:
            # удаляем первый (самый старый)
            self.cache.popitem(last=False) 


class DatabaseStructureBuilder:
    """
    Строит описание структуры базы данных:
    таблицы и их колонки.
    """
    
    def __init__(self, database_path: str):
        self.db_path = database_path


    def build(self) -> dict:
        structure = {}

        if not os.path.isdir(self.db_path):
            raise FileNotFoundError(f"Путь к базе данных не найден: {self.db_path}")

        for table_name in os.listdir(self.db_path):
            table_path = os.path.join(self.database_path, table_name)
            csv_file = os.path.join(table_path, 'table.csv')

            if not os.path.isfile(csv_file): continue # пропускаем, если файла нет

            try:
                with open(csv_file, mode='r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    if headers:
                        print(f"Найдена таблица: {entry}")
                        structure[table_name] = headers
            except Exception as e:
                # пропускаем некорректные таблицы, но логируем
                print(f"Ошибка при чтении {csv_file}: {e}")

        return structure

class AuthenticationManager:
    """
    Отвечает за базовую аутентификацию клиентов.
    Проверяет логин и пароль по локальному хранилищу (файл), хэширует пароли.
    Хранит пользователей в JSON-файле в виде {username: password_hash}.
    """

    def __init__(self, users_file: str, logger):
        
        self.users_file = users_file
        self.logger = logger
        self.users = {}

        if os.path.exists(self.users_file):

            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
                self.logger.info(f"[Auth] Загружены {len(self.users)} пользователей.")

            except Exception as e:
                self.logger.error(f"[Auth] Ошибка при чтении файла пользователей: {e}")
            
        else:
            self.logger.warning(f"[Auth] Файл пользователей не найден: {self.users_file}")


    def authenticate(self, username: str, password: str) -> bool:
        """
        Проверка логина и пароля (MD-5 хеш).
        """
        password_hash = hashlib.md5(password.encode()).hexdigest()
        stored_hash = self.users.get(username)

        if stored_hash is None:
            self.logger.warning(f'[Auth] попытка входа с неизвестным пользователем: {username}')
            return False
        
        if stored_hash == password_hash:
            self.logger.info(f'[Auth] успешная аутентификация пользователя: {username}')
            return True
        
        else:
            self.logger.warning(f'[Auth] Неверный пароль для пользователя: {username}')
            return False
        
    
    def add_user(self, username: str, password: str):
        """
        Добавить нового пользователя. Хэширует пароль и сохраняет в файл.
        """

        if username in self.users:
            self.logger.warning(f'[Auth] Пользователь уже существует.')
            return False

        password_hash = hashlib.md5(password.encode()).hexdigest()
        self.users[username] = password_hash

        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=4)
            self.logger.info(f'[Auth] Пользователь добавлен: {username}')
            return True
        
        except Exception as e:
            self.logger.error(f'[Auth] Ошибка при сохранении пользователя: {e}')
            return False
              

class Logger:
    """
    Обёртка над стандартным logging.
    Используется для централизованного логгирования на клиенте и сервере.
    """

    def __init__(
            self,
            name: str = 'AppLogger',
            log_to_file: bool = False,
            file_name: str = 'app.log'
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False      # для избежания дублежа сообщений

        formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

        # поток в stdout
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        if log_to_file:
            file_handler = logging.FileHandler(filename=file_name)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log(self, level: str, message: str):
        """
        Записывает сообщение с заданным уровнем.
        :param level: 'debug', 'info', 'warning', 'error', 'critical'
        :param message: текст сообщения
        """

        level = level.lower()
    
        if level == 'debug':
            self.logger.debug(message)
        elif level == 'info':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        elif level == 'critical':
            self.logger.critical(message)
        else:
            self.logger.info(message)  # по дефолту

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
