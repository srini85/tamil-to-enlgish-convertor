"""OCR processing for Tamil PDFs using Tesseract."""

from typing import Optional, List, Tuple
from pdf2image import convert_from_path
import pytesseract
from PIL import Image


class OCRError(Exception):
    """Custom exception for OCR-related errors."""
    pass


class TamilOCRProcessor:
    """OCR processor specialized for Tamil text extraction from PDFs."""
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        self.tesseract_config = r'--oem 3 --psm 6'
    
    def process_pdf(
        self, 
        pdf_path: str, 
        start_page: Optional[int] = None, 
        end_page: Optional[int] = None
    ) -> List[Tuple[int, str]]:
        """
        Extract Tamil text from PDF pages using OCR.
        
        Args:
            pdf_path: Path to the PDF file
            start_page: First page to process (1-indexed)
            end_page: Last page to process (1-indexed)
            
        Returns:
            List of tuples (page_number, extracted_text)
            
        Raises:
            OCRError: If OCR processing fails
        """
        try:
            images, page_offset = self._convert_pdf_to_images(
                pdf_path, start_page, end_page
            )
            
            print(f"Total pages to process: {len(images)}")
            
            extracted_pages = []
            
            for i, image in enumerate(images, 1):
                page_num = i + page_offset
                print(f"OCR processing page {page_num}...", end='\r')
                
                text = self._extract_text_from_image(image)
                
                if text.strip():
                    extracted_pages.append((page_num, text.strip()))
            
            print(f"\nOCR processing complete! Extracted text from {len(extracted_pages)} pages")
            
            if not extracted_pages:
                raise OCRError("No text extracted from any pages")
                
            return extracted_pages
            
        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise OCRError(f"OCR processing failed: {e}")
    
    def _convert_pdf_to_images(
        self, 
        pdf_path: str, 
        start_page: Optional[int], 
        end_page: Optional[int]
    ) -> Tuple[List[Image.Image], int]:
        """Convert PDF pages to images for OCR processing."""
        print("Converting PDF to images...")
        
        if start_page and end_page:
            print(f"Processing pages {start_page} to {end_page}")
            images = convert_from_path(
                pdf_path, 
                first_page=start_page, 
                last_page=end_page,
                dpi=self.dpi
            )
            page_offset = start_page - 1
        else:
            images = convert_from_path(pdf_path, dpi=self.dpi)
            page_offset = 0
        
        return images, page_offset
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """Extract Tamil text from a single image using Tesseract OCR."""
        return pytesseract.image_to_string(
            image, 
            lang='tam',
            config=self.tesseract_config
        )