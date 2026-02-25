import socketio
import time

# Create a standard Socket.IO client
sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print(">>> CONNECTED to Server! SID:", sio.get_sid())
    # Send ping
    print(">>> Sending PING...")
    sio.emit('ping')
    
    # Send command
    print(">>> Sending 'ls' command...")
    sio.emit('command', {'command': 'ls'})

@sio.event
def connect_error(data):
    print("!!! Connection Error:", data)

@sio.event
def disconnect():
    print("<<< Disconnected from Server")

@sio.event
def pong(data):
    print(f"<<< PONG Received: {data}")

@sio.event
def response(data):
    print(f"<<< RESPONSE Received: {data}")

@sio.event
def server_message(data):
    print(f"<<< SERVER MESSAGE: {data}")

if __name__ == '__main__':
    try:
        print("Attempting to connect to http://localhost:5000 ...")
        sio.connect('http://localhost:5000', transports=['websocket', 'polling'])
        print("SocketIO wait loop started...")
        sio.wait()
    except Exception as e:
        print(f"EXCEPTION: {e}")
        try:
             sio.disconnect()
        except:
            pass
