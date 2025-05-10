import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from typing import Optional, Callable, List

from src.translator.translator import Translator
from src.ui.widgets.scrollable_text import ScrollableText
from src.ui.widgets.labeled_frame import LabeledFrame

class BatchTranslatorPanel(ttk.Frame):
    """
    Panel for batch text translation functionality
    """
    def __init__(
        self, 
        master, 
        translator: Optional[Translator] = None,
        on_status_change: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ):
        """
        Initialize batch translator panel
        
        Args:
            master: Parent widget
            translator: Translator instance to use
            on_status_change: Callback for status changes (message, type)
            **kwargs: Additional arguments for Frame
        """
        super().__init__(master, **kwargs)
        
        self.translator = translator or Translator()
        self.on_status_change = on_status_change
        self.texts_to_translate = []
        self.translated_texts = []
        
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
        # Get text colors from theme if available
        text_bg = '#2A2A3A'  # Default dark background
        text_fg = '#E0E0E0'  # Default light text
        bg_color = '#1A1B2E'  # Default panel background
        accent_color = '#3F51B5'  # Default accent color
        
        if self.theme_manager:
            theme = self.theme_manager.get_theme()
            text_bg = theme.get('text_bg', text_bg)
            text_fg = theme.get('text_fg', text_fg)
            bg_color = theme.get('bg', bg_color)
            accent_color = theme.get('accent', accent_color)
        
        # Input section
        self.input_frame = LabeledFrame(self, title="Batch Translation Input", show_toolbar=True)
        input_content = self.input_frame.get_content_frame()
        
        # Add buttons to the toolbar
        self.input_frame.add_toolbar_button("Add Text", self._add_text)
        self.input_frame.add_toolbar_button("Import from File", self._import_from_file)
        self.input_frame.add_toolbar_button("Clear All", self._clear_all)
        
        # Text list frame
        self.text_listbox_frame = ttk.Frame(input_content)
        self.text_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Listbox with scrollbar - using custom colors for dark mode
        self.text_listbox = tk.Listbox(
            self.text_listbox_frame, 
            selectmode=tk.SINGLE,
            height=10,
            bg=text_bg,
            fg=text_fg,
            selectbackground=accent_color if self.use_dark_mode else None,
            selectforeground='white' if self.use_dark_mode else None,
            highlightbackground=bg_color if self.use_dark_mode else None,
            highlightcolor=text_fg if self.use_dark_mode else None,
            borderwidth=1 if self.use_dark_mode else 2
        )
        self.text_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_listbox.bind('<<ListboxSelect>>', self._on_text_selected)
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(self.text_listbox_frame, command=self.text_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_listbox.config(yscrollcommand=scrollbar.set)
        
        # Text preview
        preview_frame = ttk.Frame(input_content)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(preview_frame, text="Preview:").pack(anchor=tk.W)
        
        self.preview_text = ScrollableText(
            preview_frame,
            placeholder="Select an item to preview...",
            height=5,
            readonly=True,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Control section
        self.control_frame = ttk.Frame(self)
        
        self.translate_button = ttk.Button(
            self.control_frame, 
            text="Translate All",
            command=self._translate_batch
        )
        self.translate_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        self.progress_bar = ttk.Progressbar(
            self.control_frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.X, expand=True)
        
        # Output section
        self.output_frame = LabeledFrame(self, title="Batch Translation Results", show_toolbar=True)
        output_content = self.output_frame.get_content_frame()
        
        # Add buttons to the toolbar
        self.output_frame.add_toolbar_button("Export to File", self._export_to_file)
        
        # Results listbox
        self.results_listbox_frame = ttk.Frame(output_content)
        self.results_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.results_listbox = tk.Listbox(
            self.results_listbox_frame, 
            selectmode=tk.SINGLE,
            height=10,
            bg=text_bg,
            fg=text_fg,
            selectbackground=accent_color if self.use_dark_mode else None,
            selectforeground='white' if self.use_dark_mode else None,
            highlightbackground=bg_color if self.use_dark_mode else None,
            highlightcolor=text_fg if self.use_dark_mode else None,
            borderwidth=1 if self.use_dark_mode else 2
        )
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.results_listbox.bind('<<ListboxSelect>>', self._on_result_selected)
        
        # Scrollbar for results listbox
        results_scrollbar = ttk.Scrollbar(
            self.results_listbox_frame, 
            command=self.results_listbox.yview
        )
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.config(yscrollcommand=results_scrollbar.set)
        
        # Results preview
        results_preview_frame = ttk.Frame(output_content)
        results_preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(results_preview_frame, text="Translation Preview:").pack(anchor=tk.W)
        
        self.results_preview_text = ScrollableText(
            results_preview_frame,
            placeholder="Select a result to preview...",
            height=5,
            readonly=True,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg
        )
        self.results_preview_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
    
    def _on_theme_changed(self, event=None):
        """Handle theme change events"""
        if self.theme_manager:
            self.use_dark_mode = self.theme_manager.is_dark_theme()
            theme = self.theme_manager.get_theme()
            text_bg = theme.get('text_bg', '#2A2A3A' if self.use_dark_mode else 'white')
            text_fg = theme.get('text_fg', '#E0E0E0' if self.use_dark_mode else 'black')
            bg_color = theme.get('bg', '#1A1B2E' if self.use_dark_mode else '#FFFFFF')
            accent_color = theme.get('accent', '#3F51B5')
            
            # Update text widgets
            self.preview_text.set_dark_mode(self.use_dark_mode)
            self.preview_text.config(bg=text_bg, fg=text_fg)
            
            self.results_preview_text.set_dark_mode(self.use_dark_mode)
            self.results_preview_text.config(bg=text_bg, fg=text_fg)
            
            # Update listboxes
            self.text_listbox.config(
                bg=text_bg,
                fg=text_fg, 
                selectbackground=accent_color if self.use_dark_mode else None,
                selectforeground='white' if self.use_dark_mode else None,
                highlightbackground=bg_color if self.use_dark_mode else None,
                highlightcolor=text_fg if self.use_dark_mode else None
            )
            
            self.results_listbox.config(
                bg=text_bg,
                fg=text_fg,
                selectbackground=accent_color if self.use_dark_mode else None,
                selectforeground='white' if self.use_dark_mode else None,
                highlightbackground=bg_color if self.use_dark_mode else None,
                highlightcolor=text_fg if self.use_dark_mode else None
            )
    
    def _setup_layout(self):
        """Set up the layout for all widgets"""
        self.input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.control_frame.pack(fill=tk.X, padx=5)
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _add_text(self):
        """Add text to the batch translation list"""
        # Get text colors from theme if available
        text_bg = '#2A2A3A' if self.use_dark_mode else 'white'
        text_fg = '#E0E0E0' if self.use_dark_mode else 'black'
        if self.theme_manager:
            theme = self.theme_manager.get_theme()
            text_bg = theme.get('text_bg', text_bg)
            text_fg = theme.get('text_fg', text_fg)
        
        # Create a dialog to enter new text
        dialog = tk.Toplevel(self)
        dialog.title("Add Text for Translation")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Configure dialog appearance for dark mode
        if self.use_dark_mode and self.theme_manager:
            theme = self.theme_manager.get_theme()
            dialog.configure(bg=theme.get('bg', '#1A1B2E'))
        
        ttk.Label(dialog, text="Enter text to translate:").pack(padx=10, pady=(10, 5), anchor=tk.W)
        
        text_entry = ScrollableText(
            dialog, 
            height=10,
            dark_mode=self.use_dark_mode,
            bg=text_bg,
            fg=text_fg
        )
        text_entry.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        def add_and_close():
            text = text_entry.get_text()
            if text:
                self._add_text_to_list(text)
                dialog.destroy()
        
        ttk.Button(button_frame, text="Add", command=add_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Focus on the text entry
        text_entry.focus_set()
    
    def _add_text_to_list(self, text: str):
        """Add text to the list and update the UI"""
        if not text:
            return
            
        self.texts_to_translate.append(text)
        
        # Add to listbox (showing first 30 chars)
        preview = text[:30] + "..." if len(text) > 30 else text
        self.text_listbox.insert(tk.END, preview)
        
        # Update status
        count = len(self.texts_to_translate)
        if self.on_status_change:
            self.on_status_change(f"Added text item #{count}", "info")
    
    def _import_from_file(self):
        """Import texts from a file"""
        file_path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Split by double newline or paragraph markers
            texts = [t.strip() for t in content.split('\n\n') if t.strip()]
            
            # Add each text
            for text in texts:
                self._add_text_to_list(text)
                
            # Update status
            if self.on_status_change:
                self.on_status_change(f"Imported {len(texts)} items from {os.path.basename(file_path)}", "success")
                
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import file: {str(e)}")
            if self.on_status_change:
                self.on_status_change(f"Import failed: {str(e)}", "error")
    
    def _clear_all(self):
        """Clear all texts from the list"""
        if not self.texts_to_translate:
            return
            
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all texts?"):
            self.texts_to_translate = []
            self.text_listbox.delete(0, tk.END)
            self.preview_text.set_text("")
            
            if self.on_status_change:
                self.on_status_change("All texts cleared", "info")
    
    def _on_text_selected(self, event):
        """Handle text selection in the listbox"""
        selection = self.text_listbox.curselection()
        if selection:
            index = selection[0]
            text = self.texts_to_translate[index]
            self.preview_text.set_text(text)
    
    def _on_result_selected(self, event):
        """Handle result selection in the results listbox"""
        selection = self.results_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.translated_texts):
                text = self.translated_texts[index]
                self.results_preview_text.set_text(text)
    
    def _translate_batch(self):
        """Translate all texts in the batch"""
        if not self.texts_to_translate:
            messagebox.showinfo("Info", "No texts to translate")
            return
        
        # Reset results
        self.translated_texts = []
        self.results_listbox.delete(0, tk.END)
        self.results_preview_text.set_text("")
        
        # Update UI
        self.translate_button.config(state=tk.DISABLED)
        self.translate_button.config(text="Translating...")
        self.progress_bar['maximum'] = len(self.texts_to_translate)
        self.progress_bar['value'] = 0
        
        # Update status
        if self.on_status_change:
            self.on_status_change(f"Translating {len(self.texts_to_translate)} texts...", "info")
        
        # Use a thread to prevent UI freezing
        def translate_task():
            try:
                # Translate each text and update progress
                for i, text in enumerate(self.texts_to_translate):
                    translation = self.translator.translate(text)
                    
                    # Update the results in the main thread
                    self.after(0, lambda t=translation, idx=i: self._add_translation_result(t, idx))
                    
                # Finalize in the main thread
                self.after(0, self._finalize_translation)
                
            except Exception as e:
                # Show error in the main thread
                self.after(0, lambda: messagebox.showerror("Translation Error", str(e)))
                if self.on_status_change:
                    self.after(0, lambda: self.on_status_change(f"Error: {str(e)}", "error"))
                self.after(0, self._reset_translate_button)
        
        thread = threading.Thread(target=translate_task)
        thread.daemon = True
        thread.start()
    
    def _add_translation_result(self, translation: str, index: int):
        """Add a translation result to the results list"""
        self.translated_texts.append(translation)
        
        # Add to results listbox
        preview = translation[:30] + "..." if len(translation) > 30 else translation
        self.results_listbox.insert(tk.END, preview)
        
        # Update progress
        self.progress_bar['value'] = index + 1
    
    def _finalize_translation(self):
        """Finalize the batch translation process"""
        # Reset button and progress
        self.translate_button.config(state=tk.NORMAL)
        self.translate_button.config(text="Translate All")
        
        # Update status
        count = len(self.translated_texts)
        if self.on_status_change:
            self.on_status_change(f"Translated {count} texts successfully", "success")
    
    def _reset_translate_button(self):
        """Reset the translate button to its default state"""
        self.translate_button.config(state=tk.NORMAL)
        self.translate_button.config(text="Translate All")
    
    def _export_to_file(self):
        """Export translation results to a file"""
        if not self.translated_texts:
            messagebox.showinfo("Info", "No translation results to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save translation results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                # Write original and translation pairs
                for i, (orig, trans) in enumerate(zip(self.texts_to_translate, self.translated_texts)):
                    file.write(f"--- Text {i+1} ---\n")
                    file.write(f"Original: {orig}\n")
                    file.write(f"Translation: {trans}\n\n")
            
            # Update status
            if self.on_status_change:
                self.on_status_change(f"Exported {len(self.translated_texts)} translations to {os.path.basename(file_path)}", "success")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export file: {str(e)}")
            if self.on_status_change:
                self.on_status_change(f"Export failed: {str(e)}", "error") 