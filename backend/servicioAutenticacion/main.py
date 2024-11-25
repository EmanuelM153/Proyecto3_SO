import json
import socket
import threading
import hashlib

ALMACENAMIENTO_HOST = '127.0.0.1'
ALMACENAMIENTO_PORT = 8000
MENSAJERIA_PORT = 5001
MENSAJERIA_HOST = '127.0.0.1'

def enviar_solicitud_al_almacenamiento(solicitud):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.connect((ALMACENAMIENTO_HOST, ALMACENAMIENTO_PORT))
            cliente.sendall(json.dumps(solicitud).encode('utf-8'))
            respuesta = cliente.recv(1024).decode('utf-8')
            return json.loads(respuesta)
    except Exception as e:
        return {"status": "error", "message": str(e)}

def notificar_nuevo_usuario(username):
    """Notifica al servicio de mensajería sobre un nuevo usuario."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente:
            cliente.connect((MENSAJERIA_HOST, MENSAJERIA_PORT + 1))
            solicitud = {
                "action": "nuevo_usuario",
                "username": username
            }
            cliente.sendall(json.dumps(solicitud).encode('utf-8'))
    except Exception as e:
        print(f"Error al notificar al servicio de mensajería: {e}")

def registrar_usuario(username, password):
    """Registra un usuario nuevo en el sistema."""
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    respuesta = enviar_solicitud_al_almacenamiento({
        "action": "obtener_usuario",
        "username": username
    })

    if respuesta["status"] == "success":
        return {"status": "error", "message": "Usuario ya existe"}

    respuesta = enviar_solicitud_al_almacenamiento({
        "action": "guardar_usuario",
        "username": username,
        "password_hash": password_hash
    })
    return respuesta

def iniciar_sesion(username, password):
    """Inicia sesión de un usuario existente."""
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    respuesta = enviar_solicitud_al_almacenamiento({
        "action": "obtener_usuario",
        "username": username
    })

    if respuesta["status"] == "error":
        return {"status": "error", "message": "Usuario no encontrado"}

    usuario = respuesta["user"]
    if usuario["password_hash"] == password_hash:
        return {"status": "success", "message": "Inicio de sesión exitoso"}
    else:
        return {"status": "error", "message": "Contraseña incorrecta"}

def verificar_usuario(username):
    """Verifica si un usuario existe (llamada interna)."""
    respuesta = enviar_solicitud_al_almacenamiento({
        "action": "obtener_usuario",
        "username": username
    })
    return {"status": respuesta["status"]}

def obtener_usuarios():
    """Obtiene la lista de usuarios registrados."""
    respuesta = enviar_solicitud_al_almacenamiento({
        "action": "obtener_usuarios"
    })
    return respuesta

def manejar_cliente(conexion):
    try:
        datos = conexion.recv(1024).decode('utf-8')
        solicitud = json.loads(datos)
        accion = solicitud.get("action")

        if accion == "registrar_usuario":
            respuesta = registrar_usuario(solicitud["username"], solicitud["password"])
        elif accion == "iniciar_sesion":
            respuesta = iniciar_sesion(solicitud["username"], solicitud["password"])
        elif accion == "verificar_usuario":
            respuesta = verificar_usuario(solicitud["username"])
        elif accion == "obtener_usuarios":
            respuesta = obtener_usuarios()
        else:
            respuesta = {"status": "error", "message": "Acción no válida"}

        conexion.sendall(json.dumps(respuesta).encode('utf-8'))
    except Exception as e:
        conexion.sendall(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
    finally:
        conexion.close()

def iniciar_servidor(host='127.0.0.1', puerto=7000):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, puerto))
    servidor.listen(5)
    print(f"Servicio de autenticación iniciado en {host}:{puerto}")

    while True:
        conexion, _ = servidor.accept()
        threading.Thread(target=manejar_cliente, args=(conexion,)).start()

if __name__ == "__main__":
    iniciar_servidor()
