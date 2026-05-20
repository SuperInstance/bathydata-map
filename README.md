# bathydata-map

**Underwater autonomous drone mapping** — spatial memory of the seafloor with bathydata as ground truth anchors.

## Concept

Each dive location is a tile with:
- **Bathydata** (depth, sonar, sediment type) as hard snaps
- **Inference dial** for extrapolating marine features
- **Spatial continuity** between dive sites

As more dives complete, the map grows and inference quality improves — each new dive adds snaps that constrain future extrapolations.

## Usage

```python
from bathydata_map import Bathymap, DIVE_PRECISE, DIVE_EXPLORATORY

# Create a mapping session
map_session = Bathymap("salvage-op-2026-05-19")

# Add a dive site with bathydata
site = map_session.dive("site-001", lat=45.3, lon=-122.8, depth=87.2)
site.record_depth(87.2, confidence=1.0)
site.record_sonar("sediment", intensity=0.9)
site.record_coordinate(lat=45.3, lon=-122.8)

# Query at different inference levels
precise = site.query(DIVE_PRECISE)      # just bathydata facts
exploratory = site.query(DIVE_EXPLORATORY)  # inferred marine features

# Chain sites together
map_session.connect_sites("site-001", "site-002")

# Find anomalies (potential wreckage)
anomalies = map_session.find_anomalies(threshold=0.7)
```

## Bathydata Snap Types

- `depth`: precise depth reading from sonar
- `sediment`: bottom composition type
- `temperature`: water temperature at depth
- `current`: current speed/direction
- `object`: detected object with classification

## Dial Levels for Bathydata

```python
DIVE_PRECISE = Dial(0.1)      # Pure bathydata, no extrapolation
DIVE_MAPPED = Dial(0.3)      # Bathydata + inferred contours
DIVE_ANALYSIS = Dial(0.5)    # Contours + feature extrapolation
DIVE_EXPLORATORY = Dial(0.8) # Hypothesized features, needs verification
```

## See Also

- [signal-chain-core](../signal-chain-core) — core dial primitives
- [tile-chain](../tile-chain) — spatial anchoring for tiles

## License

MIT