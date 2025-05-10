import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import requests
from typing import Optional, Callable

from src.server.api_server import ApiServer
from src.utils.api_utils import generate_api_key, save_api_key
from src.ui.widgets.labeled_frame import LabeledFrame
from src.utils.settings import get_setting, set_setting

class ServerPanel(ttk.Frame):
    """
    Panel for server control and API key management
    """
    def __init__(
        self, 
        master,
        on_status_change: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ):
        """
        Initialize server panel
        
        Args:
            master: Parent widget
            on_status_change: Callback for status changes (message, type)
            **kwargs: Additional arguments for Frame
        """
        super().__init__(master, **kwargs)
        
        self.api_server = None
        self.on_status_change = on_status_change
        
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self):
        """Create all panel widgets"""
        # Server status section
        self.server_frame = LabeledFrame(self, title="Server Status", show_toolbar=True)
        server_content = self.server_frame.get_content_frame()
        
        self.server_status_label = ttk.Label(
            server_content, 
            text="Server: Not running",
            padding=10
        )
        self.server_status_label.pack(fill=tk.X, pady=5)
        
        # Available endpoints info
        endpoints_frame = ttk.Frame(server_content)
        endpoints_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(endpoints_frame, text="Available Endpoints:").pack(anchor=tk.W)
        endpoints_text = """
• /api/translate - Translate text
• /api/translate_batch - Batch translation
• /v1/chat/completions - OpenAI API compatible endpoint
"""
        ttk.Label(endpoints_frame, text=endpoints_text).pack(anchor=tk.W, padx=10)
        
        # API Examples and Test buttons
        buttons_frame = ttk.Frame(server_content)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        examples_button = ttk.Button(
            buttons_frame,
            text="Примеры использования API",
            command=self._show_api_examples
        )
        examples_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        test_button = ttk.Button(
            buttons_frame,
            text="Тест API",
            command=self._test_api
        )
        test_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Server control buttons
        button_frame = ttk.Frame(server_content)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_server_button = ttk.Button(
            button_frame, 
            text="Start Server", 
            command=self._start_server
        )
        self.start_server_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_server_button = ttk.Button(
            button_frame, 
            text="Stop Server", 
            command=self._stop_server, 
            state=tk.DISABLED
        )
        self.stop_server_button.pack(side=tk.LEFT)
        
        # Server configuration section
        self.config_frame = LabeledFrame(self, title="Server Configuration")
        config_content = self.config_frame.get_content_frame()
        
        # Host configuration
        host_frame = ttk.Frame(config_content)
        host_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(host_frame, text="Host:").pack(side=tk.LEFT, padx=(0, 5))
        self.host_entry = ttk.Entry(host_frame)
        self.host_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.host_entry.insert(0, "127.0.0.1")
        
        # Port configuration
        port_frame = ttk.Frame(config_content)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.port_entry = ttk.Entry(port_frame)
        self.port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.port_entry.insert(0, "8000")
        
        # Apply button
        self.apply_config_button = ttk.Button(
            config_content, 
            text="Apply Configuration",
            command=self._apply_configuration
        )
        self.apply_config_button.pack(pady=10)
        
        # API key section
        self.api_key_frame = LabeledFrame(self, title="API Key Management")
        api_key_content = self.api_key_frame.get_content_frame()
        
        self.api_key_text = tk.Text(api_key_content, height=3, width=40)
        self.api_key_text.pack(fill=tk.X, padx=5, pady=5)
        self.api_key_text.config(state=tk.DISABLED)
        
        # API key buttons
        api_key_button_frame = ttk.Frame(api_key_content)
        api_key_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.generate_key_button = ttk.Button(
            api_key_button_frame, 
            text="Generate API Key", 
            command=self._generate_api_key
        )
        self.generate_key_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.copy_key_button = ttk.Button(
            api_key_button_frame, 
            text="Copy to Clipboard", 
            command=self._copy_api_key
        )
        self.copy_key_button.pack(side=tk.LEFT)
        
        # API compatibility help
        help_frame = ttk.Frame(api_key_content)
        help_frame.pack(fill=tk.X, padx=5, pady=5)
        
        help_text = """
API Usage:
• Ключ работает со всеми API эндпоинтами (стандартным и OpenAI-совместимым)
• Стандартный API: header 'api-key: YOUR_KEY_HERE'
• OpenAI API: header 'Authorization: Bearer YOUR_KEY_HERE'
• URL: http://localhost:8000/api/translate или /v1/chat/completions
• Формат сообщений совместим с OpenAI API
"""
        ttk.Label(help_frame, text="Универсальный API-ключ", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(help_frame, text=help_text).pack(anchor=tk.W, padx=10)
    
    def _setup_layout(self):
        """Set up the layout for all widgets"""
        self.server_frame.pack(fill=tk.X, padx=5, pady=5)
        self.config_frame.pack(fill=tk.X, padx=5, pady=5)
        self.api_key_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _show_api_examples(self):
        """Show examples of API usage in different languages/platforms"""
        # Create a new window
        examples_window = tk.Toplevel(self)
        examples_window.title("Примеры использования API переводчика")
        examples_window.geometry("800x600")
        examples_window.transient(self)  # Make window modal
        examples_window.grab_set()
        
        # Configure theme colors if available
        theme_bg = "#1A1B2E"  # default dark background
        theme_fg = "#FFFFFF"  # default light text
        theme_accent = "#3F51B5"  # default accent color
        
        try:
            if hasattr(self.master.master, 'theme_manager'):
                theme = self.master.master.theme_manager.get_theme()
                theme_bg = theme.get('bg', theme_bg)
                theme_fg = theme.get('fg', theme_fg)
                theme_accent = theme.get('accent', theme_accent)
        except:
            pass
            
        examples_window.configure(bg=theme_bg)
        
        # Create notebook for tabs
        tab_control = ttk.Notebook(examples_window)
        tab_control.pack(expand=1, fill="both", padx=10, pady=10)
        
        # Function to create a tab with code example
        def create_example_tab(title, code, description):
            tab = ttk.Frame(tab_control)
            tab_control.add(tab, text=title)
            
            # Description
            desc_label = ttk.Label(tab, text=description, wraplength=750)
            desc_label.pack(pady=10, padx=10, anchor=tk.W)
            
            # Code area
            code_frame = ttk.Frame(tab)
            code_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            code_text = scrolledtext.ScrolledText(
                code_frame, 
                wrap=tk.WORD,
                bg="#2A2A3A",
                fg="#E0E0E0",
                height=15
            )
            code_text.pack(fill=tk.BOTH, expand=True)
            code_text.insert(tk.END, code)
            code_text.config(state=tk.DISABLED)
            
            # Copy button
            copy_button = ttk.Button(
                tab, 
                text="Копировать код",
                command=lambda: self._copy_to_clipboard(code)
            )
            copy_button.pack(pady=10)
            
            return tab
        
        # Python example using requests
        python_requests_code = """import requests

# Конфигурация
API_URL = "http://localhost:8000/api/translate"
API_KEY = "YOUR_API_KEY_HERE"

# Текст для перевода
text_to_translate = "Hello, world! This is a test message."

# Заголовки запроса
headers = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

# Данные запроса
data = {
    "text": text_to_translate
}

# Отправка запроса
response = requests.post(API_URL, json=data, headers=headers)

# Вывод результата
if response.status_code == 200:
    result = response.json()
    print(f"Перевод: {result['translated_text']}")
else:
    print(f"Ошибка: {response.status_code}, {response.text}")
"""
        create_example_tab("Python (requests)", python_requests_code, 
                         "Пример использования API с библиотекой requests в Python")
        
        # Python example using OpenAI library
        python_openai_code = """from openai import OpenAI

# Конфигурация
client = OpenAI(
    api_key="YOUR_API_KEY_HERE",
    base_url="http://localhost:8000"  # Важно: используйте базовый URL сервера без дополнительных путей
)

# Текст для перевода
text_to_translate = "Hello, world! This is a test message."

# Отправка запроса через OpenAI API
response = client.chat.completions.create(
    model="any-model-name",  # можно указать любое имя модели
    messages=[
        {"role": "user", "content": text_to_translate}
    ]
)

# Вывод результата
translated_text = response.choices[0].message.content
print(f"Перевод: {translated_text}")
"""
        create_example_tab("Python (OpenAI)", python_openai_code, 
                         "Пример использования API через библиотеку OpenAI в Python. ВАЖНО: base_url должен содержать только базовый URL сервера (http://localhost:8000) без дополнительных путей.")
        
        # Python example with streaming
        python_streaming_code = """from openai import OpenAI

# Конфигурация
client = OpenAI(
    api_key="YOUR_API_KEY_HERE",
    base_url="http://localhost:8000"  # Важно: используйте базовый URL без дополнительных путей
)

# Текст для перевода
text_to_translate = "Hello, world! This is a test message."

# Отправка потокового запроса через OpenAI API
stream = client.chat.completions.create(
    model="any-model-name",  # можно указать любое имя модели
    messages=[
        {"role": "user", "content": text_to_translate}
    ],
    stream=True  # Запрос потокового ответа
)

# Обработка потокового ответа
print("Перевод (по частям):")
full_response = ""
for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        content = chunk.choices[0].delta.content
        full_response += content
        print(content, end="", flush=True)
print()
print(f"Полный ответ: {full_response}")
"""
        create_example_tab("Python (Streaming)", python_streaming_code, 
                         "Пример использования API с потоковым ответом (stream=True). Это нужно для клиентов, ожидающих поэтапное получение результата.")
        
        # JavaScript example
        js_code = """// С использованием fetch API
async function translateText() {
    const API_URL = "http://localhost:8000/api/translate";
    const API_KEY = "YOUR_API_KEY_HERE";
    
    const textToTranslate = "Hello, world! This is a test message.";
    
    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "api-key": API_KEY,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: textToTranslate
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log("Перевод:", result.translated_text);
            // Отобразить перевод на странице
            document.getElementById("result").textContent = result.translated_text;
        } else {
            console.error("Ошибка:", response.status, result);
        }
    } catch (error) {
        console.error("Ошибка при выполнении запроса:", error);
    }
}

// Вызов функции
translateText();
"""
        create_example_tab("JavaScript", js_code, 
                         "Пример использования API с JavaScript и fetch API")
        
        # JavaScript streaming example
        js_streaming_code = """// С использованием Fetch API и EventSource для потокового ответа
async function translateTextStreaming() {
    const API_URL = "http://localhost:8000/v1/chat/completions";
    const API_KEY = "YOUR_API_KEY_HERE";
    
    const textToTranslate = "Hello, world! This is a test message.";
    
    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${API_KEY}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: "any-model-name",
                messages: [
                    { role: "user", content: textToTranslate }
                ],
                stream: true  // Запрос потокового ответа
            })
        });
        
        // Проверка на ошибки
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API request failed: ${response.status} ${errorText}`);
        }
        
        // Получение и обработка потокового ответа
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        const resultElement = document.getElementById("result");
        let fullResponse = "";
        
        // Функция для обработки потока данных
        async function readStream() {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                // Декодирование полученных данных
                const chunk = decoder.decode(value);
                
                // Разбор данных SSE (Server-Sent Events)
                const lines = chunk.split("\\n");
                for (const line of lines) {
                    if (line.startsWith("data: ") && line !== "data: [DONE]") {
                        const jsonStr = line.substring(6);
                        try {
                            const json = JSON.parse(jsonStr);
                            if (json.choices && json.choices[0].delta && json.choices[0].delta.content) {
                                const content = json.choices[0].delta.content;
                                full_response += content;
                                resultElement.textContent = fullResponse;
                            }
                        } catch (e) {
                            console.warn("Could not parse JSON:", jsonStr);
                        }
                    }
                }
            }
            
            console.log("Stream complete. Full response:", fullResponse);
        }
        
        // Начать обработку потока
        await readStream();
        
    } catch (error) {
        console.error("Error:", error);
        document.getElementById("result").textContent = `Error: ${error.message}`;
    }
}

// Вызов функции
translateTextStreaming();
"""
        create_example_tab("JS Streaming", js_streaming_code,
                        "Пример использования API с потоковым ответом в JavaScript.")
        
        # cURL example
        curl_code = """# Запрос к стандартному API
curl -X POST http://localhost:8000/api/translate \\
  -H "api-key: YOUR_API_KEY_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello, world! This is a test message."}'

# Запрос к OpenAI-совместимому API
curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "any-model-name",
    "messages": [
      {"role": "user", "content": "Hello, world! This is a test message."}
    ]
  }'

# ВАЖНО: адрес должен быть http://localhost:8000/v1/chat/completions
# Не добавляйте /api/translate/ перед /v1/chat/completions
"""
        create_example_tab("cURL", curl_code, 
                         "Примеры команд cURL для использования API из командной строки. Обратите внимание на правильное формирование URL для OpenAI API.")
        
        # C# example
        csharp_code = """using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace TranslatorApiClient
{
    class Program
    {
        static async Task Main(string[] args)
        {
            // Конфигурация
            string apiUrl = "http://localhost:8000/api/translate";
            string apiKey = "YOUR_API_KEY_HERE";
            string textToTranslate = "Hello, world! This is a test message.";
            
            // Создание HTTP клиента
            using (HttpClient client = new HttpClient())
            {
                // Настройка заголовков
                client.DefaultRequestHeaders.Add("api-key", apiKey);
                
                // Создание данных запроса
                var requestData = new
                {
                    text = textToTranslate
                };
                
                // Сериализация данных в JSON
                string jsonContent = JsonConvert.SerializeObject(requestData);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");
                
                // Отправка запроса
                HttpResponseMessage response = await client.PostAsync(apiUrl, content);
                
                // Обработка ответа
                if (response.IsSuccessStatusCode)
                {
                    string responseJson = await response.Content.ReadAsStringAsync();
                    var result = JsonConvert.DeserializeAnonymousType(responseJson, new { translated_text = "" });
                    
                    Console.WriteLine($"Перевод: {result.translated_text}");
                }
                else
                {
                    Console.WriteLine($"Ошибка: {response.StatusCode}, {await response.Content.ReadAsStringAsync()}");
                }
            }
        }
    }
}
"""
        create_example_tab("C#", csharp_code, 
                         "Пример использования API из приложения на C#")
        
        # Batch processing example
        batch_code = """import requests

# Конфигурация
API_URL = "http://localhost:8000/api/translate_batch"
API_KEY = "YOUR_API_KEY_HERE"

# Тексты для перевода
texts_to_translate = [
    "Hello, world!",
    "How are you doing?",
    "Machine translation is amazing!"
]

# Заголовки запроса
headers = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

# Данные запроса
data = {
    "texts": texts_to_translate
}

# Отправка запроса
response = requests.post(API_URL, json=data, headers=headers)

# Вывод результата
if response.status_code == 200:
    result = response.json()
    
    print("Результаты перевода:")
    for i, (original, translated) in enumerate(zip(texts_to_translate, result["translated_texts"])):
        print(f"{i+1}. Оригинал: {original}")
        print(f"   Перевод: {translated}")
        print()
else:
    print(f"Ошибка: {response.status_code}, {response.text}")
"""
        create_example_tab("Batch API", batch_code, 
                         "Пример пакетного перевода нескольких текстов через API")
        
        # Close button
        close_button = ttk.Button(
            examples_window, 
            text="Закрыть",
            command=examples_window.destroy
        )
        close_button.pack(pady=10)
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(text)
        
        # Show notification
        if self.on_status_change:
            self.on_status_change("Код скопирован в буфер обмена", "info")
        
    def _start_server(self):
        """Start the API server"""
        if self.api_server and self.api_server.running:
            messagebox.showinfo("Info", "Server is already running")
            return
        
        # Get host and port
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
        
        # Create server instance if it doesn't exist
        if not self.api_server:
            self.api_server = ApiServer(host=host, port=port)
        
        # Start server in a thread to prevent UI freezing
        try:
            self.api_server.start()
            
            # Update UI
            status = f"Server: Running on http://{self.api_server.host}:{self.api_server.port}"
            self.server_status_label.config(text=status)
            self.start_server_button.config(state=tk.DISABLED)
            self.stop_server_button.config(state=tk.NORMAL)
            
            # Update status bar
            if self.on_status_change:
                self.on_status_change(f"Server started on {host}:{port}", "success")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            if self.on_status_change:
                self.on_status_change(f"Server start failed: {str(e)}", "error")
    
    def _stop_server(self):
        """Stop the API server"""
        if not self.api_server or not self.api_server.running:
            messagebox.showinfo("Info", "Server is not running")
            return
        
        # Stop the server
        self.api_server.stop()
        
        # Update UI
        self.server_status_label.config(text="Server: Not running")
        self.start_server_button.config(state=tk.NORMAL)
        self.stop_server_button.config(state=tk.DISABLED)
        
        # Update status bar
        if self.on_status_change:
            self.on_status_change("Server stopped", "info")
    
    def _apply_configuration(self):
        """Apply server configuration changes"""
        if self.api_server and self.api_server.running:
            messagebox.showinfo(
                "Info", 
                "You need to stop the server before changing configuration"
            )
            return
            
        # If the server exists but isn't running, create a new one
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
            
        self.api_server = ApiServer(host=host, port=port)
        
        # Сохраняем конфигурацию в настройках
        set_setting("server.host", host)
        set_setting("server.port", port)
        
        # Update status bar
        if self.on_status_change:
            self.on_status_change("Server configuration updated", "info")
    
    def _generate_api_key(self):
        """Generate a new API key"""
        # Generate new universal key
        api_key = generate_api_key()
        
        # Save the API key
        save_api_key(api_key, {"created_at": "Generated from UI"})
        
        # Update UI
        self.api_key_text.config(state=tk.NORMAL)
        self.api_key_text.delete("1.0", tk.END)
        self.api_key_text.insert("1.0", api_key)
        self.api_key_text.config(state=tk.DISABLED)
        
        # Сохраняем API-ключ в настройках
        set_setting("api.last_key", api_key)
        
        # Update status bar
        if self.on_status_change:
            self.on_status_change("New API key generated", "success")
    
    def _copy_api_key(self):
        """Copy API key to clipboard"""
        api_key = self.api_key_text.get("1.0", tk.END).strip()
        if not api_key:
            messagebox.showinfo("Info", "No API key to copy")
            return
            
        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(api_key)
        
        # Update status bar
        if self.on_status_change:
            self.on_status_change("API key copied to clipboard", "info")
    
    def _test_api(self):
        """Test the API with a simple request"""
        if not self.api_server or not self.api_server.running:
            messagebox.showinfo("Info", "Сначала запустите сервер")
            return
        
        # Get current API key
        api_key = self.api_key_text.get("1.0", tk.END).strip()
        if not api_key:
            # Generate a new key if none exists
            self._generate_api_key()
            api_key = self.api_key_text.get("1.0", tk.END).strip()
        
        # Create test dialog
        test_window = tk.Toplevel(self)
        test_window.title("Тест API переводчика")
        test_window.geometry("600x500")
        test_window.transient(self)
        test_window.grab_set()
        
        # Configure theme colors if available
        theme_bg = "#1A1B2E"  # default dark background
        theme_fg = "#FFFFFF"  # default light text
        theme_accent = "#3F51B5"  # default accent color
        text_bg = "#2A2A3A"  # default text background
        text_fg = "#E0E0E0"  # default text color
        
        try:
            if hasattr(self.master.master, 'theme_manager'):
                theme = self.master.master.theme_manager.get_theme()
                theme_bg = theme.get('bg', theme_bg)
                theme_fg = theme.get('fg', theme_fg)
                theme_accent = theme.get('accent', theme_accent)
                text_bg = theme.get('text_bg', text_bg)
                text_fg = theme.get('text_fg', text_fg)
        except:
            pass
        
        test_window.configure(bg=theme_bg)
        
        # Test input section
        input_frame = ttk.LabelFrame(test_window, text="Ввод текста для перевода")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input text area
        input_text = scrolledtext.ScrolledText(
            input_frame, 
            wrap=tk.WORD,
            bg=text_bg,
            fg=text_fg,
            height=5
        )
        input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        input_text.insert(tk.END, "Hello, world! This is a test message.")
        
        # Options section
        options_frame = ttk.Frame(test_window)
        options_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # API Endpoint selection
        endpoint_frame = ttk.Frame(options_frame)
        endpoint_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(endpoint_frame, text="API Endpoint:").pack(side=tk.LEFT, padx=(0, 5))
        
        endpoint_type = tk.StringVar(value="translate")
        endpoints = {
            "translate": "Standard (/api/translate)",
            "openai": "OpenAI (/v1/chat/completions)"
        }
        
        endpoint_combo = ttk.Combobox(
            endpoint_frame,
            textvariable=endpoint_type,
            values=list(endpoints.values()),
            state="readonly",
            width=30
        )
        endpoint_combo.current(0)
        endpoint_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Stream option (только для OpenAI API)
        stream_frame = ttk.Frame(options_frame)
        stream_frame.pack(fill=tk.X, pady=5)
        
        stream_var = tk.BooleanVar(value=False)
        stream_check = ttk.Checkbutton(
            stream_frame,
            text="Потоковый ответ (stream=True, только для OpenAI API)",
            variable=stream_var,
            onvalue=True,
            offvalue=False
        )
        stream_check.pack(side=tk.LEFT)
        
        # Disable stream option when standard API is selected
        def toggle_stream_option(*args):
            if "Standard" in endpoint_combo.get():
                stream_check.config(state=tk.DISABLED)
                stream_var.set(False)
            else:
                stream_check.config(state=tk.NORMAL)
        
        endpoint_type.trace_add("write", toggle_stream_option)
        toggle_stream_option()  # Initial state
        
        # Test button
        test_button = ttk.Button(
            test_window, 
            text="Выполнить запрос",
            command=lambda: self._run_api_test(
                input_text.get("1.0", tk.END).strip(),
                api_key,
                "openai" if "OpenAI" in endpoint_combo.get() else "translate",
                stream_var.get(),
                result_text
            )
        )
        test_button.pack(pady=10)
        
        # Results section
        result_frame = ttk.LabelFrame(test_window, text="Результат")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        result_text = scrolledtext.ScrolledText(
            result_frame, 
            wrap=tk.WORD,
            bg=text_bg,
            fg=text_fg,
            height=10
        )
        result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        result_text.insert(tk.END, "Результат запроса будет отображен здесь")
        
        # Close button
        close_button = ttk.Button(
            test_window, 
            text="Закрыть",
            command=test_window.destroy
        )
        close_button.pack(pady=10)
    
    def _run_api_test(self, text, api_key, endpoint, use_stream, result_text_widget):
        """Run API test with the given parameters"""
        if not text:
            messagebox.showinfo("Info", "Введите текст для перевода")
            return
        
        # Clear result area
        result_text_widget.delete("1.0", tk.END)
        result_text_widget.insert(tk.END, "Выполняется запрос...\n\n")
        
        # Get server URL
        host = self.host_entry.get().strip() or "127.0.0.1"
        port = self.port_entry.get().strip() or "8000"
        base_url = f"http://{host}:{port}"
        
        # Run test in a separate thread
        def test_thread():
            try:
                if endpoint == "translate":
                    # Standard API request
                    url = f"{base_url}/api/translate"
                    
                    # Можно использовать оба формата заголовков с универсальным ключом
                    # Для демонстрации используем оба
                    headers = {
                        "api-key": api_key,
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    data = {"text": text}
                    
                    response = requests.post(url, json=data, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        translated = result.get("translated_text", "")
                        
                        # Update result in UI thread
                        self.after(0, lambda: self._update_test_result(
                            result_text_widget,
                            f"ЗАПРОС:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n\n" +
                            f"ЗАГОЛОВКИ:\n{json.dumps(headers, indent=2, ensure_ascii=False)}\n\n" +
                            f"ОТВЕТ:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n\n" +
                            f"РЕЗУЛЬТАТ ПЕРЕВОДА:\n{translated}"
                        ))
                    else:
                        # Error response
                        self.after(0, lambda: self._update_test_result(
                            result_text_widget,
                            f"ОШИБКА: {response.status_code}\n\n{response.text}"
                        ))
                else:
                    # OpenAI compatible API
                    url = f"{base_url}/v1/chat/completions"
                    
                    # Можно использовать оба формата заголовков с универсальным ключом
                    # Для демонстрации используем оба
                    headers = {
                        "api-key": api_key,
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    data = {
                        "model": "translator-model",
                        "messages": [
                            {"role": "user", "content": text}
                        ],
                        "stream": use_stream
                    }
                    
                    if use_stream:
                        # Потоковый запрос
                        self.after(0, lambda: result_text_widget.insert(tk.END, "Получение потокового ответа...\n\n"))
                        
                        # Используем stream=True для requests
                        response = requests.post(url, json=data, headers=headers, stream=True)
                        
                        if response.status_code == 200:
                            full_response = ""
                            collected_json = []
                            
                            # Обновляем информацию о запросе
                            self.after(0, lambda: self._update_test_result(
                                result_text_widget,
                                f"ЗАПРОС:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n\n" +
                                f"ЗАГОЛОВКИ:\n{json.dumps(headers, indent=2, ensure_ascii=False)}\n\n" +
                                "ПОЛУЧЕНИЕ ПОТОКОВОГО ОТВЕТА:\n"
                            ))
                            
                            # Обрабатываем поток данных
                            for line in response.iter_lines():
                                if line:
                                    line_text = line.decode('utf-8')
                                    if line_text.startswith('data: '):
                                        if line_text == 'data: [DONE]':
                                            # Поток завершен
                                            break
                                            
                                        json_str = line_text[6:]  # Remove 'data: ' prefix
                                        try:
                                            json_data = json.loads(json_str)
                                            collected_json.append(json_data)
                                            
                                            # Extract content if available
                                            if (json_data.get('choices') and 
                                                json_data['choices'][0].get('delta') and 
                                                json_data['choices'][0]['delta'].get('content')):
                                                
                                                content = json_data['choices'][0]['delta']['content']
                                                full_response += content
                                                
                                                # Update in UI thread
                                                self.after(0, lambda c=content: result_text_widget.insert(tk.END, c))
                                        except json.JSONDecodeError:
                                            # Not valid JSON, skip
                                            pass
                            
                            # Final update with the collected data
                            self.after(0, lambda: result_text_widget.insert(tk.END, 
                                f"\n\nПОЛНЫЙ ОТВЕТ:\n{full_response}\n\n" +
                                f"ДЕТАЛИ ОТВЕТА:\n{json.dumps(collected_json, indent=2, ensure_ascii=False)}"
                            ))
                        else:
                            # Error response
                            self.after(0, lambda: self._update_test_result(
                                result_text_widget,
                                f"ОШИБКА: {response.status_code}\n\n{response.text}"
                            ))
                    else:
                        # Обычный запрос
                        response = requests.post(url, json=data, headers=headers)
                        
                        if response.status_code == 200:
                            result = response.json()
                            translated = ""
                            
                            # Extract translated text from OpenAI format
                            try:
                                translated = result["choices"][0]["message"]["content"]
                            except (KeyError, IndexError):
                                translated = "Ошибка извлечения перевода из ответа"
                            
                            # Update result in UI thread
                            self.after(0, lambda: self._update_test_result(
                                result_text_widget,
                                f"ЗАПРОС:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n\n" +
                                f"ЗАГОЛОВКИ:\n{json.dumps(headers, indent=2, ensure_ascii=False)}\n\n" +
                                f"ОТВЕТ:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n\n" +
                                f"РЕЗУЛЬТАТ ПЕРЕВОДА:\n{translated}"
                            ))
                        else:
                            # Error response
                            self.after(0, lambda: self._update_test_result(
                                result_text_widget,
                                f"ОШИБКА: {response.status_code}\n\n{response.text}"
                            ))
                        
            except Exception as e:
                # Update error in UI thread
                self.after(0, lambda: self._update_test_result(
                    result_text_widget,
                    f"ОШИБКА: {str(e)}"
                ))
        
        thread = threading.Thread(target=test_thread)
        thread.daemon = True
        thread.start()
    
    def _update_test_result(self, text_widget, result):
        """Update test result text widget"""
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, result) 