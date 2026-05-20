"""
Tests for bathydata-map — underwater autonomous drone mapping
"""

import pytest
from bathydata_map import Bathymap, DiveSite, DIVE_PRECISE, DIVE_MAPPED, DIVE_ANALYSIS, DIVE_EXPLORATORY
from signal_chain import Dial


def test_divesite_creation():
    site = DiveSite("site-001", lat=45.3, lon=-122.8, depth=87.2)
    assert site.name == "site-001"
    assert site.lat == 45.3
    assert site.lon == -122.8
    assert site.depth == 87.2


def test_divesite_record_depth():
    site = DiveSite("site-001")
    site.record_depth(87.2, confidence=1.0)
    
    assert len(site.depth_readings) == 1
    assert site.depth_readings[0]["value"] == 87.2
    assert len(site.snaps) == 1


def test_divesite_record_sonar():
    site = DiveSite("site-001")
    site.record_sonar("sediment", intensity=0.9, confidence=0.85)
    
    assert len(site.sonar_readings) == 1
    assert site.sonar_readings[0]["target"] == "sediment"
    assert site.sonar_readings[0]["intensity"] == 0.9


def test_divesite_record_sediment():
    site = DiveSite("site-001")
    site.record_sediment("sand", confidence=0.9)
    
    assert site.sediment_type == "sand"
    assert len(site.snaps) == 1


def test_divesite_record_temperature():
    site = DiveSite("site-001")
    site.record_temperature(4.5, depth_m=50.0, confidence=0.8)
    
    assert len(site.temperature_readings) == 1
    assert site.temperature_readings[0]["value"] == 4.5


def test_divesite_record_current():
    site = DiveSite("site-001")
    site.record_current(speed_m_s=0.5, direction_deg=180.0, confidence=0.7)
    
    assert site.current_data["speed"] == 0.5
    assert site.current_data["direction"] == 180.0


def test_divesite_record_object():
    site = DiveSite("site-001")
    site.record_object("anchor", x=1.0, y=2.0, z=-3.0, confidence=0.85)
    
    assert len(site.detected_objects) == 1
    assert site.detected_objects[0]["object_class"] == "anchor"


def test_divesite_record_coordinate():
    site = DiveSite("site-001")
    site.record_coordinate(lat=45.3, lon=-122.8, depth=87.0)
    
    assert site.lat == 45.3
    assert site.lon == -122.8
    assert site.depth == 87.0


def test_divesite_get_bathy_summary():
    site = DiveSite("site-001", lat=45.3, lon=-122.8, depth=87.2)
    site.record_depth(87.2)
    site.record_sonar("rock")
    site.record_object("anchor", x=0, y=0, z=0)
    
    summary = site.get_bathy_summary()
    assert summary["site"] == "site-001"
    assert summary["depth_readings"] == 1
    assert summary["sonar_returns"] == 1
    assert summary["objects_detected"] == 1


def test_bathymap_creation():
    bmap = Bathymap("salvage-op-2026")
    assert bmap.name == "salvage-op-2026"
    assert bmap.global_dial.position == 0.1  # default DIVE_PRECISE


def test_bathymap_dive():
    bmap = Bathymap("test-op")
    site = bmap.dive("site-001", lat=45.3, lon=-122.8, depth=87.2)
    
    assert isinstance(site, DiveSite)
    assert site.name == "site-001"
    assert site.lat == 45.3


def test_bathymap_connect_sites():
    bmap = Bathymap("test-op")
    bmap.dive("site-a", lat=0.0, lon=0.0)
    bmap.dive("site-b", lat=1.0, lon=0.0)
    bmap.connect_sites("site-a", "site-b")
    
    assert "site-b" in bmap.rooms["site-a"].connections
    assert "site-a" in bmap.rooms["site-b"].connections


def test_bathymap_find_anomalies():
    bmap = Bathymap("test-op")
    site = bmap.dive("wreck-site")
    site.record_object("metal_mass", x=0, y=0, z=0, confidence=0.85)
    
    # Snaps are added with record_object
    anomalies = bmap.find_anomalies(threshold=0.8)
    
    assert len(anomalies) == 1
    assert anomalies[0][0] == "wreck-site"


def test_bathymap_get_map_data():
    bmap = Bathymap("test-op")
    bmap.dive("site-a", lat=45.3, lon=-122.8, depth=87.0)
    bmap.dive("site-b", lat=45.4, lon=-122.9, depth=95.0)
    
    map_data = bmap.get_map_data()
    assert len(map_data["sites"]) == 2
    assert map_data["name"] == "test-op"


def test_bathymap_path_through_sites():
    bmap = Bathymap("test-op")
    bmap.dive("site-a")
    bmap.dive("site-b")
    bmap.dive("site-c")
    
    path = bmap.path_through_sites(["site-a", "site-b", "site-c"])
    
    assert len(path) == 3
    assert path[0].name == "site-a"


def test_bathymap_with_dial_presets():
    bmap = Bathymap("exploratory-op", global_dial=DIVE_EXPLORATORY)
    site = bmap.dive("deep-site", lat=45.0, lon=-122.0, depth=200.0)
    
    assert site.dialect.position == 0.8


def test_dive_precise_vs_exploratory():
    """Test that different dial levels return different results."""
    bmap = Bathymap("test-op")
    site = bmap.dive("site-001")
    site.record_depth(87.2, confidence=1.0)
    site.add_inference({"hypothesis": "possible_wreckage"}, confidence=0.6)
    
    # DIVE_PRECISE: only snaps
    precise_results = site.query(DIVE_PRECISE)
    # DIVE_EXPLORATORY: snaps + high-confidence inferences
    exploratory_results = site.query(DIVE_EXPLORATORY)
    
    assert len(precise_results) >= 1
    assert len(exploratory_results) >= len(precise_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])