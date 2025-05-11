#!/usr/bin/env python
import tkinter as tk
import os
import sys
import argparse
import logging
from src.ui.main_window import MainWindow
from src.server.api_server import ApiServer
from src.utils.logger import get_logger, set_log_level

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
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Show only warnings and errors")
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = get_logger("nn_translator")
    
    # Set log level based on arguments
    if args.debug:
        set_log_level(logging.DEBUG)
        logger.debug("Debug logging enabled")
    elif args.quiet:
        set_log_level(logging.WARNING)
        logger.warning("Quiet mode enabled (only warnings and errors will be shown)")
    
    logger.info("Neural Network Translator starting up")
    
    if args.server_only:
        # Run only the API server
        logger.info(f"Starting API server on http://{args.host}:{args.port}")
        server = ApiServer(host=args.host, port=args.port)
        try:
            import uvicorn
            uvicorn.run(server.app, host=args.host, port=args.port)
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
    else:
        # Run the GUI application
        logger.info("Starting GUI application")
        root = tk.Tk()
        app = MainWindow(root)
        
        # If a theme was specified, apply it
        if hasattr(app, 'theme_manager') and args.theme:
            logger.debug(f"Setting theme to {args.theme}")
            app.theme_manager.set_theme(args.theme)
            
        app.run()

if __name__ == "__main__":
    main() 