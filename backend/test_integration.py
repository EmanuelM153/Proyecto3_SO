import unittest
import threading
import time
import socket
import os
import json
from servicioMensajeria.main import MessagingService
from servicioAutenticacion.main import iniciar_servidor as iniciar_autenticacion
from servicioAlmacenamiento.main import start_server as iniciar_almacenamiento
from servicioAlmacenamiento.database import init_db, DB_NAME

class IntegrationTestMessagingService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Limpiar la base de datos antes de iniciar las pruebas
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
        init_db()

        # Iniciar el servicio de almacenamiento en un hilo
        cls.almacenamiento_thread = threading.Thread(target=iniciar_almacenamiento, daemon=True)
        cls.almacenamiento_thread.start()

        time.sleep(1)

        # Iniciar el servicio de autenticación en un hilo
        cls.autenticacion_thread = threading.Thread(target=iniciar_autenticacion, args=('127.0.0.1', 7000), daemon=True)
        cls.autenticacion_thread.start()

        time.sleep(1)

        # Iniciar el servicio de mensajería en un hilo
        cls.messaging_service = MessagingService(
            host='127.0.0.1', port=5001,
            auth_host='127.0.0.1', auth_port=7000,
            storage_host='127.0.0.1', storage_port=8000
        )
        cls.messaging_thread = threading.Thread(target=cls.messaging_service.start, daemon=True)
        cls.messaging_thread.start()

        time.sleep(1)

    def test_message_flow(self):
        # Registrar usuarios necesarios
        self.register_user('user1', 'password1')
        self.register_user('user2', 'password2')

        # Iniciar dos clientes simulando user1 y user2
        user1_socket = self.connect_and_authenticate('user1')
        user2_socket = self.connect_and_authenticate('user2')

        # user1 envía un mensaje a user2
        message = 'Hola, user2!'
        self.send_message(user1_socket, 'user2', message)

        # Verificar que user2 recibe el mensaje
        received_message = self.receive_message(user2_socket)
        expected_message = f"user1 dice: {message}"
        self.assertEqual(received_message.strip(), expected_message)

        # Cerrar las conexiones de los clientes
        user1_socket.close()
        user2_socket.close()

    def register_user(self, username, password):
        # Conectarse al servicio de autenticación para registrar un usuario
        try:
            with socket.create_connection(('127.0.0.1', 7000)) as sock:
                sock.sendall(json.dumps({
                    'action': 'registrar_usuario',
                    'username': username,
                    'password': password
                }).encode())
                response = json.loads(sock.recv(1024).decode())
                self.assertEqual(response['status'], 'success')
        except Exception as e:
            self.fail(f"Error al registrar el usuario {username}: {e}")

    def connect_and_authenticate(self, username):
        # Conectarse al servicio de mensajería y autenticarse
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 5001))

        # Recibir el mensaje de autenticación
        auth_prompt = sock.recv(1024).decode()
        self.assertIn('Por favor, autentíquese', auth_prompt)

        # Enviar credenciales
        sock.sendall(f"AUTH|{username}\n".encode())
        return sock

    def send_message(self, sock, recipient, content):
        # Enviar un mensaje en formato: SEND|<recipient>|<content>
        sock.sendall(f"SEND|{recipient}|{content}\n".encode())
        # Recibir confirmación
        response = sock.recv(1024).decode()
        self.assertIn('Mensaje procesado', response)

    def receive_message(self, sock):
        # Recibir un mensaje del socket
        data = sock.recv(1024).decode()
        return data

    @classmethod
    def tearDownClass(cls):
        # Detener los servicios si es necesario (los hilos daemon terminarán con el programa)
        pass

if __name__ == '__main__':
    unittest.main()
