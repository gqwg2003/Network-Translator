import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional

class ThemeManager:
    """
    Manager for application theming and styling
    """
    # Predefined themes
    THEMES = {
        "light": {
            "bg": "#FFFFFF",
            "fg": "#000000",
            "accent": "#1976D2",
            "error": "#D32F2F",
            "success": "#388E3C",
            "warning": "#FFA000",
            "info": "#0288D1",
            "text_bg": "#F5F5F5",  # Светло-серый фон для текстовых полей
            "text_fg": "#000000",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        },
        "dark": {
            "bg": "#222222",
            "fg": "#EEEEEE",
            "accent": "#2196F3",
            "error": "#F44336",
            "success": "#4CAF50",
            "warning": "#FFC107",
            "info": "#03A9F4",
            "text_bg": "#333333",  # Тёмно-серый фон для текстовых полей 
            "text_fg": "#EEEEEE",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        },
        "dark_blue": {
            "bg": "#1A1B2E",
            "fg": "#EEEEEE",
            "accent": "#3F51B5",
            "error": "#F44336",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "info": "#29B6F6",
            "text_bg": "#2A2A3A",  # Тёмно-синий фон для текстовых полей
            "text_fg": "#E0E0E0",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        },
        "plum": {
            "bg": "#2D1B36",
            "fg": "#EEEEEE",
            "accent": "#9C27B0",
            "error": "#F44336",
            "success": "#4CAF50",
            "warning": "#FFB300",
            "info": "#26A69A",
            "text_bg": "#3D2A45",  # Тёмно-сливовый фон для текстовых полей
            "text_fg": "#E0E0E0",
            "font": ("Segoe UI", 10),
            "header_font": ("Segoe UI", 12, "bold"),
        }
    }

    def __init__(self, root: tk.Tk, theme_name: str = "dark_blue"):
        """
        Initialize the theme manager
        
        Args:
            root: Root Tk instance
            theme_name: Name of the initial theme
        """
        self.root = root
        self.current_theme_name = theme_name
        self.style = ttk.Style()
        
        self._apply_theme(theme_name)
    
    def is_dark_theme(self) -> bool:
        """
        Check if the current theme is dark
        
        Returns:
            True if the current theme is dark
        """
        return self.current_theme_name in ["dark", "dark_blue", "plum"]
        
    def _apply_theme(self, theme_name: str):
        """
        Apply the specified theme
        
        Args:
            theme_name: Name of the theme to apply
        """
        # Validate theme_name
        if theme_name not in self.THEMES:
            theme_name = "dark_blue"
        
        self.current_theme_name = theme_name
        theme = self.THEMES[theme_name]
        
        # Set ttk theme
        try:
            # Try using a more modern ttk theme
            if theme_name in ["dark", "dark_blue", "plum"]:
                self.style.theme_use("clam")
            else:
                self.style.theme_use("vista" if self._is_windows() else "clam")
        except tk.TclError:
            # Fallback to a default theme
            try:
                self.style.theme_use("clam")
            except tk.TclError:
                pass
        
        # Configure common widget colors and fonts
        self.style.configure(
            "TFrame", 
            background=theme["bg"]
        )
        
        self.style.configure(
            "TLabel", 
            background=theme["bg"],
            foreground=theme["fg"],
            font=theme["font"]
        )
        
        # Создаем общие компоненты для кнопок
        button_border = 1
        button_relief = "raised"
        primary_bg = theme["accent"]
        primary_fg = "#FFFFFF"
        
        if self.is_dark_theme():
            secondary_bg = "#444444"
            secondary_bg_active = "#555555"
            secondary_bg_disabled = "#333333"
        else:
            secondary_bg = "#E0E0E0"
            secondary_bg_active = "#D0D0D0"
            secondary_bg_disabled = "#CCCCCC"
        
        # Базовые стили для кнопок (глобальный стиль)
        self.style.configure(
            "TButton", 
            background=secondary_bg,
            foreground=theme["fg"],
            font=theme["font"],
            padding=(10, 5),
            relief=button_relief,
            borderwidth=button_border,
            focusthickness=0,  # Уменьшаем толщину фокуса
            lightcolor=secondary_bg,  # Для 3D-эффекта
            darkcolor=self._adjust_color(secondary_bg, 0.8)  # Для 3D-эффекта
        )
        
        self.style.map(
            "TButton",
            background=[('active', secondary_bg_active), ('pressed', self._adjust_color(secondary_bg_active, 0.9)),
                        ('disabled', secondary_bg_disabled)],
            foreground=[('active', theme["fg"]), ('disabled', "#A0A0A0")],
            relief=[('pressed', 'sunken')]
        )
        
        # Основная кнопка (Primary)
        self.style.configure(
            "Primary.TButton",
            background=primary_bg,
            foreground=primary_fg,
            font=(theme["font"][0], theme["font"][1], "bold"),
            padding=(15, 6),
            relief=button_relief,
            borderwidth=button_border,
            focusthickness=0,
            lightcolor=self._adjust_color(primary_bg, 1.1),  # Для 3D-эффекта
            darkcolor=self._adjust_color(primary_bg, 0.9)  # Для 3D-эффекта
        )
        
        self.style.map(
            "Primary.TButton",
            background=[('active', self._adjust_color(primary_bg, 1.2)), 
                        ('pressed', self._adjust_color(primary_bg, 0.9)),
                        ('disabled', self._adjust_color(primary_bg, 0.7))],
            foreground=[('active', primary_fg), ('disabled', "#DDDDDD")],
            relief=[('pressed', 'sunken')]
        )
        
        # Акцентированная кнопка
        self.style.configure(
            "Accent.TButton",
            background=theme["accent"],
            foreground=primary_fg,
            padding=(10, 5),
            relief=button_relief,
            borderwidth=button_border,
            focusthickness=0,
            lightcolor=self._adjust_color(theme["accent"], 1.1),
            darkcolor=self._adjust_color(theme["accent"], 0.9)
        )
        
        self.style.map(
            "Accent.TButton",
            background=[('active', self._adjust_color(theme["accent"], 1.2)),
                        ('pressed', self._adjust_color(theme["accent"], 0.9)),
                        ('disabled', "#888888")],
            foreground=[('active', primary_fg), ('disabled', "#DDDDDD")],
            relief=[('pressed', 'sunken')]
        )
        
        # Кнопка действия (Action)
        self.style.configure(
            "Action.TButton",
            background=secondary_bg,
            foreground=theme["fg"],
            font=theme["font"],
            padding=(10, 4),
            relief=button_relief,
            borderwidth=button_border,
            focusthickness=0,
            lightcolor=self._adjust_color(secondary_bg, 1.1),
            darkcolor=self._adjust_color(secondary_bg, 0.9)
        )
        
        self.style.map(
            "Action.TButton",
            background=[('active', secondary_bg_active),
                        ('pressed', self._adjust_color(secondary_bg_active, 0.9)),
                        ('disabled', secondary_bg_disabled)],
            foreground=[('active', theme["fg"]), ('disabled', "#888888")],
            relief=[('pressed', 'sunken')]
        )
        
        # Secondary кнопка
        self.style.configure(
            "Secondary.TButton",
            background=secondary_bg,
            foreground=theme["fg"],
            padding=(10, 5),
            relief=button_relief,
            borderwidth=button_border,
            focusthickness=0,
            lightcolor=self._adjust_color(secondary_bg, 1.1),
            darkcolor=self._adjust_color(secondary_bg, 0.9)
        )
        
        self.style.map(
            "Secondary.TButton",
            background=[('active', secondary_bg_active),
                        ('pressed', self._adjust_color(secondary_bg_active, 0.9)),
                        ('disabled', secondary_bg_disabled)],
            foreground=[('active', theme["fg"]), ('disabled', "#888888")],
            relief=[('pressed', 'sunken')]
        )
        
        # Стиль для вкладок
        self.style.configure(
            "TNotebook", 
            background=theme["bg"],
            tabmargins=[2, 5, 2, 0]
        )
        
        self.style.configure(
            "TNotebook.Tab", 
            background=theme["bg"],
            foreground=theme["fg"],
            font=theme["font"],
            padding=[10, 2]
        )
        
        self.style.map(
            "TNotebook.Tab",
            background=[('selected', theme["accent"])],
            foreground=[('selected', "#FFFFFF")]
        )
        
        # Configure entry widgets
        self.style.configure(
            "TEntry",
            fieldbackground=theme["text_bg"],
            foreground=theme["text_fg"],
            borderwidth=1
        )
        
        # Configure root window
        self.root.configure(bg=theme["bg"])
        
        # Notify change
        self.root.event_generate("<<ThemeChanged>>")
        
    def get_theme(self) -> Dict[str, Any]:
        """
        Get the current theme dictionary
        
        Returns:
            The current theme's color and font settings
        """
        return self.THEMES[self.current_theme_name]
    
    def get_theme_name(self) -> str:
        """Get the current theme name"""
        return self.current_theme_name
    
    def set_theme(self, theme_name: str):
        """
        Set the application theme
        
        Args:
            theme_name: Name of the theme to apply
        """
        self._apply_theme(theme_name)
    
    def toggle_theme(self):
        """
        Toggle between light and dark themes
        
        Returns:
            The name of the new theme
        """
        themes = list(self.THEMES.keys())
        current_index = themes.index(self.current_theme_name)
        new_index = (current_index + 1) % len(themes)
        new_theme = themes[new_index]
        self._apply_theme(new_theme)
        return new_theme
        
    def create_custom_theme(self, name: str, settings: Dict[str, Any]):
        """
        Create a custom theme
        
        Args:
            name: Name for the custom theme
            settings: Dictionary of theme settings
        """
        # Create a copy of the light theme as base
        base_theme = self.THEMES["light"].copy()
        
        # Update with custom settings
        base_theme.update(settings)
        
        # Add to available themes
        self.THEMES[name] = base_theme
    
    def _is_windows(self) -> bool:
        """Check if running on Windows"""
        return self.root.tk.call('tk', 'windowingsystem') == 'win32'
    
    def _is_macos(self) -> bool:
        """Check if running on macOS"""
        return self.root.tk.call('tk', 'windowingsystem') == 'aqua'
    
    def _adjust_color(self, color: str, factor: float) -> str:
        """
        Adjust a hex color by a factor (lighten or darken)
        
        Args:
            color: Hex color code
            factor: Multiply factor (>1 to lighten, <1 to darken)
            
        Returns:
            Adjusted hex color
        """
        if not color.startswith('#') or len(color) != 7:
            return color
            
        # Extract RGB components
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        # Adjust
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}" 