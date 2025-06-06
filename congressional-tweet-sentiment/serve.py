#!/usr/bin/env python3
"""
Simple HTTP server for the Congressional Tweet Sentiment Analysis app.
Run this to serve the app locally and avoid CORS issues.
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=Path(__file__).parent, **kwargs)
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

def main():
    # Change to the script's directory
    os.chdir(Path(__file__).parent)
    
    # Try to find an available port
    for port in range(8080, 8090):
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(f"✅ Serving Congressional Tweet Sentiment Analysis at:")
                print(f"   http://localhost:{port}")
                print(f"   http://127.0.0.1:{port}")
                print()
                print("📊 Features:")
                print("   • Interactive sentiment timeline by party")
                print("   • Filter by chamber, party, state, member, issue")
                print("   • Search tweets by content")
                print("   • Member rankings (most positive/negative)")
                print()
                print("🔧 Optimizations:")
                print("   • Smart file loading (only loads relevant data)")
                print("   • Optimized for 800k+ tweets")
                print("   • Files split for fast loading")
                print()
                print("Press Ctrl+C to stop the server")
                print("=" * 50)
                
                # Try to open browser automatically
                try:
                    webbrowser.open(f'http://localhost:{port}')
                except:
                    pass
                
                httpd.serve_forever()
                
        except OSError:
            continue  # Port in use, try next one
    
    print(f"❌ Could not find available port in range 8080-8089")
    sys.exit(1)

if __name__ == "__main__":
    main()