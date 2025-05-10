from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import uvicorn
import threading
from datetime import datetime
import logging
import json
import asyncio

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

class BatchTranslationRequest(BaseModel):
    texts: List[str]

class TranslationResponse(BaseModel):
    translated_text: str

class BatchTranslationResponse(BaseModel):
    translated_texts: List[str]

class ApiKeyResponse(BaseModel):
    api_key: str
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
        
        @self.app.post("/api/translate", response_model=TranslationResponse)
        async def translate(
            request: TranslationRequest,
            api_key: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None)
        ):
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            translated = self.translator.translate(request.text)
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
            
            translated = self.translator.translate_batch(request.texts)
            return BatchTranslationResponse(translated_texts=translated)
        
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
            translated_text = self.translator.translate(text_to_translate)
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
            
            # Логируем ответ
            logger.info(f"Отправляем ответ: {response}")
            
            return response
        
        # Alternative path for clients that combine base paths incorrectly
        @self.app.post("/api/translate/v1/chat/completions")
        async def alternative_chat_completions(request: Request):
            # Capture the raw request and forward it to the proper endpoint
            body = await request.json()
            authorization = request.headers.get("authorization")
            api_key = request.headers.get("api-key")
            
            # Логируем входящий запрос
            logger.info(f"Получен запрос к альтернативному пути: {body}")
            
            # Create a proper request for our standard endpoint
            proper_request = ChatCompletionRequest(**body)
            
            # Получаем API-ключ из любого доступного заголовка
            key = self._extract_api_key(api_key, authorization)
            self._validate_api_key_or_raise(key)
            
            # Extract text to translate from the last user message
            text_to_translate = ""
            for message in reversed(proper_request.messages):
                if message.role == "user":
                    text_to_translate = message.content
                    break
            
            if not text_to_translate:
                logger.error("Сообщение пользователя не найдено")
                raise HTTPException(status_code=400, detail="No user message found to translate")
            
            # Translate the text
            logger.info(f"Переводим текст: '{text_to_translate}'")
            translated_text = self.translator.translate(text_to_translate)
            logger.info(f"Результат перевода: '{translated_text}'")
            
            # Print debug info to console
            print(f"\n=== ПЕРЕВОД (альтернативный путь) ===")
            print(f"Исходный текст: {text_to_translate}")
            print(f"Переведенный текст: {translated_text}")
            print(f"===============\n")
            
            # Check if the client requested streaming
            if proper_request.stream:
                logger.info("Клиент запросил потоковый ответ, отправляем SSE")
                return self._stream_response(proper_request.model, translated_text)
            
            # Create response in OpenAI format (non-streaming)
            response = ChatCompletionResponse(
                model=proper_request.model,
                choices=[
                    ChatCompletionChoice(
                        message=ChatCompletionChoiceMessage(
                            content=translated_text
                        )
                    )
                ]
            )
            
            # Логируем ответ
            logger.info(f"Отправляем ответ: {response}")
            
            return response.dict()
    
    def _stream_response(self, model: str, translated_text: str):
        """
        Create a streaming response compatible with OpenAI SSE format
        
        Args:
            model: The model name
            translated_text: The translated text to stream
            
        Returns:
            StreamingResponse: A streaming response compatible with OpenAI API
        """
        async def generate():
            # SSE должно иметь правильный формат: data: {json}\n\n
            
            # Сначала отправляем начало ответа
            start_data = {
                "id": f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "chat.completion.chunk",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(start_data)}\n\n"
            
            # Отправляем содержимое перевода (в реальности можно было бы отправлять по частям)
            content_data = {
                "id": f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "chat.completion.chunk",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": translated_text},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(content_data)}\n\n"
            
            # Завершаем ответ
            finish_data = {
                "id": f"chatcmpl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "object": "chat.completion.chunk",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(finish_data)}\n\n"
            
            # Сигнал завершения потока
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
    
    def _extract_api_key(self, api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
        """
        Extract API key from various header formats
        
        Args:
            api_key: The API key from api-key header
            authorization: The Authorization header
            
        Returns:
            The extracted API key or None
        """
        # Сначала проверяем api-key заголовок
        if api_key:
            return api_key
            
        # Затем проверяем Authorization заголовок формата "Bearer {key}"
        if authorization and authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
            
        return None
    
    def _validate_api_key_or_raise(self, api_key: Optional[str]):
        """
        Validate the API key or raise an HTTP exception
        
        Args:
            api_key: The API key to validate
        
        Raises:
            HTTPException: If the API key is invalid
        """
        if api_key is None:
            raise HTTPException(
                status_code=401,
                detail="API key is required. Provide it in 'api-key' header or 'Authorization: Bearer {key}' header."
            )
        
        api_keys = load_api_keys()
        if not validate_api_key(api_key, api_keys):
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
    
    def start(self):
        """Start the API server in a separate thread"""
        if self.running:
            return
        
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port)
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.running = True
        
        print(f"API server started on http://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the API server"""
        # Note: uvicorn doesn't provide a clean way to stop the server
        # in a separate thread, so this is a placeholder
        self.running = False
        print("API server stopped") 