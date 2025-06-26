#!/usr/bin/env python3
"""
Simple HTTP server for serving the VIParser frontend
Run this to serve the frontend on http://localhost:3000
"""

import http.server
import socketserver
import os
import sys

# Change to the frontend directory
frontend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(frontend_dir)

PORT = 3000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"✅ VIParser Frontend Server")
            print(f"🌐 Serving at: http://localhost:{PORT}")
            print(f"📁 Directory: {frontend_dir}")
            print(f"🔗 Backend API: http://localhost:8000")
            print(f"\n🚀 Open http://localhost:{PORT} in your browser")
            print(f"⏹️  Press Ctrl+C to stop the server\n")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use")
            print(f"💡 Try stopping other servers or use a different port")
        else:
            print(f"❌ Server error: {e}")
        sys.exit(1)