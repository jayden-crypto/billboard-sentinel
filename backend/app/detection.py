"""
Computer Vision Detection Pipeline for Billboard Analysis
Mock implementation with realistic outputs for hackathon demo
"""

import json
import random
from typing import List, Dict, Tuple
from PIL import Image
import numpy as np
from .size_estimation import estimate_billboard_size
from .ocr import extract_billboard_text

class BillboardDetector:
    """Mock computer vision detector that simulates YOLO/Faster R-CNN detection"""
    
    def __init__(self):
        self.model_version = "billboard-yolo-v1.2"
        self.confidence_threshold = 0.5
        
    def detect_billboards(self, image_path: str) -> List[Dict]:
        """
        Simulate billboard detection with realistic bounding boxes and metadata
        """
        try:
            # Load image to get dimensions
            with Image.open(image_path) as img:
                width, height = img.size
        except:
            # Fallback dimensions
            width, height = 1920, 1080
            
        detections = []
        
        # Simulate 1-3 billboard detections per image
        num_detections = random.randint(1, 3)
        
        for i in range(num_detections):
            # Generate realistic bounding box
            bbox = self._generate_realistic_bbox(width, height)
            
            # Estimate real-world dimensions using camera-based size estimation
            size_estimate = estimate_billboard_size(bbox, width, height)
            est_width, est_height = size_estimate["width_m"], size_estimate["height_m"]
            
            # Generate corner points for perspective analysis
            corners = self._generate_corners(bbox)
            
            # Enhanced OCR text extraction with license detection
            ocr_result = extract_billboard_text(image_path)
            ocr_text = ocr_result["full_text"]
            qr_text = ocr_result["qr_codes"][0]["content"] if ocr_result["qr_codes"] else ""
            license_id = ocr_result["license_numbers"][0] if ocr_result["license_numbers"] else ""
            
            # Confidence score
            confidence = random.uniform(0.6, 0.95)
            
            detection = {
                'bbox': bbox,
                'corners': corners,
                'est_width_m': est_width,
                'est_height_m': est_height,
                'confidence': confidence,
                'qr_text': qr_text,
                'ocr_text': ocr_text,
                'license_id': license_id
            }
            
            detections.append(detection)
            
        return detections
    
    def _generate_realistic_bbox(self, img_width: int, img_height: int) -> List[float]:
        """Generate realistic bounding box coordinates (normalized 0-1)"""
        # Billboards are typically in upper 2/3 of image and take significant space
        x_center = random.uniform(0.2, 0.8)
        y_center = random.uniform(0.1, 0.6)  # Upper portion of image
        
        # Billboard width/height ratios are typically 3:1 to 6:1
        aspect_ratio = random.uniform(3.0, 6.0)
        
        # Size varies but should be substantial
        width = random.uniform(0.3, 0.7)
        height = width / aspect_ratio
        
        # Ensure bbox stays within image bounds
        x1 = max(0, x_center - width/2)
        y1 = max(0, y_center - height/2)
        x2 = min(1, x_center + width/2)
        y2 = min(1, y_center + height/2)
        
        return [x1, y1, x2, y2]
    
    def _generate_corners(self, bbox: List[float]) -> List[List[float]]:
        """Generate corner points with slight perspective distortion"""
        x1, y1, x2, y2 = bbox
        
        # Add slight random distortion to simulate perspective
        distortion = 0.02
        
        corners = [
            [x1 + random.uniform(-distortion, distortion), y1 + random.uniform(-distortion, distortion)],  # Top-left
            [x2 + random.uniform(-distortion, distortion), y1 + random.uniform(-distortion, distortion)],  # Top-right
            [x2 + random.uniform(-distortion, distortion), y2 + random.uniform(-distortion, distortion)],  # Bottom-right
            [x1 + random.uniform(-distortion, distortion), y2 + random.uniform(-distortion, distortion)]   # Bottom-left
        ]
        
        return corners
    
    def _estimate_dimensions(self, bbox: List[float], img_width: int, img_height: int) -> Tuple[float, float]:
        """Estimate real-world dimensions using perspective analysis"""
        x1, y1, x2, y2 = bbox
        
        # Calculate pixel dimensions
        pixel_width = (x2 - x1) * img_width
        pixel_height = (y2 - y1) * img_height
        
        # Mock depth estimation based on position in image
        # Lower in image = closer = larger actual size
        depth_factor = 1.0 + (y1 + y2) / 2  # Average y position
        
        # Typical billboard sizes with some variation
        base_width = random.uniform(8, 15)  # meters
        base_height = base_width / random.uniform(3, 6)  # aspect ratio
        
        # Apply depth correction
        estimated_width = base_width * depth_factor
        estimated_height = base_height * depth_factor
        
        return round(estimated_width, 1), round(estimated_height, 1)
    
    def _generate_mock_ocr(self) -> str:
        """Generate mock OCR text that might appear on billboards"""
        mock_texts = [
            "PREMIUM PROPERTIES AVAILABLE",
            "NEW SHOPPING MALL OPENING SOON",
            "LUXURY APARTMENTS FOR SALE",
            "BEST DEALS ON ELECTRONICS",
            "RESTAURANT GRAND OPENING",
            "MOBILE OFFERS STARTING ₹99",
            "EDUCATION INSTITUTE ADMISSIONS OPEN",
            "HEALTHCARE SERVICES 24/7",
            "AUTOMOBILE SHOWROOM",
            "FASHION STORE MEGA SALE"
        ]
        return random.choice(mock_texts)
    
    def _generate_mock_qr(self) -> str:
        """Generate mock QR code content"""
        qr_contents = [
            "https://example-business.com/offers",
            "Contact: +91-9876543210",
            "Visit: www.billboard-business.in",
            "App: Download from PlayStore",
            "Offer Code: SAVE20NOW"
        ]
        return random.choice(qr_contents)
    
    def _generate_mock_license(self) -> str:
        """Generate mock license ID"""
        # Format: CITY-YYYY-NNNN
        cities = ["CHD", "DEL", "MUM", "BLR", "HYD"]
        year = random.choice([2023, 2024])
        number = random.randint(1000, 9999)
        return f"{random.choice(cities)}-{year}-{number}"

# Singleton detector instance
detector = BillboardDetector()

def analyze_billboard_image(image_path: str) -> List[Dict]:
    """
    Main function to analyze uploaded billboard image
    Returns list of detections with violations
    """
    return detector.detect_billboards(image_path)
