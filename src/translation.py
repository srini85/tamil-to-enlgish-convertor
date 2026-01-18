"""Tamil text translation service using Google Cloud Translate API."""

import time
from typing import List

try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False


class TranslationError(Exception):
    """Custom exception for translation-related errors."""
    pass


class TamilTranslator:
    """High-accuracy Tamil to English translator using Google Cloud API."""
    
    def __init__(self):
        if not GOOGLE_TRANSLATE_AVAILABLE:
            raise ImportError(
                "Google Cloud Translate not available. "
                "Install with: pip install google-cloud-translate"
            )
        
        self.client = translate.Client()
        self._test_connection()
    
    def _test_connection(self):
        """Test API connection with a simple translation."""
        try:
            self.client.translate("test", target_language='en', source_language='ta')
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Google Translate API: {e}")
    
    def translate_text(self, text: str, chunk_size: int = 5000) -> str:
        """
        Translate Tamil text to English with intelligent chunking.
        
        Args:
            text: Tamil text to translate
            chunk_size: Maximum characters per API request
            
        Returns:
            Translated English text
            
        Raises:
            TranslationError: If translation fails completely
        """
        if not text.strip():
            return ""
        
        chunks = self._split_text(text, chunk_size)
        translated_chunks = []
        failed_chunks = 0
        
        for i, chunk in enumerate(chunks, 1):
            if chunk.strip():
                try:
                    result = self.client.translate(
                        chunk, 
                        target_language='en', 
                        source_language='ta'
                    )
                    translated_chunks.append(result['translatedText'])
                    
                    if len(chunks) > 1:
                        print(f"Translated chunk {i}/{len(chunks)}", end='\r')
                        time.sleep(0.1)  # Rate limiting
                        
                except Exception as e:
                    print(f"\nWarning: Translation failed for chunk {i}: {e}")
                    translated_chunks.append(f"[Translation failed: {chunk[:100]}...]")
                    failed_chunks += 1
        
        if len(chunks) > 1:
            print()  # New line after progress updates
            
        if failed_chunks == len(chunks):
            raise TranslationError("All translation chunks failed")
            
        return '\n'.join(translated_chunks)
    
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks while preserving line boundaries."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        for line in text.split('\n'):
            if len(current_chunk + line + '\n') > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


def is_translation_available() -> bool:
    """Check if translation dependencies are available."""
    return GOOGLE_TRANSLATE_AVAILABLE