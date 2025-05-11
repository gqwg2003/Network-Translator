import tkinter as tk
from tkinter import ttk, Menu, font
from typing import Optional, Dict, Any
import os
from PIL import Image, ImageTk

from src.translator.translator import Translator
from src.ui.panels.translator_panel import TranslatorPanel
from src.ui.panels.server_panel import ServerPanel
from src.ui.panels.batch_translator_panel import BatchTranslatorPanel
from src.ui.panels.model_manager_panel import ModelManagerPanel
from src.ui.widgets.status_bar import StatusBar
from src.ui.utils.theme_manager import ThemeManager
from src.utils.settings import load_settings, save_settings, get_setting, set_setting
from src.utils.logger import get_logger

# Константы для UI
APP_TITLE = "Neural Network Translator"
APP_VERSION = "1.2.0"
MIN_WIDTH = 900
MIN_HEIGHT = 600
DEFAULT_WIDTH = 1100
DEFAULT_HEIGHT = 700

class MainWindow:
    """
    Main application window with modern UI
    """
    def __init__(self, root: tk.Tk):
        """
        Initialize the main window
        
        Args:
            root: The Tkinter root window
        """
        # Инициализация логгера
        self.logger = get_logger("nn_translator.ui.main_window")
        self.logger.info("Initializing main window")
        
        self.root = root
        self.root.title(APP_TITLE)
        
        # Загрузка настроек размера окна
        window_width = get_setting("window.width", DEFAULT_WIDTH)
        window_height = get_setting("window.height", DEFAULT_HEIGHT)
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        
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
        
        # Центрируем окно после завершения инициализации
        self._center_window()
        
        self.logger.info("Main window initialized")
    
    def _create_widgets(self):
        """Create all main window widgets"""
        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем верхнюю панель с логотипом и заголовком
        self.header_frame = ttk.Frame(self.main_frame, padding=(20, 12))
        self.header_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 10))
        
        # Логотип (загрузим из assets или создадим заглушку)
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "assets", "logo.png")
        
        # Alternative path in images folder
        alt_logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "assets", "images", "logo.png")
        
        logo_label = ttk.Label(self.header_frame, text="NN")
        if os.path.exists(logo_path):
            try:
                # Загрузка и масштабирование логотипа
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((48, 48), Image.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                
                logo_label.config(image=logo_photo)
                logo_label.image = logo_photo  # Сохраняем ссылку
            except Exception as e:
                self.logger.error(f"Error loading logo: {e}")
        elif os.path.exists(alt_logo_path):
            try:
                # Try the alternative path
                logo_img = Image.open(alt_logo_path)
                logo_img = logo_img.resize((48, 48), Image.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                
                logo_label.config(image=logo_photo)
                logo_label.image = logo_photo  # Сохраняем ссылку
            except Exception as e:
                self.logger.error(f"Error loading logo from alt path: {e}")
        
        logo_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Заголовок и версия
        title_frame = ttk.Frame(self.header_frame)
        title_frame.pack(side=tk.LEFT)
        
        app_title_label = ttk.Label(
            title_frame, 
            text=APP_TITLE,
            font=("Segoe UI", 18, "bold")
        )
        app_title_label.pack(anchor=tk.W)
        
        app_version_label = ttk.Label(
            title_frame,
            text=f"v{APP_VERSION}",
            foreground="#888888",
            font=("Segoe UI", 10)
        )
        app_version_label.pack(anchor=tk.W)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        
        # Создаем кастомный стиль для вкладок
        style = ttk.Style()
        style.configure("Large.TNotebook.Tab", 
                        padding=(20, 10), 
                        font=("Segoe UI", 11),
                        background="#f0f0f0")
        style.map("Large.TNotebook.Tab",
                background=[("selected", "#ffffff"), ("active", "#f5f5f5")])
        style.configure("Large.TNotebook", padding=(5, 5))
        self.notebook.configure(style="Large.TNotebook")
        
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
        self.model_manager_panel = ModelManagerPanel(
            self.notebook,
            translator=self.translator,
            on_status_change=self._update_status
        )
        
        # Add panels to notebook
        self.notebook.add(self.translator_panel, text="Text Translator")
        self.notebook.add(self.batch_translator_panel, text="Batch Translator")
        self.notebook.add(self.model_manager_panel, text="Models")
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
        # Main container already set up
        
        # Add notebook to main frame
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Add status bar at the bottom
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        # Initialize status bar
        model_info = self.translator.get_model_info()
        display_name = model_info.get("display_name", model_info.get("model_id", "Unknown"))
        model_loaded = model_info.get("model_loaded", False)
        quality = model_info.get("quality", 0)
        
        model_status = f"Model: {display_name} ({quality}%)"
        status_color = "green" if model_loaded else "red"
        
        self.status_bar.set_status("model", model_status, status_color)
        self.status_bar.set_status("status", "Ready")
    
    def _create_menu(self):
        """Create the application menu"""
        # Получим цвета для меню из текущей темы
        theme = self.theme_manager.get_theme()
        bg_color = theme.get('bg', '#1A1B2E')
        fg_color = theme.get('fg', '#EEEEEE')
        
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # Настройка стиля меню под текущую тему
        menubar.config(bg=bg_color, fg=fg_color, activebackground=theme.get('accent', '#3F51B5'), 
                       activeforeground='white', relief=tk.FLAT)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0, bg=bg_color, fg=fg_color, activebackground=theme.get('accent', '#3F51B5'),
                         activeforeground='white')
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Models menu
        models_menu = Menu(menubar, tearoff=0, bg=bg_color, fg=fg_color, activebackground=theme.get('accent', '#3F51B5'),
                          activeforeground='white')
        models_menu.add_command(label="Manage Models", command=self._show_models_tab)
        menubar.add_cascade(label="Models", menu=models_menu)
        
        # View menu
        view_menu = Menu(menubar, tearoff=0, bg=bg_color, fg=fg_color, activebackground=theme.get('accent', '#3F51B5'),
                        activeforeground='white')
        view_menu.add_command(label="Light Theme", command=lambda: self._set_theme("light"))
        view_menu.add_command(label="Dark Theme", command=lambda: self._set_theme("dark"))
        view_menu.add_command(label="Dark Blue Theme", command=lambda: self._set_theme("dark_blue"))
        view_menu.add_command(label="Plum Theme", command=lambda: self._set_theme("plum"))
        view_menu.add_separator()
        view_menu.add_command(label="Cycle Themes", command=self._cycle_theme)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0, bg=bg_color, fg=fg_color, activebackground=theme.get('accent', '#3F51B5'),
                        activeforeground='white')
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
    
    def _set_theme(self, theme_name):
        """Set theme and save it to settings"""
        self.logger.info(f"Setting theme to {theme_name}")
        self.theme_manager.set_theme(theme_name)
        set_setting("theme", theme_name)
        
        # Обновляем меню под новую тему
        self._create_menu()
    
    def _cycle_theme(self):
        """Cycle through themes and save the selected one"""
        theme_name = self.theme_manager.toggle_theme()
        self.logger.info(f"Cycling theme to {theme_name}")
        set_setting("theme", theme_name)
        
        # Обновляем меню под новую тему
        self._create_menu()
    
    def _show_models_tab(self):
        """Switch to the models tab"""
        # Find the index of the models tab
        for i in range(self.notebook.index("end")):
            if "Models" in self.notebook.tab(i, "text"):
                self.notebook.select(i)
                break
    
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
        about_window.geometry("400x350")
        about_window.transient(self.root)  # Set to be on top of the main window
        about_window.grab_set()  # Modal
        about_window.resizable(False, False)
        
        # Get theme colors
        theme = self.theme_manager.get_theme()
        
        # Configure window background
        about_window.configure(bg=theme["bg"])
        
        # Create content frame
        content_frame = ttk.Frame(about_window, padding=(20, 20))
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "assets", "logo.png")
                                
        # Alternative path in images folder
        alt_logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "assets", "images", "logo.png")
        
        logo_label = ttk.Label(content_frame, text="NN", font=("Segoe UI", 24, "bold"))
        if os.path.exists(logo_path):
            try:
                # Загрузка и масштабирование логотипа
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((80, 80), Image.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                
                logo_label.config(image=logo_photo)
                logo_label.image = logo_photo  # Сохраняем ссылку
            except Exception as e:
                self.logger.error(f"Error loading logo in about dialog: {e}")
        elif os.path.exists(alt_logo_path):
            try:
                # Try the alternative path
                logo_img = Image.open(alt_logo_path)
                logo_img = logo_img.resize((80, 80), Image.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                
                logo_label.config(image=logo_photo)
                logo_label.image = logo_photo  # Сохраняем ссылку
            except Exception as e:
                self.logger.error(f"Error loading logo from alt path in about dialog: {e}")
        
        logo_label.pack(pady=(0, 15))
        
        # Add app title
        ttk.Label(
            content_frame, 
            text="Neural Network Translator", 
            font=("Segoe UI", 16, "bold"),
        ).pack()
        
        # Add version
        ttk.Label(
            content_frame, 
            text=f"Version {APP_VERSION}", 
            foreground="#888888",
        ).pack(pady=(0, 15))
        
        # Description
        ttk.Label(
            content_frame, 
            text="Offline English to Russian translator\nusing neural network models",
            justify=tk.CENTER,
            wraplength=350,
        ).pack(pady=(0, 15))
        
        # Copyright
        ttk.Label(
            content_frame,
            text="© 2025 Neural Network Translation Team",
            foreground="#888888",
            font=("Segoe UI", 9),
        ).pack(pady=(10, 0))
        
        # Close button
        close_button = ttk.Button(
            content_frame, 
            text="Close", 
            command=about_window.destroy,
            style="Accent.TButton",
            width=15
        )
        close_button.pack(pady=(15, 0))
        
    def _update_status(self, message: str, status_type: str = "info"):
        """
        Update the status bar with a message
        
        Args:
            message: The message to display
            status_type: The type of status (info, success, error, warning)
        """
        # Set the status message
        self.status_bar.set_status("status", message)
        
        # Set the color based on status type
        if status_type == "success":
            self.status_bar.set_status_color("status", "green")
        elif status_type == "error":
            self.status_bar.set_status_color("status", "red")
        elif status_type == "warning":
            self.status_bar.set_status_color("status", "orange")
        else:
            self.status_bar.set_status_color("status", "")  # Default color
        
        # Log the status message
        if status_type == "error":
            self.logger.error(message)
        elif status_type == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def _on_close(self):
        """Handle window close event"""
        # Save settings
        self._save_panel_data()
        # Load settings and then save them
        settings = load_settings()
        save_settings(settings)
        
        # Close the window
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        # Configure global font settings
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        
        self.root.mainloop()
    
    def _center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y)) 