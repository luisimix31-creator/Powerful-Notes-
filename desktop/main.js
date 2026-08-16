const { app, BrowserWindow, shell } = require("electron");
const path = require("path");

const APP_URL = "https://powerful-notes.onrender.com";

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 720,
    minHeight: 560,
    title: "Powerful Notes",
    backgroundColor: "#f6f5ff",
    icon: path.join(__dirname, "icons", "icon.png"),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.setMenuBarVisibility(false);
  win.loadURL(APP_URL);

  // Keep the app in this window; anything pointing at a different origin
  // (e.g. a payment provider's hosted checkout page) opens in the system
  // browser instead of inside the app shell.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(APP_URL)) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  win.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(APP_URL) && !url.startsWith("https://checkout.stripe.com")) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
