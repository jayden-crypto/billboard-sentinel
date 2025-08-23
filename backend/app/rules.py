"""
Violation Rules Engine for Billboard Compliance
Implements standardized violation detection with configurable thresholds
"""

import os
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ViolationType(Enum):
    SIZE_VIOLATION = "size"
    PLACEMENT_VIOLATION = "placement"
    LICENSE_MISSING = "license_missing"
    LICENSE_INVALID = "license_invalid"
    OBSCENE_CONTENT = "obscene_content"
    JUNCTION_PROXIMITY = "junction_proximity"

@dataclass
class ViolationRule:
    """Represents a single violation rule with threshold and severity"""
    rule_type: ViolationType
    threshold: float
    severity: int  # 1-5 scale
    description: str
    enabled: bool = True

@dataclass
class Detection:
    """Billboard detection data structure"""
    bbox: List[float]  # [x1, y1, x2, y2]
    est_width_m: float
    est_height_m: float
    license_id: Optional[str]
    ocr_text: Optional[str]
    confidence: float

@dataclass
class Violation:
    """Violation result with details"""
    rule_type: ViolationType
    severity: int
    reason: str
    confidence: float
    metadata: Dict = None

class BillboardRulesEngine:
    """Main rules engine for billboard violation detection"""
    
    def __init__(self):
        self.rules = self._load_default_rules()
        self.obscene_keywords = [
            "explicit", "adult", "xxx", "gambling", "tobacco", 
            "alcohol", "drugs", "violence", "hate"
        ]
    
    def _load_default_rules(self) -> List[ViolationRule]:
        """Load default violation rules from environment or config"""
        return [
            ViolationRule(
                rule_type=ViolationType.SIZE_VIOLATION,
                threshold=float(os.getenv('CITY_MAX_AREA', '48.0')),  # 12m x 4m default
                severity=4,
                description="Billboard exceeds maximum permitted area"
            ),
            ViolationRule(
                rule_type=ViolationType.JUNCTION_PROXIMITY,
                threshold=float(os.getenv('CITY_MIN_DIST', '50.0')),  # 50m minimum
                severity=3,
                description="Billboard too close to traffic junction"
            ),
            ViolationRule(
                rule_type=ViolationType.LICENSE_MISSING,
                threshold=1.0,  # Binary rule
                severity=5,
                description="No valid license displayed on billboard"
            ),
            ViolationRule(
                rule_type=ViolationType.OBSCENE_CONTENT,
                threshold=0.7,  # Confidence threshold for content detection
                severity=5,
                description="Billboard contains inappropriate content"
            ),
            ViolationRule(
                rule_type=ViolationType.LICENSE_INVALID,
                threshold=1.0,  # Binary rule
                severity=5,
                description="License not found in municipal registry"
            )
        ]
    
    def evaluate_detection(self, detection: Detection, lat: float, lon: float, 
                          junctions_data: List[Dict] = None, 
                          registry_check_func=None) -> List[Violation]:
        """
        Evaluate a single detection against all active rules
        
        Args:
            detection: Billboard detection data
            lat, lon: GPS coordinates of detection
            junctions_data: List of nearby traffic junctions
            registry_check_func: Function to check license validity
            
        Returns:
            List of violations found
        """
        violations = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            violation = None
            
            if rule.rule_type == ViolationType.SIZE_VIOLATION:
                violation = self._check_size_violation(detection, rule)
            elif rule.rule_type == ViolationType.JUNCTION_PROXIMITY:
                violation = self._check_junction_proximity(lat, lon, rule, junctions_data)
            elif rule.rule_type == ViolationType.LICENSE_MISSING:
                violation = self._check_license_missing(detection, rule)
            elif rule.rule_type == ViolationType.LICENSE_INVALID and registry_check_func:
                violation = self._check_license_invalid(detection, rule, registry_check_func)
            elif rule.rule_type == ViolationType.OBSCENE_CONTENT:
                violation = self._check_obscene_content(detection, rule)
            
            if violation:
                violations.append(violation)
        
        return violations
    
    def _check_size_violation(self, detection: Detection, rule: ViolationRule) -> Optional[Violation]:
        """Check if billboard exceeds maximum permitted area"""
        area = detection.est_width_m * detection.est_height_m
        max_area = rule.threshold
        
        if area > max_area:
            return Violation(
                rule_type=rule.rule_type,
                severity=rule.severity,
                reason=f"Area {area:.1f}m² exceeds limit of {max_area}m²",
                confidence=min(0.9, (area - max_area) / max_area),
                metadata={"actual_area": area, "max_area": max_area}
            )
        return None
    
    def _check_junction_proximity(self, lat: float, lon: float, rule: ViolationRule, 
                                 junctions_data: List[Dict]) -> Optional[Violation]:
        """Check if billboard is too close to traffic junction"""
        if not junctions_data:
            return None
            
        min_distance = rule.threshold
        
        for junction in junctions_data:
            try:
                j_coords = junction["geometry"]["coordinates"]
                j_lon, j_lat = j_coords[0], j_coords[1]
                distance = self._haversine_distance(lat, lon, j_lat, j_lon)
                
                if distance < min_distance:
                    junction_name = junction.get("properties", {}).get("name", "Unknown Junction")
                    return Violation(
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        reason=f"Only {distance:.0f}m from {junction_name} (min: {min_distance}m)",
                        confidence=min(0.9, (min_distance - distance) / min_distance),
                        metadata={"distance": distance, "junction_name": junction_name}
                    )
            except (KeyError, IndexError, TypeError):
                continue
                
        return None
    
    def _check_license_missing(self, detection: Detection, rule: ViolationRule) -> Optional[Violation]:
        """Check if billboard is missing license information"""
        if not detection.license_id or detection.license_id.strip() == "":
            return Violation(
                rule_type=rule.rule_type,
                severity=rule.severity,
                reason="No license number detected on billboard",
                confidence=0.8,
                metadata={"ocr_text": detection.ocr_text}
            )
        return None
    
    def _check_license_invalid(self, detection: Detection, rule: ViolationRule, 
                              registry_check_func) -> Optional[Violation]:
        """Check if billboard license is invalid or expired"""
        if not detection.license_id or not registry_check_func:
            return None
            
        is_valid = registry_check_func(detection.license_id.strip())
        
        if not is_valid:
            return Violation(
                rule_type=rule.rule_type,
                severity=rule.severity,
                reason=f"License {detection.license_id} not found in registry",
                confidence=0.9,
                metadata={"license_id": detection.license_id}
            )
        return None
    
    def _check_obscene_content(self, detection: Detection, rule: ViolationRule) -> Optional[Violation]:
        """Check if billboard contains inappropriate content"""
        if not detection.ocr_text:
            return None
            
        text_lower = detection.ocr_text.lower()
        found_keywords = [kw for kw in self.obscene_keywords if kw in text_lower]
        
        if found_keywords:
            confidence = min(0.95, len(found_keywords) * 0.3)
            return Violation(
                rule_type=rule.rule_type,
                severity=rule.severity,
                reason=f"Inappropriate content detected: {', '.join(found_keywords)}",
                confidence=confidence,
                metadata={"keywords": found_keywords, "full_text": detection.ocr_text}
            )
        return None
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in meters"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def add_custom_rule(self, rule: ViolationRule):
        """Add a custom violation rule"""
        self.rules.append(rule)
    
    def disable_rule(self, rule_type: ViolationType):
        """Disable a specific rule type"""
        for rule in self.rules:
            if rule.rule_type == rule_type:
                rule.enabled = False
    
    def get_rule_summary(self) -> Dict:
        """Get summary of all active rules"""
        return {
            "total_rules": len(self.rules),
            "active_rules": len([r for r in self.rules if r.enabled]),
            "rules": [
                {
                    "type": rule.rule_type.value,
                    "threshold": rule.threshold,
                    "severity": rule.severity,
                    "enabled": rule.enabled,
                    "description": rule.description
                }
                for rule in self.rules
            ]
        }
