"""
Unit tests for Billboard Violation Rules Engine
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rules import (
    BillboardRulesEngine, Detection, Violation, ViolationType, ViolationRule
)

class TestBillboardRulesEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = BillboardRulesEngine()
        
        # Sample detection data
        self.valid_detection = Detection(
            bbox=[100, 100, 300, 200],
            est_width_m=8.0,
            est_height_m=3.0,
            license_id="LIC-CHD-001",
            ocr_text="Premium Properties Available - LIC-CHD-001",
            confidence=0.85
        )
        
        self.oversized_detection = Detection(
            bbox=[50, 50, 400, 250],
            est_width_m=15.0,
            est_height_m=5.0,
            license_id="LIC-CHD-002",
            ocr_text="Mega Sale Event",
            confidence=0.92
        )
        
        self.unlicensed_detection = Detection(
            bbox=[150, 150, 350, 250],
            est_width_m=6.0,
            est_height_m=2.5,
            license_id="",
            ocr_text="Best Deals in Town",
            confidence=0.78
        )
        
        # Sample junction data
        self.sample_junctions = [
            {
                "geometry": {"coordinates": [76.3651, 30.3555]},
                "properties": {"name": "Sector 17 Junction"}
            }
        ]
    
    def test_size_violation_detection(self):
        """Test detection of oversized billboards"""
        violations = self.engine.evaluate_detection(
            self.oversized_detection, 30.3555, 76.3651
        )
        
        size_violations = [v for v in violations if v.rule_type == ViolationType.SIZE_VIOLATION]
        self.assertEqual(len(size_violations), 1)
        
        violation = size_violations[0]
        self.assertEqual(violation.severity, 4)
        self.assertIn("75.0m²", violation.reason)  # 15 * 5 = 75
        self.assertGreater(violation.confidence, 0.0)
    
    def test_valid_size_no_violation(self):
        """Test that valid-sized billboards don't trigger size violations"""
        violations = self.engine.evaluate_detection(
            self.valid_detection, 30.3555, 76.3651
        )
        
        size_violations = [v for v in violations if v.rule_type == ViolationType.SIZE_VIOLATION]
        self.assertEqual(len(size_violations), 0)
    
    def test_license_missing_violation(self):
        """Test detection of missing license"""
        violations = self.engine.evaluate_detection(
            self.unlicensed_detection, 30.3555, 76.3651
        )
        
        license_violations = [v for v in violations if v.rule_type == ViolationType.LICENSE_MISSING]
        self.assertEqual(len(license_violations), 1)
        
        violation = license_violations[0]
        self.assertEqual(violation.severity, 5)
        self.assertIn("No license number", violation.reason)
    
    def test_junction_proximity_violation(self):
        """Test detection of billboards too close to junctions"""
        # Place billboard very close to junction (same coordinates)
        violations = self.engine.evaluate_detection(
            self.valid_detection, 30.3555, 76.3651, 
            junctions_data=self.sample_junctions
        )
        
        proximity_violations = [v for v in violations if v.rule_type == ViolationType.JUNCTION_PROXIMITY]
        self.assertEqual(len(proximity_violations), 1)
        
        violation = proximity_violations[0]
        self.assertEqual(violation.severity, 3)
        self.assertIn("Sector 17 Junction", violation.reason)
    
    def test_junction_proximity_safe_distance(self):
        """Test that billboards at safe distance don't trigger proximity violations"""
        # Place billboard far from junction
        violations = self.engine.evaluate_detection(
            self.valid_detection, 30.4000, 76.4000,  # ~5km away
            junctions_data=self.sample_junctions
        )
        
        proximity_violations = [v for v in violations if v.rule_type == ViolationType.JUNCTION_PROXIMITY]
        self.assertEqual(len(proximity_violations), 0)
    
    def test_license_invalid_violation(self):
        """Test detection of invalid license"""
        # Mock registry check function that returns False
        mock_registry_check = Mock(return_value=False)
        
        violations = self.engine.evaluate_detection(
            self.valid_detection, 30.3555, 76.3651,
            registry_check_func=mock_registry_check
        )
        
        invalid_license_violations = [v for v in violations if v.rule_type == ViolationType.LICENSE_INVALID]
        self.assertEqual(len(invalid_license_violations), 1)
        
        violation = invalid_license_violations[0]
        self.assertEqual(violation.severity, 5)
        self.assertIn("LIC-CHD-001", violation.reason)
        mock_registry_check.assert_called_once_with("LIC-CHD-001")
    
    def test_obscene_content_detection(self):
        """Test detection of inappropriate content"""
        obscene_detection = Detection(
            bbox=[100, 100, 300, 200],
            est_width_m=8.0,
            est_height_m=3.0,
            license_id="LIC-CHD-003",
            ocr_text="Adult Entertainment XXX Gambling Casino",
            confidence=0.85
        )
        
        violations = self.engine.evaluate_detection(
            obscene_detection, 30.3555, 76.3651
        )
        
        content_violations = [v for v in violations if v.rule_type == ViolationType.OBSCENE_CONTENT]
        self.assertEqual(len(content_violations), 1)
        
        violation = content_violations[0]
        self.assertEqual(violation.severity, 5)
        self.assertIn("adult", violation.reason.lower())
        self.assertIn("xxx", violation.reason.lower())
    
    def test_haversine_distance_calculation(self):
        """Test GPS distance calculation accuracy"""
        # Test known distance: Chandigarh to Delhi (~250km)
        chandigarh_lat, chandigarh_lon = 30.7333, 76.7794
        delhi_lat, delhi_lon = 28.7041, 77.1025
        
        distance = self.engine._haversine_distance(
            chandigarh_lat, chandigarh_lon, delhi_lat, delhi_lon
        )
        
        # Should be approximately 250,000 meters (±10%)
        self.assertGreater(distance, 225000)
        self.assertLess(distance, 275000)
    
    def test_custom_rule_addition(self):
        """Test adding custom violation rules"""
        initial_count = len(self.engine.rules)
        
        custom_rule = ViolationRule(
            rule_type=ViolationType.SIZE_VIOLATION,
            threshold=100.0,
            severity=2,
            description="Custom size limit"
        )
        
        self.engine.add_custom_rule(custom_rule)
        self.assertEqual(len(self.engine.rules), initial_count + 1)
    
    def test_rule_disable_functionality(self):
        """Test disabling specific rule types"""
        self.engine.disable_rule(ViolationType.SIZE_VIOLATION)
        
        violations = self.engine.evaluate_detection(
            self.oversized_detection, 30.3555, 76.3651
        )
        
        size_violations = [v for v in violations if v.rule_type == ViolationType.SIZE_VIOLATION]
        self.assertEqual(len(size_violations), 0)
    
    def test_rule_summary_generation(self):
        """Test rule summary generation"""
        summary = self.engine.get_rule_summary()
        
        self.assertIn("total_rules", summary)
        self.assertIn("active_rules", summary)
        self.assertIn("rules", summary)
        self.assertIsInstance(summary["rules"], list)
        self.assertGreater(summary["total_rules"], 0)
    
    def test_multiple_violations_single_detection(self):
        """Test detection with multiple violations"""
        # Create detection that violates multiple rules
        multi_violation_detection = Detection(
            bbox=[50, 50, 400, 300],
            est_width_m=20.0,  # Oversized
            est_height_m=6.0,
            license_id="",     # Missing license
            ocr_text="XXX Adult Content Gambling",  # Obscene content
            confidence=0.88
        )
        
        violations = self.engine.evaluate_detection(
            multi_violation_detection, 30.3555, 76.3651,
            junctions_data=self.sample_junctions
        )
        
        # Should have size, license, content, and proximity violations
        violation_types = {v.rule_type for v in violations}
        expected_types = {
            ViolationType.SIZE_VIOLATION,
            ViolationType.LICENSE_MISSING,
            ViolationType.OBSCENE_CONTENT,
            ViolationType.JUNCTION_PROXIMITY
        }
        
        self.assertTrue(expected_types.issubset(violation_types))
        self.assertGreaterEqual(len(violations), 4)

if __name__ == '__main__':
    # Create tests directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)
