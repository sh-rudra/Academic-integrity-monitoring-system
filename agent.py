import requests, time, pyperclip, psutil, threading, wmi
import pygetwindow as gw
from datetime import datetime
from pywinauto import Application
import win32process

# IMPORTANT: Before running or building the agent, replace this value with the
# IPv4 address of the computer running server.py.
MONITORING_SERVER_IP = "127.0.0.1"
SERVER_URL = f"http://{MONITORING_SERVER_IP}:5000/log"

class EventAgent:
    def __init__(self):
        self.last_win = ""
        self.last_clip = ""
        self.browsers = ["Chrome", "Edge", "Firefox", "Brave"]
        self.running = True

    def push(self, etype, edata):
        payload = {"event_type": etype, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "data": edata}
        try:
            requests.post(SERVER_URL, json=payload, timeout=2)
            print(f"[SUCCESS] Pushed {etype}")
        except Exception as e:
            print(f"[FAILED] Could not connect to Monitoring Device: {e}")

    def get_app_path(self):
        try:
            hwnd = gw.getActiveWindow()._hWnd
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).exe()
        except: return "Unknown Path"

    def get_browser_url(self, title):
        try:
            app = Application(backend="uia").connect(title_re=title, timeout=0.7)
            element = app.window(title_re=title).child_window(control_type="Edit", found_index=0)
            url = element.get_value()
            if url:
                if not url.startswith(('http', 'https')): url = 'https://' + url
                return url
        except: return None

    def monitor_window(self):
        while self.running:
            try:
                win = gw.getActiveWindow()
                if win and win.title and win.title != self.last_win:
                    title = win.title
                    data = {"to_app": title}
                    if any(b in title for b in self.browsers):
                        url = self.get_browser_url(title)
                        data["source"] = url if url else "URL Hidden/Private"
                    else:
                        data["source"] = self.get_app_path()
                    self.push("WINDOW_CHANGE", data)
                    self.last_win = title
            except: pass
            time.sleep(1.0)

    def monitor_clipboard(self):
        while self.running:
            try:
                clip = pyperclip.paste()
                if clip != self.last_clip and clip.strip() != "":
                    self.push("CLIPBOARD", {"content": clip})
                    self.last_clip = clip
            except: pass
            time.sleep(1.0)

    def monitor_usb(self):
        c = wmi.WMI()
        watcher = c.watch_for(notification_type="Operation", wmi_class="Win32_USBControllerDevice", delay_secs=1)
        while self.running:
            try:
                usb_event = watcher()
                action = "USB Plugged In" if usb_event.event_type == "creation" else "USB Removed"
                self.push("USB_EVENT", {"action": action, "device": "Hardware Change Detected"})
            except: pass

    def run(self):
        print(f"Agent Active. Monitoring Participant activity...")
        tasks = [self.monitor_window, self.monitor_clipboard, self.monitor_usb]
        for task in tasks:
            threading.Thread(target=task, daemon=True).start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            self.running = False

if __name__ == "__main__":
    EventAgent().run()

