"""
bathydata-map — Underwater autonomous drone mapping

Spatial memory of the seafloor with bathydata as ground truth anchors.
Each dive site is a tile with depth, sonar, sediment, and coordinate snaps.

Usage:
    from bathydata_map import Bathymap, DIVE_PRECISE
    
    map_session = Bathymap("salvage-op-2026")
    site = map_session.dive("site-001", lat=45.3, lon=-122.8, depth=87.2)
    site.record_depth(87.2, confidence=1.0)
    
    results = site.query(DIVE_PRECISE)
"""

from signal_chain import Dial, Room, SignalChain, DIAL_FORMAL


class DiveSite(Room):
    """
    A single dive location with bathydata snaps.
    
    Attributes:
        lat, lon, depth: spatial coordinates
        depth_readings: list of depth measurements
        sonar_readings: list of sonar returns
        sediment_type: bottom composition
        temperature_readings: water temperature at depth
        detected_objects: list of detected objects
    """
    
    def __init__(self, name: str, lat: float = 0.0, lon: float = 0.0, depth: float = 0.0, dialect: Dial = None):
        super().__init__(name=name, dialect=dialect)
        self.lat = lat
        self.lon = lon
        self.depth = depth
        self.depth_readings = []
        self.sonar_readings = []
        self.sediment_type = None
        self.temperature_readings = []
        self.current_data = None
        self.detected_objects = []
    
    def record_depth(self, depth_m: float, confidence: float = 1.0, timestamp: str = None):
        """Record a depth reading."""
        reading = {"type": "depth", "value": depth_m, "unit": "meters", "confidence": confidence}
        if timestamp:
            reading["timestamp"] = timestamp
        self.depth_readings.append(reading)
        self.add_snap(reading, confidence=confidence)
    
    def record_sonar(self, target_type: str, intensity: float = 0.5, confidence: float = 0.8):
        """Record sonar return data."""
        reading = {"type": "sonar", "target": target_type, "intensity": intensity}
        self.sonar_readings.append(reading)
        self.add_snap(reading, confidence=confidence)
    
    def record_sediment(self, sediment_type: str, confidence: float = 0.9):
        """Record bottom sediment type."""
        self.sediment_type = sediment_type
        reading = {"type": "sediment", "value": sediment_type}
        self.add_snap(reading, confidence=confidence)
    
    def record_temperature(self, temp_c: float, depth_m: float, confidence: float = 0.8):
        """Record water temperature at depth."""
        reading = {"type": "temperature", "value": temp_c, "unit": "celsius", "depth": depth_m}
        self.temperature_readings.append(reading)
        self.add_snap(reading, confidence=confidence)
    
    def record_current(self, speed_m_s: float, direction_deg: float, confidence: float = 0.7):
        """Record current speed and direction."""
        self.current_data = {"speed": speed_m_s, "direction": direction_deg}
        reading = {"type": "current", "speed": speed_m_s, "direction": direction_deg}
        self.add_snap(reading, confidence=confidence)
    
    def record_object(self, object_type: str, x: float, y: float, z: float, confidence: float = 0.8):
        """Record a detected object at relative coordinates."""
        obj = {"type": "object", "object_class": object_type, "x": x, "y": y, "z": z}
        self.detected_objects.append(obj)
        self.add_snap(obj, confidence=confidence)
    
    def record_coordinate(self, lat: float = None, lon: float = None, depth: float = None):
        """Update site coordinates."""
        if lat is not None:
            self.lat = lat
        if lon is not None:
            self.lon = lon
        if depth is not None:
            self.depth = depth
        coord = {"type": "coordinate", "lat": self.lat, "lon": self.lon, "depth": self.depth}
        self.add_snap(coord, confidence=1.0)
    
    def get_bathy_summary(self) -> dict:
        """Get a summary of all bathydata for this site."""
        return {
            "site": self.name,
            "coordinates": {"lat": self.lat, "lon": self.lon, "depth": self.depth},
            "depth_readings": len(self.depth_readings),
            "sonar_returns": len(self.sonar_readings),
            "sediment": self.sediment_type,
            "objects_detected": len(self.detected_objects),
        }


class Bathymap(SignalChain):
    """
    A chain of dive sites with bathydata snapping.
    
    Each dive is a DiveSite tile with depth, sonar, sediment, and object detection.
    Sites can be connected to build a spatial map of the seafloor.
    
    Usage:
        map_session = Bathymap("salvage-op-2026")
        site = map_session.dive("site-001", lat=45.3, lon=-122.8, depth=87.2)
        site.record_depth(87.2)
        map_session.connect_sites("site-001", "site-002")
    """
    
    def __init__(self, name: str, global_dial: Dial = None):
        super().__init__(name=name, global_dial=global_dial or Dial(0.1))
    
    def dive(self, name: str, lat: float = 0.0, lon: float = 0.0, depth: float = 0.0, dial: Dial = None) -> DiveSite:
        """Get or create a dive site with coordinates."""
        if name not in self.rooms:
            d = dial or self.global_dial
            self.rooms[name] = DiveSite(name=name, lat=lat, lon=lon, depth=depth, dialect=d)
        return self.rooms[name]
    
    def connect_sites(self, site_a: str, site_b: str, metadata: dict = None):
        """Connect two dive sites (bidirectional)."""
        if site_a in self.rooms and site_b in self.rooms:
            self.rooms[site_a].connect(site_b, metadata)
            self.rooms[site_b].connect(site_a, metadata)
    
    def find_anomalies(self, threshold: float = 0.7) -> list:
        """
        Find sites with high-confidence inferred objects.
        Potential wreckage or notable features.
        
        Returns:
            list of (site_name, object) tuples
        """
        anomalies = []
        for name, site in self.rooms.items():
            for obj in site.detected_objects:
                # Find confidence of this object's snap
                for snap in site.snaps:
                    if snap.fact.get("type") == "object" and snap.fact.get("object_class") == obj.get("object_class"):
                        if snap.confidence >= threshold:
                            anomalies.append((name, obj))
        return anomalies
    
    def get_map_data(self) -> dict:
        """Get all sites with coordinates for map visualization."""
        return {
            "name": self.name,
            "sites": [
                {
                    "name": name,
                    "lat": site.lat,
                    "lon": site.lon,
                    "depth": site.depth,
                    "objects": len(site.detected_objects),
                }
                for name, site in self.rooms.items()
            ]
        }
    
    def path_through_sites(self, site_names: list) -> list:
        """Get a path through specified sites."""
        result = []
        for name in site_names:
            if name in self.rooms:
                result.append(self.rooms[name])
        return result


# Dial presets for different dive modes

DIVE_PRECISE = Dial(0.1)       # Pure bathydata, no extrapolation
DIVE_MAPPED = Dial(0.3)         # Bathydata + inferred contours
DIVE_ANALYSIS = Dial(0.5)       # Contours + feature extrapolation  
DIVE_EXPLORATORY = Dial(0.8)     # Hypothesized features, needs verification


__all__ = [
    "DiveSite",
    "Bathymap",
    "DIVE_PRECISE",
    "DIVE_MAPPED",
    "DIVE_ANALYSIS",
    "DIVE_EXPLORATORY",
]