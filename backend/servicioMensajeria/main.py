import socket
import threading
import json

class MessagingService:
    def __init__(self, host="127.0.0.1", port=5001,
                 auth_host="127.0.0.1", auth_port=7000,
                 storage_host="127.0.0.1", storage_port=8000):
        """
        Inicializa el servicio de mensajería con integración al Servicio de Autenticación y Almacenamiento.
        """
        self.host = host
        self.port = port
        self.auth_host = auth_host
        self.auth_port = auth_port
        self.storage_host = storage_host
        self.storage_port = storage_port
        self.connected_clients = {}
        self.user_list = []

    def start(self):
        """
        Inicia el servidor de mensajería.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Servicio de mensajería corriendo en {self.host}:{self.port}")

        threading.Thread(target=self.listen_for_notifications, daemon=True).start()

        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"Conexión establecida con {client_address}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def listen_for_notifications(self):
        """Escucha notificaciones del servicio de autenticación."""
        notification_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        notification_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        notification_socket.bind((self.host, self.port + 1))  # Puerto 5002
        notification_socket.listen(5)
        print(f"Servicio de mensajería escuchando notificaciones en {self.host}:{self.port + 1}")

        while True:
            conn, _ = notification_socket.accept()
            threading.Thread(target=self.handle_notification, args=(conn,)).start()

    def handle_notification(self, conn):
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                return
            notification = json.loads(data)
            action = notification.get('action')
            if action == 'nuevo_usuario':
                username = notification.get('username')
                if username:
                    print(f"Nuevo usuario registrado: {username}")
                    # Notificar a los clientes conectados
                    self.broadcast_new_user(username)
        except Exception as e:
            print(f"Error al manejar la notificación: {e}")
        finally:
            conn.close()

    def broadcast_new_user(self, username):
        """Envía la lista actualizada de usuarios a los clientes conectados."""
        for client_username, client_socket in self.connected_clients.items():
            try:
                client_socket.sendall(f"NEW_USER|{username}\n".encode())
            except Exception as e:
                print(f"Error al enviar nueva lista de usuarios a {client_username}: {e}")

    def handle_get_users(self, username):
        """Envía la lista de usuarios al cliente."""
        users = self.get_all_users()
        client_socket = self.connected_clients.get(username)
        if client_socket:
            client_socket.sendall(f"USER_LIST|{'|'.join(users)}\n".encode())

    def get_all_users(self):
        """Obtiene la lista de todos los usuarios registrados."""
        # Obtener usuarios del servicio de autenticación
        try:
            with socket.create_connection((self.auth_host, self.auth_port)) as auth_socket:
                auth_socket.sendall(json.dumps({
                    "action": "obtener_usuarios"
                }).encode())
                response = json.loads(auth_socket.recv(4096).decode())
                if response["status"] == "success":
                    return response["users"]
                else:
                    return []
        except Exception as e:
            print(f"Error al obtener la lista de usuarios: {e}")
            return []

    def handle_client(self, client_socket):
        """
        Maneja la comunicación con un cliente.
        """
        username = None
        try:
            username = self.authenticate_client(client_socket)
            if not username:
                client_socket.send("Error: Autenticación fallida\n".encode())
                client_socket.close()
                return

            self.connected_clients[username] = client_socket

            self.send_pending_messages(username)

            while True:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                command, *args = data.strip().split('|')

                if command == "SEND":
                    self.handle_send_message(username, args)
                elif command == "GET_USERS":
                    self.handle_get_users(username)
                elif command == "GET_HISTORY":
                    self.handle_get_history(username, args)
                else:
                    client_socket.send("Comando no reconocido\n".encode())
        except Exception as e:
            print(f"Error con el usuario {username}: {e}")
        finally:
            if username:
                del self.connected_clients[username]
            client_socket.close()

    def handle_get_history(self, username, args):
        """Maneja la solicitud de obtener el historial de conversación."""
        if len(args) != 1:
            client_socket = self.connected_clients.get(username)
            if client_socket:
                client_socket.send("Error: Formato incorrecto para GET_HISTORY\n".encode())
            return

        other_user = args[0]

        messages = self.get_conversation_history(username, other_user)
        client_socket = self.connected_clients.get(username)
        if client_socket:
            for msg in messages:
                formatted_message = f"HISTORY|{msg['sender']}|{msg['message']}\n"
                client_socket.send(formatted_message.encode())

    def get_conversation_history(self, user1, user2):
        """Solicita el historial de conversación al servicio de almacenamiento."""
        try:
            with socket.create_connection((self.storage_host, self.storage_port)) as storage_socket:
                storage_socket.sendall(json.dumps({
                    "action": "get_conversation_history",
                    "user1": user1,
                    "user2": user2
                }).encode())
                response = json.loads(storage_socket.recv(4096).decode())
                if response["status"] == "success":
                    return response["messages"]
                else:
                    return []
        except Exception as e:
            print(f"Error al obtener el historial de conversación: {e}")
            return []

    def authenticate_client(self, client_socket):
        """
        Autentica al cliente al momento de conectarse.
        """
        try:
            client_socket.send("Por favor, autentíquese. Formato: AUTH|<username>\n".encode())
            data = client_socket.recv(1024).decode()
            if not data:
                return None
            command, *args = data.strip().split('|')
            if command != "AUTH" or len(args) != 1:
                return None
            username = args[0]

            if self.validate_user(username):
                return username
            else:
                return None
        except Exception as e:
            print(f"Error al autenticar al cliente: {e}")
            return None

    def handle_send_message(self, sender, args):
        """
        Maneja el comando SEND para enviar un mensaje.
        Formato: SEND|<recipient>|<content>
        """
        if len(args) != 2:
            sender_socket = self.connected_clients.get(sender)
            if sender_socket:
                sender_socket.send("Error: Formato incorrecto para SEND\n".encode())
            return

        recipient, content = args

        if not self.validate_user(recipient):
            sender_socket = self.connected_clients.get(sender)
            if sender_socket:
                sender_socket.send("Error: Usuario destinatario no válido\n".encode())
            return

        if recipient in self.connected_clients:
            recipient_socket = self.connected_clients[recipient]
            try:
                message = f"{sender} dice: {content}\n"
                recipient_socket.send(message.encode())
                print(f"Mensaje enviado a {recipient}")
            except Exception as e:
                print(f"Error al enviar mensaje a {recipient}: {e}")
                self.store_message(sender, recipient, content)
        else:
            self.store_message(sender, recipient, content)

        sender_socket = self.connected_clients.get(sender)
        if sender_socket:
            sender_socket.send("Mensaje procesado\n".encode())

    def send_pending_messages(self, username):
        """
        Envía los mensajes pendientes al usuario al momento de conectarse.
        """
        messages = self.get_messages(username)
        if messages:
            client_socket = self.connected_clients.get(username)
            if client_socket:
                for message in messages:
                    response = f"{message['sender']} dice: {message['message']}\n"
                    client_socket.send(response.encode())
        else:
            pass

    def validate_user(self, username):
        """
        Valida al usuario con el Servicio de Autenticación.
        """
        try:
            with socket.create_connection((self.auth_host, self.auth_port)) as auth_socket:
                auth_socket.sendall(json.dumps({
                    "action": "verificar_usuario",
                    "username": username
                }).encode())
                response = json.loads(auth_socket.recv(1024).decode())
                return response["status"] == "success"
        except Exception as e:
            print(f"Error al validar el usuario: {e}")
            return False

    def store_message(self, sender, recipient, content):
        """
        Envía un mensaje al Servicio de Almacenamiento para guardarlo.
        """
        try:
            with socket.create_connection((self.storage_host, self.storage_port)) as storage_socket:
                storage_socket.sendall(json.dumps({
                    "action": "save_message",
                    "sender": sender,
                    "receiver": recipient,
                    "message": content
                }).encode())
                response = json.loads(storage_socket.recv(1024).decode())
                return response["status"] == "success"
        except Exception as e:
            print(f"Error al guardar el mensaje: {e}")
            return False

    def get_messages(self, recipient):
        """
        Solicita los mensajes pendientes al Servicio de Almacenamiento.
        """
        try:
            with socket.create_connection((self.storage_host, self.storage_port)) as storage_socket:
                storage_socket.sendall(json.dumps({
                    "action": "get_messages",
                    "receiver": recipient
                }).encode())
                response = json.loads(storage_socket.recv(4096).decode())
                if response["status"] == "success":
                    return response["messages"]
                else:
                    return []
        except Exception as e:
            print(f"Error al recuperar los mensajes: {e}")
            return []


if __name__ == "__main__":
    service = MessagingService(port=5001,
                               auth_host="127.0.0.1", auth_port=7000,
                               storage_host="127.0.0.1", storage_port=8000)
    service.start()
