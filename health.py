import asyncio
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # HTTP loglarni o'chirish

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8000), HealthHandler)
    server.serve_forever()

def start_health_server():
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    logger.info("Health check server port 8000 da ishga tushdi.")
