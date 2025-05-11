import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Callable
from PIL import Image, ImageTk
import os

from src.translator.translator import Translator
from src.ui.widgets.scrollable_text import ScrollableText
from src.ui.widgets.labeled_frame import LabeledFrame
from src.utils.settings import set_setting, get_setting
from src.utils.logger import get_logger

class TranslatorPanel(ttk.Frame):
    """
    Panel for text translation functionality with modern UI
    """
    def __init__(
        self, 
        master, 
        translator: Optional[Translator] = None,
        on_status_change: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ):
        """
        Initialize translator panel
        
        Args:
            master: Parent widget
            translator: Translator instance to use
            on_status_change: Callback for status changes (message, type)
            **kwargs: Additional arguments for Frame
        """
        super().__init__(master, **kwargs)
        
        # Инициализация логгера
        self.logger = get_logger("nn_translator.ui.translator_panel")
        
        self.translator = translator or Translator()
        self.on_status_change = on_status_change
        
        # Check if we can get the theme manager from the parent
        self.theme_manager = None
        try:
            if hasattr(master.master, 'theme_manager'):
                self.theme_manager = master.master.theme_manager
        except:
            self.logger.warning("Could not get theme manager from parent")
            
        # Determine if we should use dark mode
        self.use_dark_mode = True
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            # Bind to theme changes
            master.bind("<<ThemeChanged>>", self._on_theme_changed)
        
        # Formatting options from translator
        self.formatting_options = self.translator.get_formatting_options()
        
        # Загрузка сохраненных настроек
        self.auto_format = get_setting("translator.auto_format", True)
        
        self._create_widgets()
        self._setup_layout()
        
    def _create_widgets(self):
        """Create all panel widgets"""
        # Get theme colors
        if self.theme_manager:
            theme = self.theme_manager.get_theme()
            bg_color = theme.get('bg', '#1A1B2E')
            text_bg = theme.get('text_bg', '#2A2A3A')
            text_fg = theme.get('text_fg', '#E0E0E0')
            accent_color = theme.get('accent', '#3F51B5')
        else:
            bg_color = '#1A1B2E'
            text_bg = '#2A2A3A'
            text_fg = '#E0E0E0'
            accent_color = '#3F51B5'
        
        # Main content frame
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Split into main area and sidebar
        self.main_area = ttk.Frame(self.content_frame)
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.sidebar = ttk.Frame(self.content_frame, padding=(15, 10))
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 10), pady=10)
        
        # ===== MAIN AREA =====
        # Input section with header
        self.input_header = ttk.Frame(self.main_area)
        self.input_header.pack(fill=tk.X, padx=15, pady=(15, 0))
        
        ttk.Label(
            self.input_header, 
            text="English", 
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)
        
        # Clear button
        self.clear_btn = ttk.Button(
            self.input_header,
            text="Clear",
            command=self._clear_input,
            style="Action.TButton",
            width=8,
            takefocus=False
        )
        self.clear_btn.pack(side=tk.RIGHT)
        
        # Input text area
        self.input_text = ScrollableText(
            self.main_area,
            placeholder="Enter text to translate...",
            height=12,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg,
            font=("Segoe UI", 11)
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(8, 15))
        
        # Control section with translate button
        self.control_frame = ttk.Frame(self.main_area, padding=(0, 5))
        self.control_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # Translation direction indicator
        translation_indicator = ttk.Frame(self.control_frame)
        translation_indicator.pack(side=tk.LEFT)
        
        ttk.Label(
            translation_indicator, 
            text="EN", 
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            translation_indicator, 
            text=" → ", 
            font=("Segoe UI", 14)
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            translation_indicator, 
            text="RU", 
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        
        # Translate button
        self.translate_button = ttk.Button(
            self.control_frame, 
            text="Translate",
            command=self._translate,
            style="Primary.TButton",
            width=15,
            takefocus=False
        )
        self.translate_button.pack(side=tk.RIGHT)
        
        # Cache status indicator
        self.cache_frame = ttk.Frame(self.control_frame)
        self.cache_frame.pack(side=tk.RIGHT, padx=15)
        
        self.cache_var = tk.StringVar(value="Cache: On")
        self.cache_label = ttk.Label(
            self.cache_frame,
            textvariable=self.cache_var,
            foreground="green",
            font=("Segoe UI", 9)
        )
        self.cache_label.pack(side=tk.RIGHT)
        
        # Output section header
        self.output_header = ttk.Frame(self.main_area)
        self.output_header.pack(fill=tk.X, padx=15, pady=(10, 0))
        
        ttk.Label(
            self.output_header, 
            text="Russian", 
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)
        
        # Copy button
        self.copy_btn = ttk.Button(
            self.output_header,
            text="Copy",
            command=self._copy_to_clipboard,
            style="Action.TButton",
            width=8,
            takefocus=False
        )
        self.copy_btn.pack(side=tk.RIGHT)
        
        # Output text area
        self.output_text = ScrollableText(
            self.main_area,
            placeholder="Translation will appear here...",
            readonly=True,
            height=12,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg,
            font=("Segoe UI", 11)
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(8, 15))
        
        # ===== SIDEBAR =====
        # Settings title
        settings_header = ttk.Frame(self.sidebar)
        settings_header.pack(fill=tk.X, pady=(0, 12))
        
        ttk.Label(
            settings_header, 
            text="Settings", 
            font=("Segoe UI", 13, "bold")
        ).pack(side=tk.LEFT)
        
        # Text formatting options
        self.formatting_frame = LabeledFrame(
            self.sidebar, 
            title="Text Formatting",
            padding=10,
            collapsible=True,
            collapsed=get_setting("translator.formatting_collapsed", False)
        )
        self.formatting_frame.pack(fill=tk.X, pady=5)
        formatting_content = self.formatting_frame.get_content_frame()
        
        # Smart quotes option
        self.smart_quotes_var = tk.BooleanVar(value=self.formatting_options.get("smart_quotes", True))
        self.smart_quotes_check = ttk.Checkbutton(
            formatting_content,
            text="Smart Quotes («»)",
            variable=self.smart_quotes_var,
            command=self._update_formatting_options
        )
        self.smart_quotes_check.grid(row=0, column=0, sticky="w", padx=5, pady=3)
        
        # Russian punctuation option
        self.ru_punct_var = tk.BooleanVar(value=self.formatting_options.get("russian_punctuation", True))
        self.ru_punct_check = ttk.Checkbutton(
            formatting_content,
            text="Russian Punctuation",
            variable=self.ru_punct_var,
            command=self._update_formatting_options
        )
        self.ru_punct_check.grid(row=1, column=0, sticky="w", padx=5, pady=3)
        
        # Whitespace normalization option
        self.whitespace_var = tk.BooleanVar(value=self.formatting_options.get("normalize_whitespace", True))
        self.whitespace_check = ttk.Checkbutton(
            formatting_content,
            text="Normalize Whitespace",
            variable=self.whitespace_var,
            command=self._update_formatting_options
        )
        self.whitespace_check.grid(row=2, column=0, sticky="w", padx=5, pady=3)
        
        # Fix common issues option
        self.fix_issues_var = tk.BooleanVar(value=self.formatting_options.get("fix_common_issues", True))
        self.fix_issues_check = ttk.Checkbutton(
            formatting_content,
            text="Fix Common Issues",
            variable=self.fix_issues_var,
            command=self._update_formatting_options
        )
        self.fix_issues_check.grid(row=3, column=0, sticky="w", padx=5, pady=3)
        
        # Auto apply formatting
        self.auto_format_var = tk.BooleanVar(value=self.auto_format)
        self.auto_format_check = ttk.Checkbutton(
            formatting_content,
            text="Auto-apply formatting",
            variable=self.auto_format_var,
            command=self._toggle_auto_format
        )
        self.auto_format_check.grid(row=4, column=0, sticky="w", padx=5, pady=3)
        
        # Live formatting button
        formatting_buttons = ttk.Frame(formatting_content)
        formatting_buttons.grid(row=5, column=0, pady=(10, 0))
        
        self.live_format_button = ttk.Button(
            formatting_buttons, 
            text="Apply Formatting",
            command=self._apply_formatting,
            style="Accent.TButton",
            width=16,
            takefocus=False
        )
        self.live_format_button.pack(side=tk.LEFT)
        
        # Translation history frame
        self.history_frame = LabeledFrame(
            self.sidebar, 
            title="History",
            padding=10,
            collapsible=True,
            collapsed=get_setting("translator.history_collapsed", True)
        )
        self.history_frame.pack(fill=tk.X, pady=10)
        history_content = self.history_frame.get_content_frame()
        
        # Будем хранить историю переводов
        self.history_list = tk.Listbox(
            history_content,
            height=6,
            bg=text_bg,
            fg=text_fg,
            selectbackground=accent_color,
            activestyle="none",
            bd=1,
            relief="solid"
        )
        self.history_list.pack(fill=tk.BOTH, expand=True)
        self.history_list.bind('<<ListboxSelect>>', self._on_history_select)
        
        # Load history from settings
        self.translation_history = get_setting("translator.history", [])
        for item in self.translation_history:
            if item.get('source'):
                # Показываем только начало текста
                text_preview = item.get('source')[:30] + '...' if len(item.get('source')) > 30 else item.get('source')
                self.history_list.insert(tk.END, text_preview)
        
        # Cache controls frame
        self.cache_control_frame = LabeledFrame(
            self.sidebar, 
            title="Cache Controls",
            padding=10,
            collapsible=True,
            collapsed=get_setting("translator.cache_collapsed", True)
        )
        self.cache_control_frame.pack(fill=tk.X, pady=5)
        cache_content = self.cache_control_frame.get_content_frame()
        
        # Cache toggle
        self.cache_enabled_var = tk.BooleanVar(value=getattr(self.translator, "cache_enabled", True))
        self.cache_toggle = ttk.Checkbutton(
            cache_content,
            text="Enable translation cache",
            variable=self.cache_enabled_var,
            command=self._toggle_cache
        )
        self.cache_toggle.pack(fill=tk.X, pady=2)
        
        # Clear cache button
        self.clear_cache_btn = ttk.Button(
            cache_content,
            text="Clear Cache",
            command=self._clear_cache,
            style="Action.TButton",
            width=15,
            takefocus=False
        )
        self.clear_cache_btn.pack(pady=(5, 2))
        
        # Update cache status display
        self._update_cache_status()
        
        # Добавим горячие клавиши
        self.bind_all("<Control-Return>", lambda e: self._translate())
        self.bind_all("<Control-c>", lambda e: self._copy_to_clipboard())
    
    def _setup_layout(self):
        """Set up the layout for all widgets"""
        # Main panel already set up during widget creation
        pass
    
    def _update_formatting_options(self):
        """Update the formatting options based on checkbox values"""
        options = {
            "smart_quotes": self.smart_quotes_var.get(),
            "russian_punctuation": self.ru_punct_var.get(),
            "normalize_whitespace": self.whitespace_var.get(),
            "fix_common_issues": self.fix_issues_var.get()
        }
        
        # Update the translator's formatting options
        self.translator.set_formatting_options(options)
        self.formatting_options = options
        
        # Save formatting state
        set_setting("translator.formatting_collapsed", self.formatting_frame.is_collapsed())
        set_setting("translator.history_collapsed", self.history_frame.is_collapsed())
        set_setting("translator.cache_collapsed", self.cache_control_frame.is_collapsed())
    
    def _toggle_auto_format(self):
        """Toggle auto-formatting of translations"""
        self.auto_format = self.auto_format_var.get()
        set_setting("translator.auto_format", self.auto_format)
    
    def _apply_formatting(self):
        """Apply formatting to the current translation text"""
        # Get current translation
        current_text = self.output_text.get_text()
        if not current_text:
            return
            
        # Format the text and update
        formatted_text = self.translator.text_formatter.process_text(
            current_text, 
            self.formatting_options
        )
        self.output_text.set_text(formatted_text)
        
        # Save the formatted text
        set_setting("translator.last_translation", formatted_text)
    
    def _update_cache_status(self):
        """Update the cache status indicator"""
        cache_enabled = getattr(self.translator, "cache_enabled", False)
        cache_entries = len(getattr(self.translator, "translation_cache", {}))
        
        if cache_enabled:
            self.cache_var.set(f"Cache: On ({cache_entries} entries)")
            self.cache_label.config(foreground="green")
        else:
            self.cache_var.set("Cache: Off")
            self.cache_label.config(foreground="#888888")
            
        # Update checkbox state
        self.cache_enabled_var.set(cache_enabled)
    
    def _toggle_cache(self):
        """Toggle translation cache"""
        cache_enabled = self.cache_enabled_var.get()
        self.translator.set_cache_enabled(cache_enabled)
        self._update_cache_status()
    
    def _clear_cache(self):
        """Clear the translation cache"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the translation cache?"):
            self.translator.clear_cache()
            self._update_cache_status()
            if self.on_status_change:
                self.on_status_change("Cache cleared", "info")
    
    def _clear_input(self):
        """Clear the input text field"""
        self.input_text.set_text("")
    
    def _copy_to_clipboard(self):
        """Copy translation to clipboard"""
        text = self.output_text.get_text()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            if self.on_status_change:
                self.on_status_change("Copied to clipboard", "info")
    
    def _on_history_select(self, event):
        """Handle selection from history list"""
        try:
            index = self.history_list.curselection()[0]
            if index < len(self.translation_history):
                item = self.translation_history[index]
                # Set input text and translation
                self.input_text.set_text(item.get('source', ''))
                self.output_text.set_text(item.get('target', ''))
        except (IndexError, Exception) as e:
            self.logger.error(f"Error selecting from history: {e}")
    
    def _on_theme_changed(self, event=None):
        """Handle theme change events"""
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            theme = self.theme_manager.get_theme()
            text_bg = theme.get('text_bg', '#2A2A3A' if self.use_dark_mode else 'white')
            text_fg = theme.get('text_fg', '#E0E0E0' if self.use_dark_mode else 'black')
            accent_color = theme.get('accent', '#3F51B5')
            
            # Update text widgets
            self.input_text.set_dark_mode(self.use_dark_mode)
            self.input_text.config(bg=text_bg, fg=text_fg)
            
            self.output_text.set_dark_mode(self.use_dark_mode)
            self.output_text.config(bg=text_bg, fg=text_fg)
    
            # Update history list colors
            self.history_list.config(bg=text_bg, fg=text_fg, selectbackground=accent_color)
    
    def _translate(self):
        """Translate the text in the input field"""
        input_text = self.input_text.get_text()
        
        if not input_text:
            messagebox.showinfo("Info", "Please enter text to translate")
            return
        
        # Update status
        if self.on_status_change:
            self.on_status_change("Translating...", "info")
        
        # Show loading indicator
        self.translate_button.config(state=tk.DISABLED)
        self.translate_button.config(text="Translating...")
        
        # Use a thread to prevent UI freezing
        def translate_task():
            try:
                # Get formatting options
                apply_formatting = self.auto_format and any(self.formatting_options.values())
                
                # Translate with formatting options
                translation = self.translator.translate(
                    input_text, 
                    apply_formatting=apply_formatting
                )
                
                # Update the UI in the main thread
                self.after(0, lambda: self._update_translation(input_text, translation))
                if self.on_status_change:
                    self.after(0, lambda: self.on_status_change("Translation complete", "success"))
                
                # Update cache status
                self.after(0, self._update_cache_status)
                
            except Exception as e:
                # Show error in the main thread
                self.after(0, lambda: messagebox.showerror("Translation Error", str(e)))
                if self.on_status_change:
                    self.after(0, lambda: self.on_status_change(f"Error: {str(e)}", "error"))
                self.logger.error(f"Translation error: {e}")
            finally:
                # Reset button in the main thread
                self.after(0, lambda: self._reset_translate_button())
        
        thread = threading.Thread(target=translate_task)
        thread.daemon = True
        thread.start()
    
    def _update_translation(self, source_text: str, translation: str):
        """Update the output text field with the translation"""
        self.output_text.set_text(translation)
        
        # Save to history (avoid duplicates)
        new_entry = {'source': source_text, 'target': translation, 'timestamp': os.times().elapsed}
        
        # Check if we already have this source text in history
        source_exists = False
        for i, item in enumerate(self.translation_history):
            if item.get('source') == source_text:
                # Update existing entry and move to top
                self.translation_history.pop(i)
                self.translation_history.insert(0, new_entry)
                source_exists = True
                break
                
        if not source_exists:
            # Add new entry at the beginning
            self.translation_history.insert(0, new_entry)
            # Limit history size
            if len(self.translation_history) > 20:
                self.translation_history = self.translation_history[:20]
        
        # Update history display
        self.history_list.delete(0, tk.END)
        for item in self.translation_history:
            if item.get('source'):
                text_preview = item.get('source')[:30] + '...' if len(item.get('source')) > 30 else item.get('source')
                self.history_list.insert(tk.END, text_preview)
        
        # Save history and translation
        set_setting("translator.history", self.translation_history)
        set_setting("translator.last_translation", translation)
        set_setting("translator.last_text", source_text)
    
    def _reset_translate_button(self):
        """Reset the translate button to its default state"""
        self.translate_button.config(state=tk.NORMAL)
        self.translate_button.config(text="Translate")
        
    def get_text(self) -> str:
        """Get the current input text"""
        return self.input_text.get_text()
        
    def get_translation(self) -> str:
        """Get the current translation text"""
        return self.output_text.get_text()
        
    def set_text(self, text: str):
        """Set the input text"""
        self.input_text.set_text(text)
        
    def set_translation(self, text: str):
        """Set the output text"""
        self.output_text.set_text(text)