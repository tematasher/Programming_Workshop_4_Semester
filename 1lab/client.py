import socket
import struct
import json

class Client:
    def __init__(self, host='localhost', port=7777):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, self.port))

    def send_message(self, message: str):
        encoded = message.encode('utf-8')
        length = struct.pack('!I', len(encoded))
        self.socket.sendall(length + encoded)

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

    def authenticate(self):
        username = input("Username: ")
        password = input("Password: ")
        auth_data = json.dumps({'username': username, 'password': password})
        self.send_message(auth_data)
        response = json.loads(self.recv_message())
        if response.get('status') != 'ok':
            print("❌ Authentication failed:", response.get('message'))
            return False
        print("✅ Authenticated successfully")
        return True

    def run(self):
        try:
            self.connect()
            if not self.authenticate():
                self.socket.close()
                return

            while True:
                cmd = input("sql> ").strip()
                if cmd.upper() == "EXIT":
                    self.send_message("EXIT")
                    print("👋 Disconnected.")
                    break

                self.send_message(cmd)
                response = self.recv_message()
                if not response:
                    print("🔌 Connection closed by server.")
                    break

                response_data = json.loads(response)

                if response_data.get('status') == 'error':
                    print("⚠️ Error:", response_data.get('message'))
                elif cmd.upper() == "GET_STRUCTURE":
                    print("📊 Database structure:")
                    for table, columns in response_data.get('structure', {}).items():
                        print(f"  - {table}: {', '.join(columns)}")
                else:
                    print("📥 Query result:")
                    result = response_data.get('result', [])
                    if not result:
                        print("  (empty result)")
                    else:
                        # Вывод CSV в терминал
                        headers = result[0].keys()
                        print(", ".join(headers))
                        for row in result:
                            print(", ".join(str(row[col]) for col in headers))
        except Exception as e:
            print("❗ Error:", e)
        finally:
            self.socket.close()
