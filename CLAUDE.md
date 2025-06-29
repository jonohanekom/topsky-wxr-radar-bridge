# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python FastAPI server that acts as a bridge between the TopSky plugin for EuroScope and the OpenWeatherMap (OWM) API. It mimics the RainViewer API for aviation radar plugins, providing real-time weather radar data in a format compatible with air traffic control simulation software.

**CRITICAL: This server must be reliable and performant for real-time air traffic control simulation. Always act as a senior software engineer when working on this code.**

## Architecture

The application is a single-file FastAPI server (`main.py`) that:

1. **Acts as a proxy/bridge** between TopSky plugin and OpenWeatherMap API
2. **Handles coordinate conversion** from lat/lon to OWM tile coordinates using Web Mercator projection
3. **Serves multiple endpoint formats**:
   - Standard RainViewer format: `/v2/radar/{timestamp}/{z}/{x}/{y}.png`
   - TopSky-specific format: `/v2/radar/{timestamp}/{x}/{z}/{lon}/{lat}/.png` (non-standard)
   - Metadata endpoint: `/public/weather-maps.json`
4. **Image processing** ensures all PNG tiles are 256x256 RGBA format for maximum compatibility
5. **Error handling** returns blank transparent tiles for failed requests or out-of-range coordinates

## Key Components

- **Coordinate conversion**: `latlon_to_tile()` function converts geographic coordinates to tile indices using Web Mercator projection
- **Tile fetching**: `fetch_and_return_tile()` retrieves tiles from OpenWeatherMap and processes them
- **Timestamp generation**: `generate_timestamps()` creates RainViewer-compatible time navigation data
- **CORS middleware** for cross-origin requests
- **Request logging middleware** for debugging
- **Path normalization middleware** handles double slashes in URLs

## Development Commands

### Install Dependencies
```bash
uv pip install -r pyproject.toml
```

### Run the Server
```bash
python main.py
```
The server runs on `http://localhost:8000` by default.

### Testing
```bash
pytest
```

### Code Formatting
```bash
black main.py
```

## Configuration

Uses environment variables (loaded from `.env` file):
- `OPENWEATHER_API_KEY`: Required OpenWeatherMap API key
- `BASE_URL`: Server base URL (default: `http://localhost:8000`)
- `TILE_LAYER`: OWM layer type (default: `precipitation_new`)

Available tile layers: `precipitation_new`, `clouds_new`, `temp_new`, `wind_new`, `pressure_new`, `humidity_new`

## Testing the API

- Health check: `GET /health`
- Weather maps metadata: `GET /public/weather-maps.json`
- Test radar tile: `GET /v2/radar/1234567890/5/16/10.png`

## Development Guidelines

### Code Quality Standards
- **Reasoning First**: Always provide 4-5 sentences explaining your approach before writing code
- **Defensive Programming**: Assume inputs from client or OWM may be malformed, out of range, or unexpected
- **Type Hinting**: Use Python's type hints for all function signatures and complex variables
- **Error Boundaries**: Wrap all external interactions (API calls, file I/O) in try/except blocks

### Critical Requirements
- **Always return valid PNG**: The server must ALWAYS return a valid PNG response, even if blank. HTTP errors or corrupted images are fatal failures for the TopSky plugin
- **RGBA Format**: Always convert images to RGBA format using `.convert("RGBA")` for maximum compatibility
- **Simple PNG Format**: Use basic `img.save(buf, format="PNG")` without extra parameters - TopSky's PNG decoder is highly simplistic
- **256x256 Tiles**: Ensure all tiles are exactly 256x256 pixels to match TopSky configuration

### Performance Requirements
- **Async Operations**: Use `httpx.AsyncClient` for all OWM API calls to avoid blocking
- **P95 Response Time**: Strive to keep response time under 500ms for standard tiles
- **Connection Pooling**: Reuse `httpx.AsyncClient` instances across requests

### Error Handling Patterns
```python
def validate_coordinates(lat: float, lon: float) -> bool:
    """Checks if latitude and longitude are within valid WGS 84 range."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0

def is_valid_zoom(zoom: int) -> bool:
    """OWM generally supports zoom levels from 0 to 18."""
    return 0 <= zoom <= 18
```

## Critical Historical Issues Solved

### 1. Non-Standard TopSky URL Format
- **Issue**: TopSky uses non-standard format `/v2/radar/{timestamp}/{x}/{z}/{lon}/{lat}/.png` instead of standard RainViewer format
- **Solution**: Use string type hints for lon/lat parameters and convert to float manually inside endpoint functions
- **Location**: `radar_tile_topsky()` function in main.py:169

### 2. PNG Compatibility Problems
- **Issue**: TopSky plugin reported "file not recognized as a PNG" errors with valid PNG files
- **Solution**: Use simplest PNG save format without optimization parameters. TopSky's PNG decoder is intolerant of advanced PNG features
- **Critical**: Always use `img.save(buf, format="PNG")` without extra parameters

### 3. Metadata Request Flexibility
- **Issue**: TopSky requests `weather-maps.json` with trailing slashes and other variations
- **Solution**: Use path converter `{http_stuff:path}` to catch all variations of the metadata endpoint
- **Location**: `weather_maps_json()` function with multiple route decorators

### 4. Configuration Alignment
- **Issue**: Visual artifacts (horizontal lines) when server tile size doesn't match TopSky configuration
- **Solution**: Ensure `WXR_ImageSize=256` in TopSky settings matches server's 256x256 output

## TopSky Plugin Configuration

Add to `TopSkySettings.txt`:
```
WXR_Server=http://localhost:8000
WXR_TimeStampsURL=http://localhost:8000/public/weather-maps.json
WXR_Page_Prefix=/v2/radar/
WXR_Page_Suffix=.png
WXR_ImageSize=256
```

## Security Requirements
- **Never commit API keys**: Always use environment variables or `.env` file
- **Input validation**: Sanitize client-provided input in logs to prevent log injection
- **Dependency updates**: Regularly update dependencies to patch security vulnerabilities