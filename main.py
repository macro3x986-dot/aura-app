import os
import sys
import threading
import time

# --- চdir করি ফাইল যেখানে, সেখানে ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

# --- Flask app import ---
from app import app as flask_app

# --- Werkzeug server (Kivy-friendly) ---
from werkzeug.serving import make_server

_server = None

def start_flask():
    global _server
    _server = make_server('127.0.0.1', 5000, flask_app, threaded=True)
    _server.serve_forever()

def wait_for_flask(timeout=20):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen('http://127.0.0.1:5000/', timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False

# --- Kivy ---
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.clock import Clock

if platform == 'android':
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    Activity = autoclass('org.kivy.android.PythonActivity')
    Color = autoclass('android.graphics.Color')

    _webview = None

    @run_on_ui_thread
    def build_webview():
        global _webview
        activity = Activity.mActivity
        _webview = WebView(activity)
        settings = _webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setLoadWithOverviewMode(True)
        settings.setUseWideViewPort(True)
        settings.setSupportZoom(False)
        _webview.setBackgroundColor(Color.parseColor('#05010a'))
        _webview.setWebViewClient(WebViewClient())
        _webview.loadUrl('http://127.0.0.1:5000/')
        activity.setContentView(_webview)

    class AURA(App):
        def build(self):
            threading.Thread(target=start_flask, daemon=True).start()

            def on_ready(dt):
                if wait_for_flask(10):
                    build_webview()
                else:
                    Clock.schedule_once(on_ready, 2)

            Clock.schedule_once(on_ready, 1)
            return Widget()

else:
    class AURA(App):
        def build(self):
            threading.Thread(target=start_flask, daemon=True).start()
            if wait_for_flask(10):
                try:
                    import webbrowser
                    webbrowser.open('http://127.0.0.1:5000/')
                except Exception:
                    pass
            return Widget()

if __name__ == '__main__':
    AURA().run()