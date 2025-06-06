import asyncio
import json
import websockets
import cmd
import sys


class WebSocketCLI(cmd.Cmd):
    prompt = "ws-client> "
    intro = "WebSocket Client. Type 'help' for commands."


    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket
        self.running = True
        self.task_id = None
    
    
    async def receive_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                print(f"\n[WS] {data}\n{self.prompt}", end="")
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed by server")
            self.running = False
    

    def do_auth(self, arg):
        """Authenticate: AUTH <token>"""
        asyncio.create_task(self.websocket.send(arg))
    

    def do_parse(self, arg):
        """Start parsing: PARSE <url> [max_depth=2] [format=graphml]"""
        args = arg.split()
        if not args:
            print("Error: URL is required")
            return
        
        url = args[0]
        max_depth = int(args[1]) if len(args) > 1 else 2
        format = args[2] if len(args) > 2 else "graphml"
        
        command = json.dumps({
            "command": "parse",
            "url": url,
            "max_depth": max_depth,
            "format": format
        })
        asyncio.create_task(self.websocket.send(command))
    

    def do_status(self, arg):
        """Check task status: STATUS <task_id>"""
        if not arg:
            if self.task_id:
                arg = self.task_id
            else:
                print("Error: Task ID is required")
                return
        
        command = json.dumps({
            "command": "status",
            "task_id": arg
        })
        asyncio.create_task(self.websocket.send(command))
        self.task_id = arg
    


    def do_exit(self, arg):
        """Exit the client: EXIT"""
        self.running = False
        return True
    

    def do_script(self, arg):
        """Run commands from file: SCRIPT <filename>"""
        try:
            with open(arg, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        print(f"> {line}")
                        self.onecmd(line)
        except FileNotFoundError:
            print(f"File not found: {arg}")


async def main():
    async with websockets.connect("ws://localhost:8001/api/v1/ws") as websocket:
        cli = WebSocketCLI(websocket)
        receiver_task = asyncio.create_task(cli.receive_messages())
        
        try:
            while cli.running:
                cli.cmdloop()
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            receiver_task.cancel()
            await receiver_task


if __name__ == "__main__":
    asyncio.run(main())