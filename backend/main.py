import sys
import multiprocessing
import time
import subprocess

def start_microservices():
    import os
    from servicioMensajeria.main import MessagingService
    from servicioAutenticacion.main import iniciar_servidor as iniciar_autenticacion
    from servicioAlmacenamiento.main import start_server as iniciar_almacenamiento
    from servicioAlmacenamiento.database import init_db, DB_NAME

    # Limpiar la base de datos antes de iniciar los servicios
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    init_db()
    print("Base de datos inicializada.")

    # Iniciar el servicio de almacenamiento
    almacenamiento_process = multiprocessing.Process(target=iniciar_almacenamiento, daemon=True)
    almacenamiento_process.start()
    print("Servicio de almacenamiento iniciado.")

    time.sleep(1)

    # Iniciar el servicio de autenticación
    autenticacion_process = multiprocessing.Process(target=iniciar_autenticacion, args=('127.0.0.1', 7000), daemon=True)
    autenticacion_process.start()
    print("Servicio de autenticación iniciado.")

    time.sleep(1)

    # Iniciar el servicio de mensajería
    messaging_service = MessagingService(
        host='127.0.0.1', port=5001,
        auth_host='127.0.0.1', auth_port=7000,
        storage_host='127.0.0.1', storage_port=8000
    )
    messaging_process = multiprocessing.Process(target=messaging_service.start, daemon=True)
    messaging_process.start()
    print("Servicio de mensajería iniciado.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Servicios detenidos.")

def run_tests():
    print("Ejecutando pruebas unitarias y de integración...")
    subprocess.run(['python', 'test_database.py'])
    time.sleep(1)
    subprocess.run(['python', 'test_autenticacion.py'])
    time.sleep(1)
    subprocess.run(['python', 'test_integration.py'])

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_tests()
    else:
        start_microservices()
