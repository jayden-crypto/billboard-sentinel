"""
Geofence and Permitted Database Check Module
Implements location-based validation against municipal billboard registry
"""

import json
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class GeofenceZone:
    """Represents a geofenced area with specific billboard regulations"""
    zone_id: str
    name: str
    coordinates: List[Tuple[float, float]]  # Polygon boundary points
    max_billboards: int
    size_limit_m2: float
    prohibited: bool = False
    special_rules: Dict = None

class BillboardGeofence:
    """Geofence validation system for billboard placement compliance"""
    
    def __init__(self):
        self.restricted_zones = self._load_restricted_zones()
        self.permitted_locations = []
    
    def _load_restricted_zones(self) -> List[GeofenceZone]:
        """Load predefined restricted zones (schools, hospitals, religious sites)"""
        return [
            GeofenceZone(
                zone_id="school_buffer_001",
                name="Government Model Senior Secondary School Buffer",
                coordinates=[(30.3545, 76.3625), (30.3555, 76.3625), (30.3555, 76.3635), (30.3545, 76.3635)],
                max_billboards=0,
                size_limit_m2=0,
                prohibited=True,
                special_rules={"buffer_distance_m": 100, "reason": "Educational institution protection"}
            ),
            GeofenceZone(
                zone_id="hospital_buffer_001", 
                name="PGI Chandigarh Buffer Zone",
                coordinates=[(30.3520, 76.3580), (30.3530, 76.3580), (30.3530, 76.3590), (30.3520, 76.3590)],
                max_billboards=0,
                size_limit_m2=0,
                prohibited=True,
                special_rules={"buffer_distance_m": 200, "reason": "Healthcare facility protection"}
            ),
            GeofenceZone(
                zone_id="heritage_buffer_001",
                name="Rock Garden Heritage Site Buffer",
                coordinates=[(30.3575, 76.3665), (30.3585, 76.3665), (30.3585, 76.3675), (30.3575, 76.3675)],
                max_billboards=2,
                size_limit_m2=20.0,
                prohibited=False,
                special_rules={"aesthetic_approval_required": True, "reason": "Heritage site preservation"}
            ),
            GeofenceZone(
                zone_id="commercial_zone_001",
                name="Sector 17 Commercial Plaza",
                coordinates=[(30.3640, 76.3720), (30.3660, 76.3720), (30.3660, 76.3740), (30.3640, 76.3740)],
                max_billboards=10,
                size_limit_m2=48.0,
                prohibited=False,
                special_rules={"premium_zone": True, "higher_fees": True}
            )
        ]
    
    def check_location_compliance(self, lat: float, lon: float, 
                                billboard_area_m2: float = 0) -> Dict:
        """
        Check if billboard location complies with geofence regulations
        
        Args:
            lat, lon: Billboard GPS coordinates
            billboard_area_m2: Proposed billboard area
            
        Returns:
            Compliance result with violations and recommendations
        """
        violations = []
        zone_info = None
        compliance_status = "compliant"
        
        # Check against all restricted zones
        for zone in self.restricted_zones:
            if self._point_in_polygon(lat, lon, zone.coordinates):
                zone_info = zone
                
                if zone.prohibited:
                    violations.append({
                        "type": "prohibited_zone",
                        "severity": 5,
                        "reason": f"Billboard prohibited in {zone.name}",
                        "details": zone.special_rules.get("reason", "Zone restriction")
                    })
                    compliance_status = "prohibited"
                
                elif billboard_area_m2 > zone.size_limit_m2:
                    violations.append({
                        "type": "size_exceeds_zone_limit",
                        "severity": 4,
                        "reason": f"Area {billboard_area_m2}m² exceeds zone limit of {zone.size_limit_m2}m²",
                        "zone": zone.name
                    })
                    compliance_status = "non_compliant"
                
                break
        
        # Check buffer distances for sensitive areas
        buffer_violations = self._check_buffer_distances(lat, lon)
        violations.extend(buffer_violations)
        
        if buffer_violations:
            compliance_status = "non_compliant"
        
        return {
            "compliance_status": compliance_status,
            "zone_info": {
                "zone_id": zone_info.zone_id if zone_info else None,
                "zone_name": zone_info.name if zone_info else "Unzoned area",
                "max_billboards": zone_info.max_billboards if zone_info else "No limit",
                "size_limit_m2": zone_info.size_limit_m2 if zone_info else "Standard limit applies"
            },
            "violations": violations,
            "recommendations": self._generate_recommendations(violations, zone_info)
        }
    
    def check_permitted_database(self, license_id: str, lat: float, lon: float) -> Dict:
        """
        Check if billboard license exists in permitted database and location matches
        
        Args:
            license_id: Billboard license identifier
            lat, lon: Reported billboard location
            
        Returns:
            Database verification result
        """
        # Mock database check - in production, this would query actual municipal database
        permitted_billboards = [
            {"license_id": "LIC-CHD-001", "lat": 30.3555, "lon": 76.3651, "status": "active"},
            {"license_id": "LIC-CHD-002", "lat": 30.3542, "lon": 76.3620, "status": "active"},
            {"license_id": "LIC-CHD-003", "lat": 30.3598, "lon": 76.3712, "status": "active"},
            {"license_id": "LIC-CHD-004", "lat": 30.3521, "lon": 76.3589, "status": "expired"}
        ]
        
        # Find matching license
        matching_record = None
        for record in permitted_billboards:
            if record["license_id"] == license_id:
                matching_record = record
                break
        
        if not matching_record:
            return {
                "database_status": "not_found",
                "license_valid": False,
                "location_match": False,
                "reason": f"License {license_id} not found in municipal database"
            }
        
        # Check location proximity (within 50m tolerance)
        distance_m = self._haversine_distance(lat, lon, matching_record["lat"], matching_record["lon"])
        location_match = distance_m <= 50.0
        
        # Check license status
        license_valid = matching_record["status"] == "active"
        
        return {
            "database_status": "found",
            "license_valid": license_valid,
            "location_match": location_match,
            "distance_from_registered": round(distance_m, 1),
            "registered_location": [matching_record["lat"], matching_record["lon"]],
            "license_status": matching_record["status"],
            "reason": self._get_database_reason(license_valid, location_match, distance_m)
        }
    
    def _point_in_polygon(self, lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
        """Check if point is inside polygon using ray casting algorithm"""
        x, y = lon, lat
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _check_buffer_distances(self, lat: float, lon: float) -> List[Dict]:
        """Check minimum buffer distances from sensitive locations"""
        violations = []
        
        # Sensitive locations with required buffer distances
        sensitive_locations = [
            {"name": "DAV Public School", "lat": 30.3548, "lon": 76.3628, "buffer_m": 100},
            {"name": "Gurudwara Singh Sabha", "lat": 30.3562, "lon": 76.3645, "buffer_m": 75},
            {"name": "Children's Park", "lat": 30.3535, "lon": 76.3605, "buffer_m": 50}
        ]
        
        for location in sensitive_locations:
            distance = self._haversine_distance(lat, lon, location["lat"], location["lon"])
            if distance < location["buffer_m"]:
                violations.append({
                    "type": "buffer_violation",
                    "severity": 4,
                    "reason": f"Only {distance:.0f}m from {location['name']} (min: {location['buffer_m']}m)",
                    "location": location["name"],
                    "required_distance": location["buffer_m"],
                    "actual_distance": round(distance, 1)
                })
        
        return violations
    
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
    
    def _generate_recommendations(self, violations: List[Dict], zone_info: Optional[GeofenceZone]) -> List[str]:
        """Generate actionable recommendations based on violations"""
        recommendations = []
        
        if any(v["type"] == "prohibited_zone" for v in violations):
            recommendations.append("Relocate billboard outside restricted zone")
            recommendations.append("Consider alternative advertising methods for this area")
        
        if any(v["type"] == "size_exceeds_zone_limit" for v in violations):
            recommendations.append(f"Reduce billboard size to comply with zone limit")
            if zone_info:
                recommendations.append(f"Maximum allowed area: {zone_info.size_limit_m2}m²")
        
        if any(v["type"] == "buffer_violation" for v in violations):
            recommendations.append("Relocate billboard to maintain required buffer distances")
            recommendations.append("Check municipal guidelines for sensitive area buffers")
        
        if not violations:
            recommendations.append("Location complies with current regulations")
            recommendations.append("Ensure proper licensing and size compliance")
        
        return recommendations
    
    def _get_database_reason(self, license_valid: bool, location_match: bool, distance_m: float) -> str:
        """Generate reason message for database check result"""
        if not license_valid and not location_match:
            return f"License expired and location mismatch ({distance_m:.1f}m from registered)"
        elif not license_valid:
            return "License has expired"
        elif not location_match:
            return f"Location mismatch: {distance_m:.1f}m from registered location"
        else:
            return "License valid and location matches registered coordinates"

# Utility function for integration
def validate_billboard_location(lat: float, lon: float, license_id: str = None, 
                              area_m2: float = 0) -> Dict:
    """
    Comprehensive location validation for billboard placement
    
    Returns:
        Combined geofence and database validation results
    """
    geofence = BillboardGeofence()
    
    # Geofence compliance check
    location_result = geofence.check_location_compliance(lat, lon, area_m2)
    
    # Database verification if license provided
    database_result = None
    if license_id:
        database_result = geofence.check_permitted_database(license_id, lat, lon)
    
    return {
        "location_compliance": location_result,
        "database_verification": database_result,
        "overall_status": "compliant" if location_result["compliance_status"] == "compliant" and 
                         (not database_result or database_result["license_valid"]) else "non_compliant"
    }
