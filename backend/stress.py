import threading
import time
import socket
import json
import random
import os

from servicioAlmacenamiento.database import init_db, DB_NAME

NUM_CLIENTS = 30          # Número de clientes simultáneos
MESSAGES_PER_CLIENT = 10  # Número de mensajes que enviará cada cliente
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001

# Usuarios de prueba
TEST_USERS = [f'user{i}' for i in range(NUM_CLIENTS + 1)]

def register_user(username, password):
    try:
        with socket.create_connection(('127.0.0.1', 7000)) as sock:
            sock.sendall(json.dumps({
                'action': 'registrar_usuario',
                'username': username,
                'password': password
            }).encode())
            response = json.loads(sock.recv(1024).decode())
            if response['status'] != 'success':
                print(f"Error al registrar el usuario {username}: {response['message']}")
    except Exception as e:
        print(f"Excepción al registrar el usuario {username}: {e}")

def client_thread(username):
    try:
        # Conectar al servicio de mensajería
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((SERVER_HOST, SERVER_PORT))

        # Autenticar
        sock.recv(1024)
        sock.sendall(f"AUTH|{username}\n".encode())

        # Escuchar mensajes entrantes en un hilo separado
        threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

        # Enviar mensajes
        for _ in range(MESSAGES_PER_CLIENT):
            # Elegir un destinatario al azar diferente al remitente
            recipient = random.choice([user for user in TEST_USERS if user != username])
            message = f"Hola {recipient}, soy {username}"
            sock.sendall(f"SEND|{recipient}|{message}\n".encode())
            time.sleep(random.uniform(0.1, 0.5))

        # Esperar un momento para recibir mensajes
        time.sleep(1)
        sock.close()
    except Exception as e:
        print(f"Error en el cliente {username}: {e}")

def receive_messages(sock):
    # Función para recibir mensajes
    while True:
        try:
            data = sock.recv(1024).decode()
            if data:
                pass
            else:
                break
        except:
            break

def main():
    start_time = time.time()

    print("Registrando usuarios...")
    for username in TEST_USERS:
        register_user(username, 'password')

    time.sleep(1)

    print("Iniciando clientes...")
    threads = []
    for username in TEST_USERS[:-1]:  # El último usuario se deja como destinatario extra
        t = threading.Thread(target=client_thread, args=(username,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end_time = time.time()
    total_time = end_time - start_time
    total_messages = NUM_CLIENTS * MESSAGES_PER_CLIENT

    print("\n--- Resultados de la Prueba de Estrés ---")
    print(f"Tiempo total: {total_time:.2f} segundos")
    print(f"Total de mensajes enviados: {total_messages}")
    print(f"Tiempo promedio por mensaje: {total_time / total_messages:.4f} segundos")
    print(f"Mensajes por segundo: {total_messages / total_time:.2f}")

if __name__ == '__main__':
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    init_db()

    main()
