import socket
import struct
import select
import asyncio
import scapy
import os
import sys
import tempfile


# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# hostname = socket.gethostname()
# port = 12345
# server.bind((hostname, port))
# server.listen(5)

# print('Server running...')

# con, address = server.accept()

# print(f'Connection: {con}\nAddress: {address}\n')
# print(f'con.recv0: {con.recv(0)}')
# print(f'con.recv1: {con.recv(1)}')
# print(f'con.recv2: {con.recv(2)}')
# print(f'con.recv3: {con.recv(3)}')
# print(f'con.recv4: {con.recv(4)}')

# con.close()
# server.close()