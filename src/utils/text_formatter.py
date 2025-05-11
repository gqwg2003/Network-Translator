"""
Text formatting utilities for Neural Network Translator
"""
import re
from typing import Optional, Dict, List, Callable


class TextFormatter:
    """
    Utility class for text formatting and conversion operations
    """
    
    @staticmethod
    def convert_smart_quotes(text: str, to_smart: bool = True) -> str:
        """
        Convert between straight and smart quotes (curly)
        
        Args:
            text: The text to process
            to_smart: If True, convert straight quotes to smart quotes. 
                     If False, convert smart quotes to straight quotes.
        
        Returns:
            Processed text
        """
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
            
            return result
        else:
            # Convert smart quotes to straight quotes
            text = text.replace('«', '"').replace('»', '"')
            text = text.replace('"', '"').replace('"', '"')
            text = text.replace(''', "'").replace(''', "'")
            return text
    
    @staticmethod
    def convert_punctuation(text: str, style: str = "russian") -> str:
        """
        Convert punctuation according to the specified style
        
        Args:
            text: The text to process
            style: The style to convert to ("russian" or "english")
        
        Returns:
            Processed text
        """
        if style.lower() == "russian":
            # Convert em-dash surrounded by spaces
            text = re.sub(r'\s+—\s+', ' — ', text)
            # Ensure space after punctuation
            text = re.sub(r'([,;])(\S)', r'\1 \2', text)
            # Fix space before punctuation (shouldn't be there in Russian)
            text = re.sub(r'\s+([,.!?:;])', r'\1', text)
            # Adjust dash formatting
            text = re.sub(r'\s+-\s+', r' — ', text)
        else:  # English
            # Ensure space after punctuation
            text = re.sub(r'([,.!?:;])([^\s0-9])', r'\1 \2', text)
            # Fix multiple spaces
            text = re.sub(r'\s+', ' ', text)
        
        return text
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize whitespace in text (remove extra spaces, normalize line endings)
        
        Args:
            text: The text to process
        
        Returns:
            Processed text
        """
        # Replace multiple spaces with a single space
        text = re.sub(r' +', ' ', text)
        # Normalize line endings to LF
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Remove spaces at the beginning of lines
        text = re.sub(r'\n ', '\n', text)
        # Remove trailing whitespace
        text = re.sub(r' +$', '', text, flags=re.MULTILINE)
        
        return text
    
    @staticmethod
    def fix_common_issues(text: str) -> str:
        """
        Fix common issues in translated Russian text
        
        Args:
            text: The text to process
        
        Returns:
            Processed text
        """
        # Fix spaces between words and parentheses/brackets
        text = re.sub(r'(\S)\s+\)', r'\1)', text)
        text = re.sub(r'\(\s+(\S)', r'(\1', text)
        
        # Fix incorrectly placed quotation marks
        text = re.sub(r'«\s+(\S)', r'«\1', text)
        text = re.sub(r'(\S)\s+»', r'\1»', text)
        
        # Fix double punctuation
        text = re.sub(r'([.!?,:;])\s*([.!?,:;])', r'\1', text)
        
        # Normalize ellipsis
        text = re.sub(r'\.{2,}', '…', text)
        
        # Fix space before punctuation
        text = re.sub(r'\s+([.,!?:;])', r'\1', text)
        
        return text
    
    @staticmethod
    def process_text(text: str, operations: Dict[str, bool] = None) -> str:
        """
        Process text with multiple formatting operations at once
        
        Args:
            text: The text to process
            operations: Dictionary of operations to apply, e.g. 
                       {"smart_quotes": True, "normalize_whitespace": True}
        
        Returns:
            Processed text
        """
        if operations is None:
            operations = {
                "smart_quotes": True,
                "russian_punctuation": True,
                "normalize_whitespace": True,
                "fix_common_issues": True
            }
        
        if operations.get("normalize_whitespace", False):
            text = TextFormatter.normalize_whitespace(text)
            
        if operations.get("smart_quotes", False):
            text = TextFormatter.convert_smart_quotes(text, to_smart=True)
            
        if operations.get("russian_punctuation", False):
            text = TextFormatter.convert_punctuation(text, style="russian")
            
        if operations.get("fix_common_issues", False):
            text = TextFormatter.fix_common_issues(text)
            
        return text 