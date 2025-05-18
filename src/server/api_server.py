from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
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
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("translator-api")

from src.translator.translator import Translator
from src.utils.api_utils import (
    generate_api_key, validate_api_key, load_api_keys, 
    save_api_key, revoke_api_key
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Models for API requests and responses
class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    apply_formatting: bool = True

    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or contain only whitespace')
        return v.strip()

class BatchTranslationRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=100)
    apply_formatting: bool = True

    @validator('texts')
    def validate_texts(cls, v):
        for text in v:
            if not text.strip():
                raise ValueError('Texts cannot contain empty strings or strings with only whitespace')
        return [text.strip() for text in v]

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

    @validator('*')
    def validate_options(cls, v):
        if v is not None and not isinstance(v, bool):
            raise ValueError('All formatting options must be boolean values')
        return v

class FormattingOptionsResponse(BaseModel):
    options: Dict[str, bool]
    message: str

# OpenAI API compatibility models
class ChatMessage(BaseModel):
    role: str = Field(..., regex='^(system|user|assistant)$')
    content: str = Field(..., min_length=1)

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., min_length=1)
    messages: List[ChatMessage] = Field(..., min_items=1)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
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
        
        # Add rate limiting
        self.app.state.limiter = limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        # Add trusted hosts middleware
        self.app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=["*"]  # В продакшене заменить на конкретные хосты
        )
        
        # Add error handlers
        self.app.add_exception_handler(Exception, self._handle_exception)
        
        self._setup_routes()
    
    async def _handle_exception(self, request: Request, exc: Exception):
        """Global exception handler"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers
            )
            
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    def _setup_routes(self):
        """Set up the API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "Neural Network Translator API"}
        
        @self.app.get("/api/status", response_model=ServerStatusResponse)
        @limiter.limit("60/minute")
        async def server_status():
            try:
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
            except Exception as e:
                logger.error(f"Error in server_status: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get server status"
                )
        
        @self.app.post("/api/translate", response_model=TranslationResponse)
        @limiter.limit("30/minute")
        async def translate(
            request: TranslationRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
                # Получаем API-ключ из любого доступного заголовка
                key = self._extract_api_key(api_key, authorization)
                self._validate_api_key_or_raise(key)
                
                self.requests_handled += 1
                
                # Проверяем, что модель загружена
                if not self.translator.model.model or not self.translator.model.tokenizer:
                    raise HTTPException(
                        status_code=503,
                        detail="Translation model is not loaded"
                    )
                
                # Проверяем длину текста
                if len(request.text) > 5000:
                    raise HTTPException(
                        status_code=400,
                        detail="Text length exceeds maximum limit of 5000 characters"
                    )
                
                translated = self.translator.translate(
                    request.text, 
                    apply_formatting=request.apply_formatting
                )
                
                if translated.startswith("Error:"):
                    raise HTTPException(
                        status_code=500,
                        detail=translated
                    )
                    
                logger.info(f"Перевод: '{request.text}' -> '{translated}'")
                return TranslationResponse(translated_text=translated)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error during translation: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error during translation"
                )
        
        @self.app.post("/api/translate_batch", response_model=BatchTranslationResponse)
        @limiter.limit("20/minute")
        async def translate_batch(
            request: BatchTranslationRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
                # Получаем API-ключ из любого доступного заголовка
                key = self._extract_api_key(api_key, authorization)
                self._validate_api_key_or_raise(key)
                
                self.requests_handled += 1
                
                # Проверяем, что модель загружена
                if not self.translator.model.model or not self.translator.model.tokenizer:
                    raise HTTPException(
                        status_code=503,
                        detail="Translation model is not loaded"
                    )
                
                # Проверяем общую длину всех текстов
                total_length = sum(len(text) for text in request.texts)
                if total_length > 10000:  # Максимальная общая длина для batch
                    raise HTTPException(
                        status_code=400,
                        detail="Total text length exceeds maximum limit of 10000 characters"
                    )
                
                translated = self.translator.translate_batch(
                    request.texts,
                    apply_formatting=request.apply_formatting
                )
                
                if any(t.startswith("Error:") for t in translated):
                    raise HTTPException(
                        status_code=500,
                        detail="Error occurred during batch translation"
                    )
                    
                return BatchTranslationResponse(translated_texts=translated)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error during batch translation: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error during batch translation"
                )
        
        @self.app.get("/api/formatting/options", response_model=FormattingOptionsResponse)
        @limiter.limit("60/minute")
        async def get_formatting_options(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
                # Получаем API-ключ из любого доступного заголовка
                key = self._extract_api_key(api_key, authorization)
                self._validate_api_key_or_raise(key)
                
                return FormattingOptionsResponse(
                    options=self.translator.get_formatting_options(),
                    message="Formatting options retrieved successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting formatting options: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get formatting options"
                )
        
        @self.app.post("/api/formatting/options", response_model=FormattingOptionsResponse)
        @limiter.limit("30/minute")
        async def set_formatting_options(
            request: FormattingOptionsRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
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
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error setting formatting options: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update formatting options"
                )
        
        @self.app.post("/api/cache/control", response_model=CacheStatusResponse)
        @limiter.limit("30/minute")
        async def control_cache(
            request: CacheControlRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
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
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error controlling cache: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to control cache"
                )
        
        @self.app.post("/api/cache/clear", response_model=CacheStatusResponse)
        @limiter.limit("30/minute")
        async def clear_cache(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
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
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error clearing cache: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to clear cache"
                )
        
        @self.app.get("/api/cache/status", response_model=CacheStatusResponse)
        @limiter.limit("60/minute")
        async def cache_status(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
                # Получаем API-ключ из любого доступного заголовка
                key = self._extract_api_key(api_key, authorization)
                self._validate_api_key_or_raise(key)
                
                cache_status = {
                    "enabled": self.translator.cache_enabled,
                    "entries": len(self.translator.translation_cache) if self.translator.cache_enabled else 0,
                    "message": "Cache status retrieved successfully"
                }
                
                return CacheStatusResponse(**cache_status)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting cache status: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get cache status"
                )
        
        @self.app.post("/api/generate_key", response_model=ApiKeyResponse)
        @limiter.limit("10/minute")
        async def generate_key():
            try:
                api_key = generate_api_key()
                if not save_api_key(api_key, {"created_at": str(datetime.now())}):
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to save API key"
                    )
                
                return ApiKeyResponse(
                    api_key=api_key,
                    message="API key generated successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error generating API key: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate API key"
                )
        
        @self.app.delete("/api/revoke_key")
        @limiter.limit("10/minute")
        async def revoke_key(
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
                # Получаем API-ключ из любого доступного заголовка
                key = self._extract_api_key(api_key, authorization)
                self._validate_api_key_or_raise(key)
                
                success = revoke_api_key(key)
                if not success:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to revoke API key"
                    )
                
                return {"message": "API key revoked successfully"}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error revoking API key: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Failed to revoke API key"
                )
        
        # OpenAI API compatibility endpoint
        @self.app.post("/v1/chat/completions")
        @limiter.limit("30/minute")
        async def chat_completions(
            request: ChatCompletionRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            try:
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
                    raise HTTPException(
                        status_code=400,
                        detail="No user message found to translate"
                    )
                
                # Проверяем, что модель загружена
                if not self.translator.model.model or not self.translator.model.tokenizer:
                    raise HTTPException(
                        status_code=503,
                        detail="Translation model is not loaded"
                    )
                
                # Проверяем длину текста
                if len(text_to_translate) > 5000:
                    raise HTTPException(
                        status_code=400,
                        detail="Text length exceeds maximum limit of 5000 characters"
                    )
                
                # Translate the text
                logger.info(f"Переводим текст: '{text_to_translate}'")
                translated_text = self.translator.translate(text_to_translate, apply_formatting=True)
                logger.info(f"Результат перевода: '{translated_text}'")
                
                if translated_text.startswith("Error:"):
                    raise HTTPException(
                        status_code=500,
                        detail=translated_text
                    )
                
                # Print debug info to console
                logger.info(f"\n=== ПЕРЕВОД ===")
                logger.info(f"Исходный текст: {text_to_translate}")
                logger.info(f"Переведенный текст: {translated_text}")
                logger.info(f"===============\n")
                
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
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in chat completions: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error during chat completion"
                )
        
        @self.app.post("/api/translate/v1/chat/completions")
        @limiter.limit("30/minute")
        async def alternative_chat_completions(request: Request):
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
                        try:
                            async with httpx.AsyncClient() as client:
                                async with client.stream("POST", target_url, content=body, headers=headers) as response:
                                    async for chunk in response.aiter_bytes():
                                        yield chunk
                        except Exception as e:
                            logger.error(f"Error in stream generator: {e}", exc_info=True)
                            yield f"data: {json.dumps({'error': str(e)})}\n\n"
                            yield "data: [DONE]\n\n"
                
                    # Возвращаем потоковый ответ с тем же content-type
                    return StreamingResponse(
                        stream_generator(),
                        media_type="text/event-stream"
                    )
                else:
                    # Для обычных запросов используем стандартный подход
                    try:
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
                        logger.error(f"Error forwarding request: {e}", exc_info=True)
                        raise HTTPException(
                            status_code=500,
                            detail=f"Error forwarding request: {str(e)}"
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error in alternative chat completions: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error during request forwarding"
                )
    
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
            try:
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
                    try:
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
                    except Exception as e:
                        logger.error(f"Error generating token {i}: {e}", exc_info=True)
                        error_event = {
                            "id": f"{id_base}-error",
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "content": f"\nError: {str(e)}"
                                    },
                                    "finish_reason": "error"
                                }
                            ]
                        }
                        yield f"data: {json.dumps(error_event)}\n\n"
                        break
                
                # Финальный маркер для SSE
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in stream generation: {e}", exc_info=True)
                error_event = {
                    "id": f"chatcmpl-error-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": f"\nError: {str(e)}"
                            },
                            "finish_reason": "error"
                        }
                    ]
                }
                yield f"data: {json.dumps(error_event)}\n\n"
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
            if not api_key.strip():
                raise HTTPException(
                    status_code=401,
                    detail="Empty API key provided",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return api_key.strip()
            
        if authorization:
            # Обработка формата Bearer {token}
            if authorization.startswith("Bearer "):
                token = authorization[7:].strip()
                if not token:
                    raise HTTPException(
                        status_code=401,
                        detail="Empty Bearer token provided",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                return token
                
            # Обработка наличия только токена
            if not authorization.strip():
                raise HTTPException(
                    status_code=401,
                    detail="Empty authorization token provided",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return authorization.strip()
            
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
            
        try:
            # Load API keys before validation
            api_keys = load_api_keys()
            
            # Проверяем формат ключа
            if not (api_key.startswith("nn_tr_") or api_key.startswith("sk-") or api_key.startswith("nn_translator_")):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key format",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Проверяем длину ключа
            if len(api_key) < 10:
                raise HTTPException(
                    status_code=401,
                    detail="API key is too short",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            is_valid = validate_api_key(api_key, api_keys)
            if not is_valid:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Internal server error during API key validation"
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
        
        logger.info(f"API server started on http://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the API server"""
        if self.server_thread and self.running:
            # There's no clean way to stop a uvicorn server from another thread
            # The process will be terminated when the main thread exits
            self.running = False
            logger.info("API server is shutting down...") 