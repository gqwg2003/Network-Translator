import tkinter as tk
from tkinter import ttk, Menu
from typing import Optional, Dict, Any

from src.translator.translator import Translator
from src.ui.panels.translator_panel import TranslatorPanel
from src.ui.panels.server_panel import ServerPanel
from src.ui.panels.batch_translator_panel import BatchTranslatorPanel
from src.ui.widgets.status_bar import StatusBar
from src.ui.utils.theme_manager import ThemeManager
from src.utils.settings import load_settings, save_settings, get_setting, set_setting

class MainWindow:
    """
    Main application window
    """
    def __init__(self, root: tk.Tk):
        """
        Initialize the main window
        
        Args:
            root: The Tkinter root window
        """
        self.root = root
        self.root.title("Neural Network Translator")
        
        # Загрузка настроек размера окна
        window_width = get_setting("window.width", 900)
        window_height = get_setting("window.height", 700)
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(800, 600)
        
        # Обработчик события закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Use the same translator instance for all panels
        self.translator = Translator()
        
        # Initialize theme manager with saved theme
        self.theme_manager = ThemeManager(root)
        saved_theme = get_setting("theme", "dark_blue")
        
        # Create widgets and set up layout
        self._create_widgets()
        self._setup_layout()
        self._create_menu()
        
        # Применяем сохраненную тему после создания всех виджетов
        self.theme_manager.set_theme(saved_theme)
    
    def _create_widgets(self):
        """Create all main window widgets"""
        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        
        # Create panels
        self.translator_panel = TranslatorPanel(
            self.notebook, 
            translator=self.translator,
            on_status_change=self._update_status
        )
        self.batch_translator_panel = BatchTranslatorPanel(
            self.notebook,
            translator=self.translator,
            on_status_change=self._update_status
        )
        self.server_panel = ServerPanel(
            self.notebook,
            on_status_change=self._update_status
        )
        
        # Add panels to notebook
        self.notebook.add(self.translator_panel, text="Text Translator")
        self.notebook.add(self.batch_translator_panel, text="Batch Translator")
        self.notebook.add(self.server_panel, text="API Server")
        
        # Create status bar
        self.status_bar = StatusBar(
            self.main_frame,
            sections=[
                {"name": "status", "width": 4},
                {"name": "model", "width": 1}
            ]
        )
        
        # Загрузка сохраненных данных в панели
        self._load_panel_data()
    
    def _setup_layout(self):
        """Set up the layout for all widgets"""
        # Add notebook to main frame
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add status bar at the bottom
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        # Initialize status bar
        model_info = self.translator.get_model_info()
        model_path = model_info.get("model_path", "Unknown")
        model_loaded = model_info.get("model_loaded", False)
        
        model_status = f"Model: {model_path.split('/')[-1]}"
        status_color = "green" if model_loaded else "red"
        
        self.status_bar.set_status("model", model_status, status_color)
        self.status_bar.set_status("status", "Ready")
    
    def _create_menu(self):
        """Create the application menu"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = Menu(menubar, tearoff=0)
        view_menu.add_command(label="Light Theme", command=lambda: self._set_theme("light"))
        view_menu.add_command(label="Dark Theme", command=lambda: self._set_theme("dark"))
        view_menu.add_command(label="Dark Blue Theme", command=lambda: self._set_theme("dark_blue"))
        view_menu.add_command(label="Plum Theme", command=lambda: self._set_theme("plum"))
        view_menu.add_separator()
        view_menu.add_command(label="Cycle Themes", command=self._cycle_theme)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
    
    def _set_theme(self, theme_name):
        """Set theme and save it to settings"""
        self.theme_manager.set_theme(theme_name)
        set_setting("theme", theme_name)
    
    def _cycle_theme(self):
        """Cycle through themes and save the selected one"""
        theme_name = self.theme_manager.toggle_theme()
        set_setting("theme", theme_name)
    
    def _load_panel_data(self):
        """Load saved data into panels"""
        # Загрузка данных панели переводчика
        last_text = get_setting("translator.last_text", "")
        last_translation = get_setting("translator.last_translation", "")
        if last_text:
            self.translator_panel.set_text(last_text)
        if last_translation:
            self.translator_panel.set_translation(last_translation)
            
        # Загрузка API ключа для панели сервера
        last_key = get_setting("api.last_key", "")
        if last_key and hasattr(self.server_panel, 'api_key_text'):
            self.server_panel.api_key_text.config(state=tk.NORMAL)
            self.server_panel.api_key_text.delete("1.0", tk.END)
            self.server_panel.api_key_text.insert("1.0", last_key)
            self.server_panel.api_key_text.config(state=tk.DISABLED)
            
        # Загрузка конфигурации сервера
        host = get_setting("server.host", "127.0.0.1")
        port = get_setting("server.port", 8000)
        if hasattr(self.server_panel, 'host_entry'):
            self.server_panel.host_entry.delete(0, tk.END)
            self.server_panel.host_entry.insert(0, host)
        if hasattr(self.server_panel, 'port_entry'):
            self.server_panel.port_entry.delete(0, tk.END)
            self.server_panel.port_entry.insert(0, str(port))
    
    def _save_panel_data(self):
        """Save panel data to settings"""
        # Сохранение данных панели переводчика
        if hasattr(self.translator_panel, 'get_text'):
            set_setting("translator.last_text", self.translator_panel.get_text())
        if hasattr(self.translator_panel, 'get_translation'):
            set_setting("translator.last_translation", self.translator_panel.get_translation())
            
        # Сохранение API ключа из панели сервера
        if hasattr(self.server_panel, 'api_key_text'):
            api_key = self.server_panel.api_key_text.get("1.0", tk.END).strip()
            if api_key:
                set_setting("api.last_key", api_key)
                
        # Сохранение конфигурации сервера
        if hasattr(self.server_panel, 'host_entry') and hasattr(self.server_panel, 'port_entry'):
            host = self.server_panel.host_entry.get().strip()
            port_str = self.server_panel.port_entry.get().strip()
            
            if host:
                set_setting("server.host", host)
            
            try:
                port = int(port_str)
                set_setting("server.port", port)
            except ValueError:
                pass
        
        # Сохранение размера окна
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width > 100 and height > 100:  # Проверка на валидность размеров
            set_setting("window.width", width)
            set_setting("window.height", height)
        
    def _show_about(self):
        """Show the about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About Neural Network Translator")
        about_window.geometry("400x300")
        about_window.transient(self.root)  # Set to be on top of the main window
        about_window.grab_set()  # Modal
        about_window.resizable(False, False)
        
        # Get theme colors
        theme = self.theme_manager.get_theme()
        
        # Configure window background
        about_window.configure(bg=theme["bg"])
        
        # Add content
        ttk.Label(
            about_window, 
            text="Neural Network Translator", 
            font=theme["header_font"],
            background=theme["bg"],
            foreground=theme["accent"]
        ).pack(pady=(20, 10))
        
        ttk.Label(
            about_window, 
            text="Offline translator using neural network models",
            background=theme["bg"],
            foreground=theme["fg"]
        ).pack(pady=5)
        
        ttk.Label(
            about_window, 
            text="Version 1.0",
            background=theme["bg"],
            foreground=theme["fg"]
        ).pack(pady=5)
        
        ttk.Label(
            about_window, 
            text="Model: Helsinki-NLP/opus-mt-en-ru",
            background=theme["bg"],
            foreground=theme["fg"]
        ).pack(pady=5)
        
        ttk.Button(
            about_window, 
            text="OK", 
            command=about_window.destroy
        ).pack(pady=20)
        
        # Center the window relative to the main window
        about_window.update_idletasks()
        width = about_window.winfo_width()
        height = about_window.winfo_height()
        
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        
        about_window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """
        Update the status bar with a message
        
        Args:
            message: The status message
            status_type: Message type (info, success, error)
        """
        # Map status type to color
        theme = self.theme_manager.get_theme()
        color_map = {
            "info": theme["info"],
            "success": theme["success"],
            "error": theme["error"],
            "warning": theme["warning"]
        }
        
        color = color_map.get(status_type, theme["fg"])
        self.status_bar.set_status("status", message, color)
        
        # Log to console as well
        print(f"[{status_type.upper()}] {message}")
    
    def _on_close(self):
        """Handle window close event"""
        # Сохраняем настройки перед выходом
        self._save_panel_data()
        
        # Завершаем работу приложения
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run the main window loop"""
        # Center the window on screen
        self._center_window()
        
        # Start the application main loop
        self.root.mainloop()
    
    def _center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}") 