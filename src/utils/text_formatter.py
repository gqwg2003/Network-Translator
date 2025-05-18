"""
Text formatting utilities for Neural Network Translator
"""
import re
import logging
from typing import List, Dict, Any, Optional, Union, Set
from functools import lru_cache

MIN_TEXT_LENGTH = 1
MAX_TEXT_LENGTH = 10000
MAX_PATTERN_LENGTH = 1000

DEFAULT_OPERATIONS = {
    "smart_quotes",
    "punctuation",
    "whitespace",
    "common_issues"
}

logger = logging.getLogger("nn_translator.text_formatter")

class TextFormatter:
    def __init__(self, style: str = "default"):
        self.style = style
        self._compile_patterns()
        
    def _compile_patterns(self) -> None:
        self.patterns = {
            "smart_quotes": re.compile(r'[""](.*?)[""]'),
            "punctuation": re.compile(r'([.,!?;:])'),
            "whitespace": re.compile(r'\s+'),
            "common_issues": re.compile(r'([a-zA-Z])([.,!?;:])')
        }
        
    def _validate_text(self, text: str) -> None:
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        if not text:
            raise ValueError("Text cannot be empty")
        if len(text) < MIN_TEXT_LENGTH:
            raise ValueError(f"Text length must be at least {MIN_TEXT_LENGTH} character")
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text length must not exceed {MAX_TEXT_LENGTH} characters")
            
    def _validate_operations(self, operations: List[str]) -> None:
        if not operations:
            raise ValueError("Operations list cannot be empty")
        if not all(op in DEFAULT_OPERATIONS for op in operations):
            raise ValueError(f"Invalid operation. Must be one of: {', '.join(DEFAULT_OPERATIONS)}")
            
    def _validate_style(self, style: str) -> None:
        if not isinstance(style, str):
            raise ValueError("Style must be a string")
        if not style:
            raise ValueError("Style cannot be empty")
            
    def _validate_result(self, result: str) -> None:
        if not result:
            raise ValueError("Formatting result cannot be empty")
        if len(result) > MAX_TEXT_LENGTH:
            raise ValueError(f"Formatted text exceeds maximum length of {MAX_TEXT_LENGTH} characters")
            
    @lru_cache(maxsize=1000)
    def convert_smart_quotes(self, text: str) -> str:
        try:
            self._validate_text(text)
            result = self.patterns["smart_quotes"].sub(r'"\1"', text)
            self._validate_result(result)
            return result
        except Exception as e:
            logger.error(f"Error converting smart quotes: {e}")
            return text
            
    @lru_cache(maxsize=1000)
    def convert_punctuation(self, text: str) -> str:
        try:
            self._validate_text(text)
            result = self.patterns["punctuation"].sub(r'\1 ', text)
            self._validate_result(result)
            return result
        except Exception as e:
            logger.error(f"Error converting punctuation: {e}")
            return text
            
    @lru_cache(maxsize=1000)
    def normalize_whitespace(self, text: str) -> str:
        try:
            self._validate_text(text)
            result = self.patterns["whitespace"].sub(' ', text).strip()
            self._validate_result(result)
            return result
        except Exception as e:
            logger.error(f"Error normalizing whitespace: {e}")
            return text
            
    @lru_cache(maxsize=1000)
    def fix_common_issues(self, text: str) -> str:
        try:
            self._validate_text(text)
            result = self.patterns["common_issues"].sub(r'\1 \2', text)
            self._validate_result(result)
            return result
        except Exception as e:
            logger.error(f"Error fixing common issues: {e}")
            return text
            
    def format_text(self, text: str, operations: Optional[List[str]] = None) -> str:
        try:
            self._validate_text(text)
            
            if operations is None:
                operations = list(DEFAULT_OPERATIONS)
            else:
                self._validate_operations(operations)
                
            result = text
            for operation in operations:
                if operation == "smart_quotes":
                    result = self.convert_smart_quotes(result)
                elif operation == "punctuation":
                    result = self.convert_punctuation(result)
                elif operation == "whitespace":
                    result = self.normalize_whitespace(result)
                elif operation == "common_issues":
                    result = self.fix_common_issues(result)
                    
            self._validate_result(result)
            return result
        except Exception as e:
            logger.error(f"Error formatting text: {e}")
            return text 