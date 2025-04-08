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


class Client:
    def __init__(self, database_path='./data', host='localhost', port='7777'):
        self.db_path = database_path
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def start(self):
        pass

    
    def connect(self):
        self.client_socket.connect((self.host, self.port))

    
    def shutdown(self):
        pass