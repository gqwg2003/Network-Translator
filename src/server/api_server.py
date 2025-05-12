from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import uvicorn
import threading
import time
from datetime import datetime
import logging
import json
import asyncio
import psutil
import httpx

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("translator-api")

from src.translator.translator import Translator
from src.utils.api_utils import (
    generate_api_key, validate_api_key, load_api_keys, 
    save_api_key, revoke_api_key
)

# Models for API requests and responses
class TranslationRequest(BaseModel):
    text: str
    apply_formatting: bool = True

class BatchTranslationRequest(BaseModel):
    texts: List[str]
    apply_formatting: bool = True

class TranslationResponse(BaseModel):
    translated_text: str

class BatchTranslationResponse(BaseModel):
    translated_texts: List[str]

class ApiKeyResponse(BaseModel):
    api_key: str
    message: str

class CacheControlRequest(BaseModel):
    enabled: bool

class CacheStatusResponse(BaseModel):
    enabled: bool
    entries: int
    message: str

class ServerStatusResponse(BaseModel):
    status: str = "ok"
    uptime: int
    translator_ready: bool
    cache_enabled: bool
    cache_entries: int
    cpu_usage: float
    memory_usage: float
    requests_handled: int
    formatting_enabled: bool
    formatting_options: Dict[str, bool]

class FormattingOptionsRequest(BaseModel):
    smart_quotes: Optional[bool] = None
    russian_punctuation: Optional[bool] = None
    normalize_whitespace: Optional[bool] = None
    fix_common_issues: Optional[bool] = None

class FormattingOptionsResponse(BaseModel):
    options: Dict[str, bool]
    message: str

# OpenAI API compatibility models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

class ChatCompletionChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionChoiceMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int] = Field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })

class ApiServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        """
        Initialize the API server
        
        Args:
            host: The host to run the server on
            port: The port to run the server on
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="Neural Network Translator API")
        self.translator = Translator()
        self.server_thread = None
        self.running = False
        self.start_time = time.time()
        self.requests_handled = 0
        
        # Set up CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up the API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "Neural Network Translator API"}
        
        @self.app.get("/api/status", response_model=ServerStatusResponse)
        async def server_status():
            self.requests_handled += 1
            
            uptime = int(time.time() - self.start_time)
            model_info = self.translator.get_model_info()
            
            # Get system stats
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            return ServerStatusResponse(
                uptime=uptime,
                translator_ready=model_info.get("model_loaded", False),
                cache_enabled=model_info.get("cache_enabled", False),
                cache_entries=model_info.get("cache_entries", 0),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                requests_handled=self.requests_handled,
                formatting_enabled=any(self.translator.formatting_options.values()),
                formatting_options=self.translator.formatting_options
            )
        
        @self.app.post("/api/translate", response_model=TranslationResponse)
        async def translate(
            request: TranslationRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            self.requests_handled += 1
            translated = self.translator.translate(
                request.text, 
                apply_formatting=request.apply_formatting
            )
            logger.info(f"Перевод: '{request.text}' -> '{translated}'")
            return TranslationResponse(translated_text=translated)
        
        @self.app.post("/api/translate_batch", response_model=BatchTranslationResponse)
        async def translate_batch(
            request: BatchTranslationRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            self.requests_handled += 1
            translated = self.translator.translate_batch(
                request.texts,
                apply_formatting=request.apply_formatting
            )
            return BatchTranslationResponse(translated_texts=translated)
        
        @self.app.get("/api/formatting/options", response_model=FormattingOptionsResponse)
        async def get_formatting_options(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            return FormattingOptionsResponse(
                options=self.translator.get_formatting_options(),
                message="Formatting options retrieved successfully"
            )
        
        @self.app.post("/api/formatting/options", response_model=FormattingOptionsResponse)
        async def set_formatting_options(
            request: FormattingOptionsRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            # Обновляем только те опции, которые были предоставлены в запросе
            options_to_update = {}
            for key, value in request.dict().items():
                if value is not None:
                    options_to_update[key] = value
                    
            self.translator.set_formatting_options(options_to_update)
            
            return FormattingOptionsResponse(
                options=self.translator.get_formatting_options(),
                message="Formatting options updated successfully"
            )
        
        @self.app.post("/api/cache/control", response_model=CacheStatusResponse)
        async def control_cache(
            request: CacheControlRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            self.translator.set_cache_enabled(request.enabled)
            
            cache_status = {
                "enabled": self.translator.cache_enabled,
                "entries": len(self.translator.translation_cache) if self.translator.cache_enabled else 0,
                "message": f"Cache {'enabled' if request.enabled else 'disabled'} successfully"
            }
            
            return CacheStatusResponse(**cache_status)
        
        @self.app.post("/api/cache/clear", response_model=CacheStatusResponse)
        async def clear_cache(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            self.translator.clear_cache()
            
            cache_status = {
                "enabled": self.translator.cache_enabled,
                "entries": 0,
                "message": "Cache cleared successfully"
            }
            
            return CacheStatusResponse(**cache_status)
        
        @self.app.get("/api/cache/status", response_model=CacheStatusResponse)
        async def cache_status(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            cache_status = {
                "enabled": self.translator.cache_enabled,
                "entries": len(self.translator.translation_cache) if self.translator.cache_enabled else 0,
                "message": "Cache status retrieved successfully"
            }
            
            return CacheStatusResponse(**cache_status)
        
        @self.app.post("/api/generate_key", response_model=ApiKeyResponse)
        async def generate_key():
            api_key = generate_api_key()
            save_api_key(api_key, {"created_at": str(datetime.now())})
            
            return ApiKeyResponse(
                api_key=api_key,
                message="API key generated successfully"
            )
        
        @self.app.delete("/api/revoke_key")
        async def revoke_key(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            success = revoke_api_key(key)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to revoke API key")
            
            return {"message": "API key revoked successfully"}
        
        # OpenAI API compatibility endpoint
        @self.app.post("/v1/chat/completions")
        async def chat_completions(
            request: ChatCompletionRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Логируем входящий запрос
            logger.info(f"Получен запрос к OpenAI API: {request}")
            
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            # Extract text to translate from the last user message
            text_to_translate = ""
            for message in reversed(request.messages):
                if message.role == "user":
                    text_to_translate = message.content
                    break
            
            if not text_to_translate:
                logger.error("Сообщение пользователя не найдено")
                raise HTTPException(status_code=400, detail="No user message found to translate")
            
            # Translate the text
            logger.info(f"Переводим текст: '{text_to_translate}'")
            translated_text = self.translator.translate(text_to_translate, apply_formatting=True)
            logger.info(f"Результат перевода: '{translated_text}'")
            
            # Print debug info to console
            print(f"\n=== ПЕРЕВОД ===")
            print(f"Исходный текст: {text_to_translate}")
            print(f"Переведенный текст: {translated_text}")
            print(f"===============\n")
            
            # Check if the client requested streaming
            if request.stream:
                logger.info("Клиент запросил потоковый ответ, отправляем SSE")
                return self._stream_response(request.model, translated_text)
            
            # Create response in OpenAI format (non-streaming)
            response = ChatCompletionResponse(
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        message=ChatCompletionChoiceMessage(
                            content=translated_text
                        )
                    )
                ]
            )
            
            return response
        
        @self.app.post("/api/translate/v1/chat/completions")
        async def alternative_chat_completions(request: Request):
            # Capture the raw request and forward it to the proper endpoint
            try:
                # Read the raw body
                body = await request.body()
                
                # Get all headers
                headers = dict(request.headers)
                
                # Проверяем, запрашивается ли потоковый режим
                is_stream = False
                try:
                    # Пытаемся проверить stream параметр в JSON
                    request_data = json.loads(body)
                    is_stream = request_data.get("stream", False)
                except json.JSONDecodeError:
                    # Если не можем разобрать JSON, предполагаем обычный запрос
                    pass
                
                # Создаем URL для перенаправления
                target_url = f"http://{self.host}:{self.port}/v1/chat/completions"
                
                # Если запрашивается поток, перенаправляем как поток
                if is_stream:
                    # Используем прямое прокси соединение
                    async def stream_generator():
                        async with httpx.AsyncClient() as client:
                            async with client.stream("POST", target_url, content=body, headers=headers) as response:
                                async for chunk in response.aiter_bytes():
                                    yield chunk
                
                    # Возвращаем потоковый ответ с тем же content-type
                    return StreamingResponse(
                        stream_generator(),
                        media_type="text/event-stream"
                    )
                else:
                    # Для обычных запросов используем стандартный подход
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            target_url,
                            content=body,
                            headers=headers
                        )
                        
                        return JSONResponse(
                            content=response.json(),
                            status_code=response.status_code
                        )
            except Exception as e:
                logger.error(f"Error forwarding request: {e}")
                raise HTTPException(status_code=500, detail=f"Error forwarding request: {str(e)}")
    
    def _stream_response(self, model: str, translated_text: str):
        """
        Create a streaming response for chat completions
        
        Args:
            model: The model name
            translated_text: The translated text to stream
        
        Returns:
            A streaming response
        """
        async def generate():
            # SSE должно иметь правильный формат: data: {json}\n\n
            
            # Сначала отправляем начало ответа
            id_base = f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            created = int(datetime.now().timestamp())
            
            # Разбиваем текст на слова для имитации постепенной генерации
            words = translated_text.split()
            tokens = []
            current_token = ""
            
            # Создаем примерно 10-20 токенов из слов
            # (делаем более реалистичную имитацию токенизации)
            for word in words:
                if len(current_token) + len(word) < 10:
                    current_token += " " + word if current_token else word
                else:
                    tokens.append(current_token)
                    current_token = word
            
            # Добавляем последний токен
            if current_token:
                tokens.append(current_token)
            
            # Если токенов мало, разбиваем последний токен на символы
            if len(tokens) < 5:
                last = tokens.pop()
                for i in range(0, len(last), 3):
                    tokens.append(last[i:i+3])
            
            # Отправляем токены по одному
            for i, token in enumerate(tokens):
                is_last = i == len(tokens) - 1
                partial_text = " ".join(tokens[:i+1])
                
                event = {
                    "id": f"{id_base}-{i}",
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": token if i > 0 else token
                            } if not is_last else {},
                            "finish_reason": "stop" if is_last else None
                        }
                    ]
                }
                
                # Выравниваем результаты для потокового режима
                yield f"data: {json.dumps(event)}\n\n"
                
                # Имитируем задержку генерации
                await asyncio.sleep(0.05)
            
            # Финальный маркер для SSE
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    
    def _extract_api_key(self, api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
        """
        Extract the API key from the headers
        
        Args:
            api_key: The API key header
            authorization: The authorization header
            
        Returns:
            The extracted API key
        """
        # Приоритет: 1. api-key header, 2. authorization header
        if api_key:
            return api_key
            
        if authorization:
            # Обработка формата Bearer {token}
            if authorization.startswith("Bearer "):
                return authorization[7:]
                
            # Обработка наличия только токена
            return authorization
            
        return None
    
    def _validate_api_key_or_raise(self, api_key: Optional[str]):
        """
        Validate the API key or raise an exception
        
        Args:
            api_key: The API key to validate
            
        Raises:
            HTTPException: If the API key is invalid
        """
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key is required",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        # Load API keys before validation
        api_keys = load_api_keys()
        is_valid = validate_api_key(api_key, api_keys)
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def start(self):
        """Start the API server"""
        if self.running:
            return
        
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        
        print(f"API server started on http://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the API server"""
        if self.server_thread and self.running:
            # There's no clean way to stop a uvicorn server from another thread
            # The process will be terminated when the main thread exits
            self.running = False
            print("API server is shutting down...") 