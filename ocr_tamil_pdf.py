
"""
Tamil PDF OCR and Translation
Converts Tamil PDF to Unicode text and optionally translates to English
"""

import sys
import os
import time
from typing import Optional, List, Tuple
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

class TamilTranslator:
    def __init__(self):
        if not GOOGLE_TRANSLATE_AVAILABLE:
            raise ImportError("Google Cloud Translate not available. Install with: pip install google-cloud-translate")
        
        self.client = translate.Client()
        self._test_connection()
    
    def _test_connection(self):
        try:
            self.client.translate("test", target_language='en', source_language='ta')
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Google Translate API: {e}")
    
    def translate_text(self, text: str, chunk_size: int = 5000) -> str:
        if not text.strip():
            return ""
        
        chunks = self._split_text(text, chunk_size)
        translated_chunks = []
        
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
        
        if len(chunks) > 1:
            print()  # New line after progress updates
            
        return '\n'.join(translated_chunks)
    
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
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


def ocr_pdf_to_unicode_text(
    pdf_path: str, 
    output_txt_path: Optional[str] = None, 
    start_page: Optional[int] = None, 
    end_page: Optional[int] = None,
    translate_to_english: bool = False
) -> Optional[str]:
    """
    OCR a Tamil PDF to Unicode text and optionally translate to English
    
    Args:
        pdf_path: Path to input PDF file
        output_txt_path: Path to output text file (optional)
        start_page: Start page number (1-indexed, optional)
        end_page: End page number (1-indexed, optional)
        translate_to_english: Whether to translate Tamil text to English
    """
    
    base_name = os.path.splitext(pdf_path)[0]
    
    if output_txt_path is None:
        suffix = "_english" if translate_to_english else "_tamil_unicode"
        output_txt_path = f"{base_name}{suffix}.txt"
    
    print(f"OCR Processing: {pdf_path}")
    print(f"Output: {output_txt_path}")
    print(f"Translation: {'Enabled (Tamil → English)' if translate_to_english else 'Disabled'}")
    
    translator = None
    if translate_to_english:
        try:
            translator = TamilTranslator()
            print("✓ Google Translate API connected")
        except Exception as e:
            print(f"✗ Translation setup failed: {e}")
            return None
    
    custom_config = r'--oem 3 --psm 6'
    all_text_pages = []
    
    try:
        print("\nConverting PDF to images...")
        images, page_offset = _convert_pdf_to_images(pdf_path, start_page, end_page)
        
        print(f"Total pages to process: {len(images)}")
        
        for i, image in enumerate(images, 1):
            page_num = i + page_offset
            print(f"OCR processing page {page_num}...", end='\r')
            
            text = pytesseract.image_to_string(
                image, 
                lang='tam',
                config=custom_config
            )
            
            if text.strip():
                all_text_pages.append((page_num, text.strip()))
        
        print(f"\nOCR processing complete! Extracted text from {len(all_text_pages)} pages")
        
        final_content = _process_extracted_text(all_text_pages, translator, translate_to_english)
        
        _save_output_file(output_txt_path, final_content)
        
        _display_summary(output_txt_path, final_content, translate_to_english, page_offset)
        
        return output_txt_path
        
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        return None


def _convert_pdf_to_images(pdf_path: str, start_page: Optional[int], end_page: Optional[int]) -> Tuple[List, int]:
    if start_page and end_page:
        print(f"Processing pages {start_page} to {end_page}")
        images = convert_from_path(
            pdf_path, 
            first_page=start_page, 
            last_page=end_page,
            dpi=300
        )
        page_offset = start_page - 1
    else:
        images = convert_from_path(pdf_path, dpi=300)
        page_offset = 0
    
    return images, page_offset


def _process_extracted_text(pages_data: List[Tuple[int, str]], translator: Optional[TamilTranslator], translate: bool) -> str:
    content_parts = []
    
    for page_num, text in pages_data:
        page_header = f"\n{'='*70}\nPage {page_num}\n{'='*70}\n"
        
        if translate and translator:
            print(f"Translating page {page_num}...")
            try:
                translated_text = translator.translate_text(text)
                content_parts.append(page_header + translated_text)
            except Exception as e:
                print(f"Translation failed for page {page_num}: {e}")
                content_parts.append(page_header + f"[Translation Error]\n{text}")
        else:
            content_parts.append(page_header + text)
    
    return '\n\n'.join(content_parts)


def _save_output_file(output_path: str, content: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"✓ Output saved to: {output_path}")
    print(f"✓ File size: {file_size_kb:.2f} KB")


def _display_summary(output_path: str, content: str, translated: bool, page_offset: int):
    print(f"\n--- Sample from Page {1 + page_offset} ---")
    lines = content.split('\n')
    
    # Find first non-header content
    sample_lines = []
    header_passed = False
    
    for line in lines:
        if '=' in line and 'Page' in line:
            header_passed = True
            continue
        elif header_passed and line.strip():
            sample_lines.append(line)
            if len(sample_lines) >= 8:
                break
    
    for line in sample_lines:
        print(line)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='OCR Tamil PDF to Unicode text with optional English translation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # OCR only (Tamil Unicode)
  python3 ocr_tamil_pdf.py book.pdf
  
  # OCR + Translation to English
  python3 ocr_tamil_pdf.py book.pdf --translate
  
  # Process specific pages with translation
  python3 ocr_tamil_pdf.py book.pdf --start 1 --end 5 --translate
  
  # Custom output file
  python3 ocr_tamil_pdf.py book.pdf output.txt --translate

Requirements for translation:
  pip install google-cloud-translate
  Set up Google Cloud credentials (GOOGLE_APPLICATION_CREDENTIALS)
        """
    )
    
    parser.add_argument('pdf_file', help='Input PDF file path')
    parser.add_argument('output_file', nargs='?', help='Output text file path (optional)')
    parser.add_argument('--start', type=int, help='Start page number (1-indexed)')
    parser.add_argument('--end', type=int, help='End page number (1-indexed)')
    parser.add_argument('--translate', action='store_true', 
                       help='Translate Tamil text to English using Google Translate API')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_file):
        print(f"Error: File '{args.pdf_file}' not found!")
        sys.exit(1)
    
    if args.start and args.end and args.start > args.end:
        print("Error: Start page must be less than or equal to end page!")
        sys.exit(1)
    
    if args.translate and not GOOGLE_TRANSLATE_AVAILABLE:
        print("Error: Translation requested but google-cloud-translate not installed!")
        print("Install with: pip install google-cloud-translate")
        print("Set up Google Cloud credentials: https://cloud.google.com/docs/authentication/getting-started")
        sys.exit(1)
    
    result = ocr_pdf_to_unicode_text(
        args.pdf_file, 
        args.output_file,
        args.start,
        args.end,
        args.translate
    )
    
    if result:
        print(f"\n🎉 Processing completed successfully!")
        if args.translate:
            print(f"📖 Tamil PDF → English translation saved to: {result}")
        else:
            print(f"📝 Tamil Unicode text saved to: {result}")
    else:
        print("\n❌ Processing failed!")
        sys.exit(1)
