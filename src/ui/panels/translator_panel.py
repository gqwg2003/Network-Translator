import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Callable

from src.translator.translator import Translator
from src.ui.widgets.scrollable_text import ScrollableText
from src.ui.widgets.labeled_frame import LabeledFrame
from src.utils.settings import set_setting

class TranslatorPanel(ttk.Frame):
    """
    Panel for text translation functionality
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
        
        self.translator = translator or Translator()
        self.on_status_change = on_status_change
        
        # Check if we can get the theme manager from the parent
        self.theme_manager = None
        try:
            if hasattr(master.master, 'theme_manager'):
                self.theme_manager = master.master.theme_manager
        except:
            pass
            
        # Determine if we should use dark mode
        self.use_dark_mode = True
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            # Bind to theme changes
            master.bind("<<ThemeChanged>>", self._on_theme_changed)
        
        self._create_widgets()
        self._setup_layout()
        
    def _create_widgets(self):
        """Create all panel widgets"""
        # Input section
        self.input_frame = LabeledFrame(self, title="Input Text (English)")
        input_content = self.input_frame.get_content_frame()
        
        # Get text colors from theme if available
        text_bg = '#2A2A3A'  # Default dark background
        text_fg = '#E0E0E0'  # Default light text
        if self.theme_manager:
            theme = self.theme_manager.get_theme()
            text_bg = theme.get('text_bg', text_bg)
            text_fg = theme.get('text_fg', text_fg)
        
        self.input_text = ScrollableText(
            input_content,
            placeholder="Enter text to translate...",
            height=10,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # Control section
        self.control_frame = ttk.Frame(self)
        
        self.translate_button = ttk.Button(
            self.control_frame, 
            text="Translate",
            command=self._translate
        )
        self.translate_button.pack(padx=5, pady=10)
        
        # Output section
        self.output_frame = LabeledFrame(self, title="Translation (Russian)")
        output_content = self.output_frame.get_content_frame()
        
        self.output_text = ScrollableText(
            output_content,
            placeholder="Translation will appear here...",
            readonly=True,
            height=10,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
    
    def _on_theme_changed(self, event=None):
        """Handle theme change events"""
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            theme = self.theme_manager.get_theme()
            text_bg = theme.get('text_bg', '#2A2A3A' if self.use_dark_mode else 'white')
            text_fg = theme.get('text_fg', '#E0E0E0' if self.use_dark_mode else 'black')
            
            # Update text widgets
            self.input_text.set_dark_mode(self.use_dark_mode)
            self.input_text.config(bg=text_bg, fg=text_fg)
            
            self.output_text.set_dark_mode(self.use_dark_mode)
            self.output_text.config(bg=text_bg, fg=text_fg)
    
    def _setup_layout(self):
        """Set up the layout for all widgets"""
        self.input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.control_frame.pack(fill=tk.X)
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
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
                translation = self.translator.translate(input_text)
                
                # Update the UI in the main thread
                self.after(0, lambda: self._update_translation(translation))
                if self.on_status_change:
                    self.after(0, lambda: self.on_status_change("Translation complete", "success"))
            except Exception as e:
                # Show error in the main thread
                self.after(0, lambda: messagebox.showerror("Translation Error", str(e)))
                if self.on_status_change:
                    self.after(0, lambda: self.on_status_change(f"Error: {str(e)}", "error"))
            finally:
                # Reset button in the main thread
                self.after(0, lambda: self._reset_translate_button())
        
        thread = threading.Thread(target=translate_task)
        thread.daemon = True
        thread.start()
    
    def _update_translation(self, translation: str):
        """Update the output text field with the translation"""
        self.output_text.set_text(translation)
        
        # Сохраняем перевод в настройках
        set_setting("translator.last_translation", translation)
    
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
        
        # Сохраняем текст в настройках
        set_setting("translator.last_text", text)
        
    def set_translation(self, text: str):
        """Set the output text"""
        self.output_text.set_text(text)
        
        # Сохраняем перевод в настройках
        set_setting("translator.last_translation", text) 