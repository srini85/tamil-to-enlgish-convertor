"""Local Tamil text translation service using free, offline alternatives."""

import time
from typing import List, Optional
from abc import ABC, abstractmethod

# Try importing various local translation libraries
try:
    from transformers import pipeline, MarianMTModel, MarianTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import argostranslate.package
    import argostranslate.translate
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class LocalTranslationError(Exception):
    """Custom exception for local translation-related errors."""
    pass


class BaseTranslator(ABC):
    """Base class for translation services."""
    
    @abstractmethod
    def translate_text(self, text: str, chunk_size: int = 5000) -> str:
        """Translate text from Tamil to English."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the translator is available and ready."""
        pass
    
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


class HuggingFaceTranslator(BaseTranslator):
    """Translation using HuggingFace Transformers (MarianMT models)."""
    
    def __init__(self):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library not available")
        
        self.model_name = "Helsinki-NLP/opus-mt-mul-en"  # Multilingual to English
        self.pipeline = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the translation model."""
        try:
            print("Loading HuggingFace translation model (first time may take a while)...")
            self.pipeline = pipeline("translation", model=self.model_name, device=-1)  # CPU
            print("✓ HuggingFace model loaded successfully")
        except Exception as e:
            print(f"Failed to load HuggingFace model: {e}")
            raise LocalTranslationError(f"Failed to initialize HuggingFace translator: {e}")
    
    def is_available(self) -> bool:
        return TRANSFORMERS_AVAILABLE and self.pipeline is not None
    
    def translate_text(self, text: str, chunk_size: int = 1000) -> str:
        """Translate Tamil text to English using HuggingFace."""
        if not text.strip():
            return ""
        
        if not self.is_available():
            raise LocalTranslationError("HuggingFace translator not available")
        
        chunks = self._split_text(text, chunk_size)
        translated_chunks = []
        failed_chunks = 0
        
        for i, chunk in enumerate(chunks, 1):
            if chunk.strip():
                try:
                    # Add language hint for better Tamil recognition
                    result = self.pipeline(f">>tam<< {chunk}", max_length=500)
                    translated_text = result[0]['translation_text']
                    translated_chunks.append(translated_text)
                    
                    if len(chunks) > 1:
                        print(f"Translated chunk {i}/{len(chunks)} (HuggingFace)", end='\r')
                        
                except Exception as e:
                    print(f"\nWarning: HuggingFace translation failed for chunk {i}: {e}")
                    translated_chunks.append(f"[Translation failed: {chunk[:100]}...]")
                    failed_chunks += 1
        
        if len(chunks) > 1:
            print()
            
        if failed_chunks == len(chunks):
            raise LocalTranslationError("All HuggingFace translation chunks failed")
            
        return '\n'.join(translated_chunks)


class ArgosTranslator(BaseTranslator):
    """Translation using Argos Translate (offline)."""
    
    def __init__(self):
        if not ARGOS_AVAILABLE:
            raise ImportError("argostranslate library not available")
        
        self._setup_language_packages()
    
    def _setup_language_packages(self):
        """Download and install required language packages."""
        try:
            # Update package index
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # Find Tamil to English package
            ta_en_package = None
            for package in available_packages:
                if package.from_code == 'ta' and package.to_code == 'en':
                    ta_en_package = package
                    break
            
            if ta_en_package and not ta_en_package.is_installed():
                print("Installing Tamil-English language package for Argos Translate...")
                argostranslate.package.install_from_path(ta_en_package.download())
                print("✓ Tamil-English package installed")
        except Exception as e:
            print(f"Warning: Could not setup Argos language packages: {e}")
    
    def is_available(self) -> bool:
        if not ARGOS_AVAILABLE:
            return False
        try:
            # Check if Tamil to English translation is available
            installed_languages = argostranslate.translate.get_installed_languages()
            tamil = next((lang for lang in installed_languages if lang.code == 'ta'), None)
            if tamil:
                return any(lang.code == 'en' for lang in tamil.targets)
            return False
        except:
            return False
    
    def translate_text(self, text: str, chunk_size: int = 2000) -> str:
        """Translate Tamil text to English using Argos."""
        if not text.strip():
            return ""
        
        if not self.is_available():
            raise LocalTranslationError("Argos translator not available")
        
        chunks = self._split_text(text, chunk_size)
        translated_chunks = []
        failed_chunks = 0
        
        for i, chunk in enumerate(chunks, 1):
            if chunk.strip():
                try:
                    translated_text = argostranslate.translate.translate(chunk, 'ta', 'en')
                    translated_chunks.append(translated_text)
                    
                    if len(chunks) > 1:
                        print(f"Translated chunk {i}/{len(chunks)} (Argos)", end='\r')
                        
                except Exception as e:
                    print(f"\nWarning: Argos translation failed for chunk {i}: {e}")
                    translated_chunks.append(f"[Translation failed: {chunk[:100]}...]")
                    failed_chunks += 1
        
        if len(chunks) > 1:
            print()
            
        if failed_chunks == len(chunks):
            raise LocalTranslationError("All Argos translation chunks failed")
            
        return '\n'.join(translated_chunks)


class LibreTranslateClient(BaseTranslator):
    """Translation using LibreTranslate API (can be run locally)."""
    
    def __init__(self, api_url: str = "https://translate.argosopentech.com"):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library not available")
        
        self.api_url = api_url.rstrip('/')
        self.api_key = None  # LibreTranslate is free
    
    def is_available(self) -> bool:
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.api_url}/languages", timeout=5)
            if response.status_code == 200:
                languages = response.json()
                lang_codes = [lang['code'] for lang in languages]
                return 'ta' in lang_codes and 'en' in lang_codes
            return False
        except:
            return False
    
    def translate_text(self, text: str, chunk_size: int = 3000) -> str:
        """Translate Tamil text to English using LibreTranslate."""
        if not text.strip():
            return ""
        
        if not self.is_available():
            raise LocalTranslationError("LibreTranslate API not available")
        
        chunks = self._split_text(text, chunk_size)
        translated_chunks = []
        failed_chunks = 0
        
        for i, chunk in enumerate(chunks, 1):
            if chunk.strip():
                try:
                    data = {
                        'q': chunk,
                        'source': 'ta',
                        'target': 'en',
                        'format': 'text'
                    }
                    
                    if self.api_key:
                        data['api_key'] = self.api_key
                    
                    response = requests.post(f"{self.api_url}/translate", data=data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        translated_chunks.append(result['translatedText'])
                    else:
                        raise Exception(f"API error: {response.status_code}")
                    
                    if len(chunks) > 1:
                        print(f"Translated chunk {i}/{len(chunks)} (LibreTranslate)", end='\r')
                        time.sleep(0.5)  # Rate limiting
                        
                except Exception as e:
                    print(f"\nWarning: LibreTranslate failed for chunk {i}: {e}")
                    translated_chunks.append(f"[Translation failed: {chunk[:100]}...]")
                    failed_chunks += 1
        
        if len(chunks) > 1:
            print()
            
        if failed_chunks == len(chunks):
            raise LocalTranslationError("All LibreTranslate chunks failed")
            
        return '\n'.join(translated_chunks)


class LocalTranslator:
    """Main local translator that tries multiple translation services."""
    
    def __init__(self, preferred_service: Optional[str] = None):
        self.services = {}
        self.preferred_service = preferred_service
        self.active_service = None
        
        # Initialize available services
        self._initialize_services()
        
        if not self.services:
            raise LocalTranslationError("No local translation services available")
    
    def _initialize_services(self):
        """Initialize all available translation services."""
        
        # Try HuggingFace Transformers
        try:
            hf_translator = HuggingFaceTranslator()
            if hf_translator.is_available():
                self.services['huggingface'] = hf_translator
                print("✓ HuggingFace translator initialized")
        except Exception as e:
            print(f"✗ HuggingFace translator unavailable: {e}")
        
        # Try Argos Translate
        try:
            argos_translator = ArgosTranslator()
            if argos_translator.is_available():
                self.services['argos'] = argos_translator
                print("✓ Argos translator initialized")
        except Exception as e:
            print(f"✗ Argos translator unavailable: {e}")
        
        # Try LibreTranslate
        try:
            libre_translator = LibreTranslateClient()
            if libre_translator.is_available():
                self.services['libretranslate'] = libre_translator
                print("✓ LibreTranslate API accessible")
        except Exception as e:
            print(f"✗ LibreTranslate unavailable: {e}")
        
        # Select active service
        if self.preferred_service and self.preferred_service in self.services:
            self.active_service = self.services[self.preferred_service]
        elif self.services:
            # Priority order: Argos (fully offline) > HuggingFace > LibreTranslate (online)
            for service_name in ['argos', 'huggingface', 'libretranslate']:
                if service_name in self.services:
                    self.active_service = self.services[service_name]
                    print(f"Using {service_name} translator")
                    break
    
    def translate_text(self, text: str) -> str:
        """Translate text using the active service."""
        if not self.active_service:
            raise LocalTranslationError("No translation service available")
        
        return self.active_service.translate_text(text)
    
    def get_available_services(self) -> List[str]:
        """Get list of available translation services."""
        return list(self.services.keys())
    
    def switch_service(self, service_name: str) -> bool:
        """Switch to a different translation service."""
        if service_name in self.services:
            self.active_service = self.services[service_name]
            print(f"Switched to {service_name} translator")
            return True
        return False


def is_local_translation_available() -> bool:
    """Check if any local translation service is available."""
    try:
        translator = LocalTranslator()
        return len(translator.get_available_services()) > 0
    except:
        return False


# Backwards compatibility
def is_translation_available() -> bool:
    """Check if translation (local or cloud) is available."""
    return is_local_translation_available()