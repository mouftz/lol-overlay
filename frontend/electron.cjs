const { app, BrowserWindow, globalShortcut, screen } = require('electron');

let win;

function createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    
    win = new BrowserWindow({
        width: width,
        height: height,
        x: 0,
        y: 0,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        resizable: true,
        hasShadow: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    win.loadURL('http://localhost:5174');
    win.webContents.openDevTools({ mode: 'detach' });

    // Make the window click-through everywhere
    win.setIgnoreMouseEvents(true, { forward: true });
}

app.whenReady().then(() => {
    createWindow();

    // Cmd+Shift+H -> toggle visibility
    globalShortcut.register('CommandOrControl+Shift+H', () => {
        if (win.isVisible()) win.hide();
        else win.show();
    });

    // Cmd+Shift+Q -> quit the overlay
    globalShortcut.register('CommandOrControl+Shift+Q', () => {
        app.quit();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});