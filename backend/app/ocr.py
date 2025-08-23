"""
OCR Module for License Number and QR Code Detection
Implements text extraction from billboard images for compliance verification
"""

import re
import random
from typing import List, Dict, Optional, Tuple
from PIL import Image
import json

class BillboardOCR:
    """OCR system for extracting license numbers and text from billboards"""
    
    def __init__(self):
        self.license_patterns = [
            r'LIC-[A-Z]{3}-\d{3,4}',  # LIC-CHD-001
            r'[A-Z]{2,3}/\d{4}/\d{2,4}',  # CH/2024/001
            r'ADV-\d{6}',  # ADV-240001
            r'PERMIT-\d{4}-\d{3}'  # PERMIT-2024-001
        ]
        
        # Common billboard text patterns for mock OCR
        self.mock_texts = [
            "PREMIUM PROPERTIES AVAILABLE",
            "BEST DEALS IN TOWN",
            "LUXURY APARTMENTS FOR SALE",
            "MEGA SALE EVENT",
            "GRAND OPENING SOON",
            "QUALITY EDUCATION CENTER",
            "HEALTHCARE SERVICES",
            "RESTAURANT & BANQUET HALL",
            "SHOPPING MALL OPENING",
            "REAL ESTATE INVESTMENT"
        ]
        
        # Mock license numbers for realistic simulation
        self.mock_licenses = [
            "LIC-CHD-001", "LIC-CHD-002", "LIC-CHD-003", "LIC-CHD-004",
            "CH/2024/156", "CH/2024/289", "ADV-240001", "PERMIT-2024-078"
        ]
    
    def extract_text_from_image(self, image_path: str) -> Dict:
        """
        Extract all text from billboard image using OCR
        
        Args:
            image_path: Path to the billboard image
            
        Returns:
            Dictionary with extracted text, license numbers, and confidence
        """
        try:
            # Load image to get realistic dimensions for mock
            with Image.open(image_path) as img:
                width, height = img.size
        except:
            width, height = 1920, 1080
        
        # Mock OCR extraction with realistic results
        extracted_text = self._generate_mock_ocr_text()
        license_numbers = self._extract_license_numbers(extracted_text)
        qr_codes = self._detect_qr_codes(extracted_text)
        
        # Calculate confidence based on text clarity simulation
        confidence = self._calculate_ocr_confidence(extracted_text, width, height)
        
        return {
            "full_text": extracted_text,
            "license_numbers": license_numbers,
            "qr_codes": qr_codes,
            "confidence": confidence,
            "method": "mock_ocr_v1.2"
        }
    
    def _generate_mock_ocr_text(self) -> str:
        """Generate realistic OCR text output"""
        # Simulate main billboard text
        main_text = random.choice(self.mock_texts)
        
        # 60% chance of including license number
        license_text = ""
        if random.random() < 0.6:
            license_text = f" {random.choice(self.mock_licenses)}"
        
        # 30% chance of additional text
        additional_text = ""
        if random.random() < 0.3:
            additional = ["CALL 9876543210", "WWW.EXAMPLE.COM", "AUTHORIZED DEALER"]
            additional_text = f" {random.choice(additional)}"
        
        # 10% chance of OCR errors (realistic simulation)
        full_text = main_text + license_text + additional_text
        if random.random() < 0.1:
            full_text = self._introduce_ocr_errors(full_text)
        
        return full_text
    
    def _extract_license_numbers(self, text: str) -> List[str]:
        """Extract license numbers using regex patterns"""
        found_licenses = []
        
        for pattern in self.license_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_licenses.extend(matches)
        
        # Remove duplicates and return
        return list(set(found_licenses))
    
    def _detect_qr_codes(self, text: str) -> List[Dict]:
        """Mock QR code detection (20% chance)"""
        qr_codes = []
        
        if random.random() < 0.2:
            # Simulate QR code content
            qr_content = random.choice([
                "https://example.com/billboard/LIC-CHD-001",
                "LICENSE:LIC-CHD-002|VALID:2025-12-31",
                "PERMIT:CH/2024/156|AUTHORITY:CHANDIGARH"
            ])
            
            qr_codes.append({
                "content": qr_content,
                "position": [random.randint(50, 200), random.randint(50, 150)],
                "confidence": random.uniform(0.8, 0.95)
            })
        
        return qr_codes
    
    def _calculate_ocr_confidence(self, text: str, width: int, height: int) -> float:
        """Calculate OCR confidence based on various factors"""
        base_confidence = 0.85
        
        # Text length factor
        length_factor = min(1.0, len(text) / 50)
        
        # Image size factor (larger images generally have better OCR)
        size_factor = min(1.0, (width * height) / (1920 * 1080))
        
        # License detection bonus
        license_bonus = 0.1 if any(pattern in text for pattern in ["LIC-", "PERMIT-", "ADV-"]) else 0
        
        confidence = base_confidence * length_factor * size_factor + license_bonus
        return min(0.95, max(0.3, confidence))
    
    def _introduce_ocr_errors(self, text: str) -> str:
        """Introduce realistic OCR errors for simulation"""
        # Common OCR substitutions
        substitutions = {
            'O': '0', '0': 'O', 'I': '1', '1': 'I',
            'S': '5', '5': 'S', 'B': '8', '8': 'B'
        }
        
        result = text
        # Apply 1-2 random substitutions
        for _ in range(random.randint(1, 2)):
            if result:
                pos = random.randint(0, len(result) - 1)
                char = result[pos]
                if char in substitutions:
                    result = result[:pos] + substitutions[char] + result[pos+1:]
        
        return result
    
    def verify_license_format(self, license_text: str) -> Dict:
        """Verify if extracted license follows valid format"""
        for pattern in self.license_patterns:
            if re.match(pattern, license_text, re.IGNORECASE):
                return {
                    "valid_format": True,
                    "pattern": pattern,
                    "license": license_text.upper()
                }
        
        return {
            "valid_format": False,
            "pattern": None,
            "license": license_text
        }

# Utility function for integration
def extract_billboard_text(image_path: str) -> Dict:
    """
    Convenience function for billboard text extraction
    
    Returns:
        Dictionary with OCR results and license information
    """
    ocr = BillboardOCR()
    return ocr.extract_text_from_image(image_path)
