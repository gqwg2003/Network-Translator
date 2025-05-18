"""
Text formatting utilities for Neural Network Translator
"""
import re
import logging
from typing import Optional, Dict, List, Callable
from functools import lru_cache

# Константы
MIN_TEXT_LENGTH = 1
MAX_TEXT_LENGTH = 1000000
MAX_PATTERN_LENGTH = 1000
DEFAULT_OPERATIONS = {
    "smart_quotes": True,
    "russian_punctuation": True,
    "normalize_whitespace": True,
    "fix_common_issues": True
}

# Регулярные выражения
PUNCTUATION_PATTERNS = {
    "russian": {
        "em_dash": r'\s+—\s+',
        "space_after": r'([,;])(\S)',
        "space_before": r'\s+([,.!?:;])',
        "dash": r'\s+-\s+'
    },
    "english": {
        "space_after": r'([,.!?:;])([^\s0-9])',
        "multiple_spaces": r'\s+'
    }
}

class TextFormatter:
    """
    Utility class for text formatting and conversion operations
    """
    def __init__(self):
        """Initialize the text formatter"""
        self.logger = logging.getLogger("nn_translator.text_formatter")
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regular expressions for better performance"""
        try:
            self.compiled_patterns = {}
            for style, patterns in PUNCTUATION_PATTERNS.items():
                self.compiled_patterns[style] = {}
                for name, pattern in patterns.items():
                    if len(pattern) > MAX_PATTERN_LENGTH:
                        raise ValueError(f"Pattern {name} is too long (max {MAX_PATTERN_LENGTH} chars)")
                    try:
                        self.compiled_patterns[style][name] = re.compile(pattern)
                    except re.error as e:
                        self.logger.error(f"Error compiling pattern {name}: {e}")
                        raise ValueError(f"Invalid pattern {name}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error compiling patterns: {e}", exc_info=True)
            raise RuntimeError(f"Failed to compile patterns: {str(e)}")
    
    def _validate_text(self, text: str) -> None:
        """
        Validate input text
        
        Args:
            text: Text to validate
            
        Raises:
            ValueError: If text is invalid
        """
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
            
        if not text.strip():
            raise ValueError("Text cannot be empty or contain only whitespace")
            
        if len(text) < MIN_TEXT_LENGTH:
            raise ValueError(f"Text is too short (minimum {MIN_TEXT_LENGTH} characters)")
            
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text is too long (maximum {MAX_TEXT_LENGTH} characters)")
    
    def _validate_operations(self, operations: Dict[str, bool]) -> None:
        """
        Validate formatting operations
        
        Args:
            operations: Dictionary of operations to validate
            
        Raises:
            ValueError: If operations are invalid
        """
        if not isinstance(operations, dict):
            raise ValueError("Operations must be a dictionary")
            
        for key, value in operations.items():
            if key not in DEFAULT_OPERATIONS:
                raise ValueError(f"Unknown operation: {key}")
            if not isinstance(value, bool):
                raise ValueError(f"Operation value must be boolean: {key}")
    
    def _validate_style(self, style: str) -> None:
        """
        Validate style parameter
        
        Args:
            style: Style to validate
            
        Raises:
            ValueError: If style is invalid
        """
        if not isinstance(style, str):
            raise ValueError("Style must be a string")
            
        if style.lower() not in PUNCTUATION_PATTERNS:
            raise ValueError(f"Style must be one of: {', '.join(PUNCTUATION_PATTERNS.keys())}")
    
    def _validate_result(self, result: str) -> str:
        """
        Validate formatting result
        
        Args:
            result: Result to validate
            
        Returns:
            Validated result
            
        Raises:
            ValueError: If result is invalid
        """
        if not isinstance(result, str):
            raise ValueError("Result must be a string")
            
        if not result.strip():
            raise ValueError("Result cannot be empty or contain only whitespace")
            
        return result
    
    @lru_cache(maxsize=1000)
    def convert_smart_quotes(self, text: str, to_smart: bool = True) -> str:
        """
        Convert between straight and smart quotes (curly)
        
        Args:
            text: The text to process
            to_smart: If True, convert straight quotes to smart quotes. 
                     If False, convert smart quotes to straight quotes.
        
        Returns:
            Processed text
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If conversion fails
        """
        try:
            self._validate_text(text)
            
            if to_smart:
                # Простой метод - заменяем все двойные кавычки на «»
                # Сначала заменяем пары кавычек
                result = ""
                in_quote = False
                for char in text:
                    if char == '"':
                        if in_quote:
                            result += '»'
                            in_quote = False
                        else:
                            result += '«'
                            in_quote = True
                    else:
                        result += char
                
                # Обработка одиночных кавычек (апострофов)
                text = result
                result = ""
                in_quote = False
                for char in text:
                    if char == "'":
                        if in_quote:
                            result += '''
                            in_quote = False
                        else:
                            result += '''
                            in_quote = True
                    else:
                        result += char
                
                return self._validate_result(result)
            else:
                # Convert smart quotes to straight quotes
                result = text.replace('«', '"').replace('»', '"')
                result = result.replace('"', '"').replace('"', '"')
                result = result.replace(''', "'").replace(''', "'")
                return self._validate_result(result)
                
        except ValueError as e:
            self.logger.error(f"Validation error in convert_smart_quotes: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in convert_smart_quotes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to convert quotes: {str(e)}")
    
    @lru_cache(maxsize=1000)
    def convert_punctuation(self, text: str, style: str = "russian") -> str:
        """
        Convert punctuation according to the specified style
        
        Args:
            text: The text to process
            style: The style to convert to ("russian" or "english")
        
        Returns:
            Processed text
            
        Raises:
            ValueError: If text or style is invalid
            RuntimeError: If conversion fails
        """
        try:
            self._validate_text(text)
            self._validate_style(style)
            
            # Get patterns for the specified style
            patterns = self.compiled_patterns.get(style.lower(), {})
            
            # Apply each pattern
            result = text
            for pattern_name, pattern in patterns.items():
                try:
                    if pattern_name == "space_after":
                        result = pattern.sub(r'\1 \2', result)
                    elif pattern_name == "space_before":
                        result = pattern.sub(r' \1', result)
                    else:
                        result = pattern.sub(' ', result)
                except re.error as e:
                    self.logger.error(f"Regex error in pattern {pattern_name}: {e}")
                    continue
                    
            return self._validate_result(result)
        except ValueError as e:
            self.logger.error(f"Validation error in convert_punctuation: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in convert_punctuation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to convert punctuation: {str(e)}")
    
    @lru_cache(maxsize=1000)
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text
        
        Args:
            text: The text to process
        
        Returns:
            Processed text
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If normalization fails
        """
        try:
            self._validate_text(text)
            
            # Replace multiple spaces with a single space
            result = re.sub(r'\s+', ' ', text)
            
            # Remove leading/trailing whitespace
            result = result.strip()
            
            return self._validate_result(result)
        except ValueError as e:
            self.logger.error(f"Validation error in normalize_whitespace: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in normalize_whitespace: {e}", exc_info=True)
            raise RuntimeError(f"Failed to normalize whitespace: {str(e)}")
    
    @lru_cache(maxsize=1000)
    def fix_common_issues(self, text: str) -> str:
        """
        Fix common text issues
        
        Args:
            text: The text to process
        
        Returns:
            Processed text
            
        Raises:
            ValueError: If text is invalid
            RuntimeError: If fixing fails
        """
        try:
            self._validate_text(text)
            
            # Fix common issues
            result = text
            
            # Fix multiple punctuation
            result = re.sub(r'([.,!?])\1+', r'\1', result)
            
            # Fix spaces around punctuation
            result = re.sub(r'\s+([.,!?])', r'\1', result)
            
            # Fix multiple spaces
            result = re.sub(r'\s+', ' ', result)
            
            # Fix leading/trailing whitespace
            result = result.strip()
            
            return self._validate_result(result)
        except ValueError as e:
            self.logger.error(f"Validation error in fix_common_issues: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in fix_common_issues: {e}", exc_info=True)
            raise RuntimeError(f"Failed to fix common issues: {str(e)}")
    
    @lru_cache(maxsize=1000)
    def process_text(self, text: str, operations: Dict[str, bool] = None) -> str:
        """
        Process text with specified operations
        
        Args:
            text: The text to process
            operations: Dictionary of operations to apply
            
        Returns:
            Processed text
            
        Raises:
            ValueError: If text or operations are invalid
            RuntimeError: If processing fails
        """
        try:
            self._validate_text(text)
            
            # Use default operations if none provided
            if operations is None:
                operations = DEFAULT_OPERATIONS
            else:
                self._validate_operations(operations)
            
            # Apply each operation
            result = text
            
            if operations.get("smart_quotes", False):
                result = self.convert_smart_quotes(result)
                
            if operations.get("russian_punctuation", False):
                result = self.convert_punctuation(result, "russian")
                
            if operations.get("normalize_whitespace", False):
                result = self.normalize_whitespace(result)
                
            if operations.get("fix_common_issues", False):
                result = self.fix_common_issues(result)
                
            return self._validate_result(result)
        except ValueError as e:
            self.logger.error(f"Validation error in process_text: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in process_text: {e}", exc_info=True)
            raise RuntimeError(f"Failed to process text: {str(e)}") 