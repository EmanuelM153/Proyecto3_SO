import unittest
import os
import threading
import time

from servicioAutenticacion.main import registrar_usuario, iniciar_sesion, verificar_usuario
from servicioAlmacenamiento.main import start_server as iniciar_almacenamiento
from servicioAlmacenamiento.database import DB_NAME, init_db

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)
init_db()

class TestServicioAutenticacion(unittest.TestCase):
    almacenamiento_thread = threading.Thread(target=iniciar_almacenamiento, daemon=True)
    almacenamiento_thread.start()

    time.sleep(1)

    def test_registrar_usuario(self):
        respuesta = registrar_usuario("testuser2", "password1234")
        self.assertEqual(respuesta["status"], "success")

    def test_usuario_existente(self):
        registrar_usuario("testuser", "password123")
        respuesta = registrar_usuario("testuser", "password123")
        self.assertEqual(respuesta["status"], "error")

    def test_iniciar_sesion_exitoso(self):
        registrar_usuario("testuser", "password123")
        respuesta = iniciar_sesion("testuser", "password123")
        self.assertEqual(respuesta["status"], "success")

    def test_iniciar_sesion_fallo(self):
        registrar_usuario("testuser", "password123")
        respuesta = iniciar_sesion("testuser", "wrongpassword")
        self.assertEqual(respuesta["status"], "error")

    def test_verificar_usuario(self):
        registrar_usuario("testuser", "password123")
        respuesta = verificar_usuario("testuser")
        self.assertEqual(respuesta["status"], "success")

if __name__ == "__main__":
    unittest.main()
