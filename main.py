#!/usr/bin/env python
import tkinter as tk
import os
import sys
import argparse
from src.ui.main_window import MainWindow
from src.server.api_server import ApiServer

def main():
    """
    Main entry point for the Neural Network Translator application
    """
    parser = argparse.ArgumentParser(description="Neural Network Translator")
    parser.add_argument("--server-only", action="store_true", help="Run only the API server without GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run the API server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
    parser.add_argument("--theme", default="dark_blue", choices=["light", "dark", "dark_blue", "plum"], 
                        help="UI theme (light, dark, dark_blue, plum)")
    
    args = parser.parse_args()
    
    if args.server_only:
        # Run only the API server
        server = ApiServer(host=args.host, port=args.port)
        try:
            print(f"Starting API server on http://{args.host}:{args.port}")
            import uvicorn
            uvicorn.run(server.app, host=args.host, port=args.port)
        except KeyboardInterrupt:
            print("Server stopped")
    else:
        # Run the GUI application
        root = tk.Tk()
        app = MainWindow(root)
        
        # If a theme was specified, apply it
        if hasattr(app, 'theme_manager') and args.theme:
            app.theme_manager.set_theme(args.theme)
            
        app.run()

if __name__ == "__main__":
    main() 