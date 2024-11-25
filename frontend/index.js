const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
	// Crear la ventana del navegador
	const win = new BrowserWindow({
		width: 800,
		height: 600,
		webPreferences: {
			nodeIntegration: true, // Permite usar Node.js en el renderer process
			contextIsolation: false
		}
	});

	// Cargar el archivo index.html
	win.loadFile('index.html');
}

app.whenReady().then(() => {
	createWindow();

	app.on('activate', function() {
		// En macOS, vuelve a crear la ventana en la aplicación cuando el dock se hace clic y no hay otras ventanas abiertas.
		if (BrowserWindow.getAllWindows().length === 0) createWindow();
	});
});

app.on('window-all-closed', function() {
	// En macOS, es común que las aplicaciones y su barra de menú permanezcan activas hasta que el usuario salga explícitamente con Cmd + Q
	if (process.platform !== 'darwin') app.quit();
});
