import socket
import threading
import json
from .database import get_all_users, init_db, save_user, get_user, save_message, get_messages, get_conversation_history

HOST = "127.0.0.1"
PORT = 8000

def handle_client(conn, addr):
    print(f"Conexión establecida desde {addr}")
    try:
        data = conn.recv(1024)
        if not data:
            return
        request = json.loads(data.decode("utf-8"))
        action = request.get("action")

        if action == "guardar_usuario":
            save_user(request["username"], request["password_hash"])
            response = {"status": "success", "message": "Usuario registrado exitosamente"}
        elif action == "obtener_usuario":
            user = get_user(request["username"])
            if user:
                response = {"status": "success", "user": user}
            else:
                response = {"status": "error", "message": "Usuario no encontrado"}
        elif action == "obtener_usuarios":
            users = get_all_users()
            response = {"status": "success", "users": users}
        elif action == "save_message":
            save_message(request["sender"], request["receiver"], request["message"])
            response = {"status": "success", "message": "Mensaje guardado"}
        elif action == "get_conversation_history":
                user1 = request.get("user1")
                user2 = request.get("user2")
                messages = get_conversation_history(user1, user2)
                response = {"status": "success", "messages": messages}
        elif action == "get_messages":
            messages = get_messages(request["receiver"])
            response = {"status": "success", "messages": messages}
        else:
            response = {"status": "error", "message": "Acción no válida"}
    except Exception as e:
        response = {"status": "error", "message": str(e)}
    finally:
        conn.sendall(json.dumps(response).encode("utf-8"))
        conn.close()

def start_server():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Servidor de almacenamiento escuchando en {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

if __name__ == "__main__":
    start_server()
