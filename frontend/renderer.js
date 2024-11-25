const net = require('net');

let currentUser = null;
let currentRecipient = null;
let contacts = [];

const authHost = '127.0.0.1';
const authPort = 7000;
const messagingHost = '127.0.0.1';
const messagingPort = 5001;

// Elementos del DOM
const loginContainer = document.getElementById('login-container');
const chatContainer = document.getElementById('chat-container');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const loginError = document.getElementById('login-error');
const currentUserSpan = document.getElementById('current-user');
const contactList = document.getElementById('contact-list');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

let messagingSocket = null;

// Eventos
loginBtn.addEventListener('click', login);
registerBtn.addEventListener('click', register);
sendBtn.addEventListener('click', enviarMensaje);

function login() {
	const username = usernameInput.value.trim();
	const password = passwordInput.value.trim();

	if (!username || !password) {
		loginError.innerText = 'Por favor, ingresa un nombre de usuario y contraseña.';
		return;
	}

	iniciarSesion(username, password, (err) => {
		if (err) {
			loginError.innerText = err;
		} else {
			currentUser = username;
			iniciarChat();
		}
	});
}

function seleccionarContacto(contact) {
	currentRecipient = contact;
	const items = document.querySelectorAll('#contact-list li');
	items.forEach(item => {
		if (item.innerText === contact) {
			item.classList.add('active');
		} else {
			item.classList.remove('active');
		}
	});
	messagesDiv.innerHTML = '';
	obtenerHistorialConversacion(contact);
}

function obtenerHistorialConversacion(contact) {
	if (messagingSocket && messagingSocket.writable) {
		messagingSocket.write(`GET_HISTORY|${contact}\n`);
	}
}

function register() {
	const username = usernameInput.value.trim();
	const password = passwordInput.value.trim();

	if (!username || !password) {
		loginError.innerText = 'Por favor, ingresa un nombre de usuario y contraseña.';
		return;
	}

	registrarUsuario(username, password, (err) => {
		if (err) {
			loginError.innerText = err;
		} else {
			currentUser = username;
			iniciarChat();
		}
	});
}

function iniciarSesion(username, password, callback) {
	const client = new net.Socket();
	client.connect(authPort, authHost, () => {
		const solicitud = {
			action: 'iniciar_sesion',
			username: username,
			password: password
		};
		client.write(JSON.stringify(solicitud));
	});

	client.on('data', (data) => {
		const respuesta = JSON.parse(data.toString());
		if (respuesta.status === 'success') {
			callback(null);
		} else {
			callback(respuesta.message);
		}
		client.destroy();
	});

	client.on('error', (err) => {
		callback('Error de conexión con el servicio de autenticación.');
	});
}

function registrarUsuario(username, password, callback) {
	const client = new net.Socket();
	client.connect(authPort, authHost, () => {
		const solicitud = {
			action: 'registrar_usuario',
			username: username,
			password: password
		};
		client.write(JSON.stringify(solicitud));
	});

	client.on('data', (data) => {
		const respuesta = JSON.parse(data.toString());
		if (respuesta.status === 'success') {
			callback(null);
		} else {
			callback(respuesta.message);
		}
		client.destroy();
	});

	client.on('error', (err) => {
		callback('Error de conexión con el servicio de autenticación.');
	});
}

function iniciarChat() {
	loginContainer.style.display = 'none';
	chatContainer.style.display = 'block';
	currentUserSpan.innerText = currentUser;

	obtenerContactos();

	iniciarConexionMensajeria();
}

function obtenerContactos() {
	const client = new net.Socket();
	client.connect(authPort, authHost, () => {
		const solicitud = {
			action: 'obtener_usuarios'
		};
		client.write(JSON.stringify(solicitud));
	});

	client.on('data', (data) => {
		const respuesta = JSON.parse(data.toString());
		if (respuesta.status === 'success') {
			contacts = respuesta.users.filter(user => user !== currentUser);
			actualizarListaContactos();
		}
		client.destroy();
	});

	client.on('error', (err) => {
		console.log('Error al obtener contactos:', err);
	});
}

function actualizarListaContactos() {
	contactList.innerHTML = '';
	contacts.forEach(contact => {
		const li = document.createElement('li');
		li.innerText = contact;
		li.addEventListener('click', () => {
			seleccionarContacto(contact);
		});
		contactList.appendChild(li);
	});
}

function seleccionarContacto(contact) {
	currentRecipient = contact;
	const items = document.querySelectorAll('#contact-list li');
	items.forEach(item => {
		if (item.innerText === contact) {
			item.classList.add('active');
		} else {
			item.classList.remove('active');
		}
	});
	messagesDiv.innerHTML = '';
}

function iniciarConexionMensajeria() {
	messagingSocket = new net.Socket();

	messagingSocket.connect(messagingPort, messagingHost, () => {
		console.log('Conectado al servicio de mensajería');
	});

	let authenticated = false;

	messagingSocket.on('data', (data) => {
		const mensajes = data.toString().trim().split('\n');
		mensajes.forEach(mensaje => {
			if (!authenticated) {
				if (mensaje.includes('Por favor, autentíquese')) {
					// Enviar credenciales
					messagingSocket.write(`AUTH|${currentUser}\n`);
				} else if (mensaje.includes('Error: Autenticación fallida')) {
					console.log('Autenticación fallida en el servicio de mensajería');
					messagingSocket.destroy();
				} else {
					authenticated = true;
					console.log('Autenticado en el servicio de mensajería');
					// Solicitar lista de usuarios
					messagingSocket.write('GET_USERS\n');
				}
			} else {
				if (mensaje.startsWith('Error:')) {
					console.log('Error:', mensaje);
				} else if (mensaje === 'Mensaje procesado') {
					// Mensaje enviado correctamente
				} else if (mensaje.startsWith('USER_LIST|')) {
					// Recibir lista de usuarios
					const users = mensaje.split('|').slice(1);
					contacts = users.filter(user => user !== currentUser);
					actualizarListaContactos();
				} else if (mensaje.startsWith('NEW_USER|')) {
					// Recibir notificación de nuevo usuario
					const newUser = mensaje.split('|')[1];
					if (newUser !== currentUser && !contacts.includes(newUser)) {
						contacts.push(newUser);
						actualizarListaContactos();
					}
				} else if (mensaje.startsWith('HISTORY|')) {
					// Recibir mensajes del historial
					const parts = mensaje.split('|');
					const sender = parts[1];
					const content = parts.slice(2).join('|'); // Por si el mensaje contiene '|'
					mostrarMensaje(`${sender}: ${content}`, true);
				} else {
					// Recibir mensaje nuevo
					mostrarMensaje(mensaje, false);
				}
			}
		});
	});

	messagingSocket.on('error', (err) => {
		console.log('Error en la conexión de mensajería:', err);
	});
}

function enviarMensaje() {
	const message = messageInput.value.trim();
	if (!message || !currentRecipient) {
		return;
	}

	messagingSocket.write(`SEND|${currentRecipient}|${message}\n`);
	mostrarMensaje(`Tú: ${message}`);
	messageInput.value = '';
}

function mostrarMensaje(mensaje) {
	const msgElement = document.createElement('p');
	msgElement.innerText = mensaje;
	messagesDiv.appendChild(msgElement);
	messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
