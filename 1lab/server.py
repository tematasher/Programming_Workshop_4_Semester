import socket
import struct
import select
import asyncio
import threading
import logging
import scapy
import os
import csv
import sys
import tempfile
import json
import hashlib


file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [stdout_handler]
# handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG, 
    format='[%(asctime)s] %(name)s - %(message)s',
    handlers=handlers
)

class Server:
    """
    Запуск сервера, приём клиентов, делегирование
    их обработки. Делегирует соединение в ClientHandler.
    """
    def __init__(self, database_path='./data', host='localhost', port='7777'):
        self.host = host
        self.port = port
        self.db_path = database_path
        self.server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)


    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        client, addr = self.server_socket.accept()


    def accept_connections(self):
        pass

    
    def shutdown(self):
        pass


class ClientHandler:
    def __init__(self, conn, addr, database_manager, auth_manager, logger):
        pass

        
    def handle(self):
        pass


class SQLParser:
     def parse(self, raw_query: str) -> dict:
        pass
     

class QueryExecutor:
    def __init__(self, database_path):
        pass


    def execute(self, query_dict: dict) -> list[dict]:
        pass


class CacheManager:
    def __init__(self, max_size):
        pass


    def get(self, query_hash):
        pass


    def set(self, query_hash, result):
        pass


class DatabaseStructureBuilder:
    def build(self) -> dict:
        pass


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
