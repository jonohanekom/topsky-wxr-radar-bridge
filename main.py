import os
import math
import time
from io import BytesIO
from typing import Tuple, Dict, Any, Union
import configparser
import sys
import httpx
from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import asyncio

# Add dotenv support to load .env file automatically (for development)
from dotenv import load_dotenv
load_dotenv()

# Application version
__version__ = "1.0.1"

# Configuration loading with fallback to environment variables
def load_config():
    """Load configuration from config.ini file or environment variables as fallback."""
    config = configparser.ConfigParser()
    
    # Try to load from config.ini first
    config_file = "config.ini"
    if os.path.exists(config_file):
        print(f"Loading configuration from {config_file}")
        config.read(config_file)
        
        # Get values from config file
        api_key = config.get('openweathermap', 'api_key', fallback=None)
        base_url = config.get('server', 'base_url', fallback="http://localhost:8000")
        tile_layer = config.get('openweathermap', 'tile_layer', fallback="precipitation_new")
        
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            print("ERROR: Please edit config.ini and set your OpenWeatherMap API key")
            print("Get your API key from: https://openweathermap.org/api")
            sys.exit(1)
            
        return api_key, base_url, tile_layer
    else:
        # Fallback to environment variables (for development)
        print("config.ini not found, using environment variables")
        api_key = os.getenv("OPENWEATHER_API_KEY")
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        tile_layer = os.getenv("TILE_LAYER", "precipitation_new")
        
        if not api_key:
            print("ERROR: No API key found. Please create config.ini or set OPENWEATHER_API_KEY environment variable")
            sys.exit(1)
            
        return api_key, base_url, tile_layer

# Load configuration
OPENWEATHER_API_KEY, BASE_URL, TILE_LAYER = load_config()
# Available OWM tile layers:
# - "precipitation_new" = Rain/snow intensity (current)
# - "clouds_new" = Cloud cover percentage
# - "temp_new" = Temperature
# - "wind_new" = Wind speed
# - "pressure_new" = Atmospheric pressure
# - "humidity_new" = Relative humidity

app = FastAPI(
    title="TopSky Weather Radar Bridge",
    description="A FastAPI server that bridges TopSky/EuroScope with OpenWeatherMap radar data",
    version=__version__
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming HTTP requests and their responses."""
    print(f"→ {request.method} {request.url}")
    response = await call_next(request)
    print(f"← {response.status_code}")
    return response

@app.middleware("http")
async def normalize_path_middleware(request: Request, call_next):
    # Normalize double slashes in the path
    scope = request.scope
    original_path = scope["path"]
    normalized_path = original_path.replace("//", "/")
    if normalized_path != original_path:
        scope["path"] = normalized_path
        # Rebuild the request with the new path
        request = Request(scope, request.receive)
    return await call_next(request)

def latlon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
    """
    Convert latitude and longitude to OWM tile x, y coordinates for a given zoom level.
    Uses the Web Mercator projection math.
    """
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    # Calculate x tile index
    x = int((lon + 180.0) / 360.0 * n)
    # Calculate y tile index
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def latlon_to_world_pixels(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    """Converts lat/lon to world pixel coordinates at a given zoom level."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n * 256
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * 256
    return x, y

def create_blank_tile(width: int = 256, height: int = 256) -> bytes:
    """
    Create a fully transparent PNG tile of a given size.
    Used as a fallback for errors or missing data.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

async def fetch_tile_async(client: httpx.AsyncClient, z: int, x: int, y: int) -> Union[bytes, None]:
    """Asynchronously fetches a single tile from OWM."""
    tile_url = f"https://tile.openweathermap.org/map/{TILE_LAYER}/{z}/{x}/{y}.png"
    try:
        resp = await client.get(tile_url, params={"appid": OPENWEATHER_API_KEY})
        if resp.status_code == 200:
            return resp.content
        # For 404s (tile doesn't exist), we'll return None and handle it as a blank tile
        if resp.status_code == 404:
            print(f"Tile not found (404): {tile_url}")
            return None
        resp.raise_for_status() # Raise for other errors like 401, 500, etc.
        return resp.content
    except httpx.RequestError as e:
        print(f"HTTP error fetching tile {z}/{x}/{y}: {e}")
        return None
    except Exception as e:
        print(f"Generic error fetching tile {z}/{x}/{y}: {e}")
        return None

async def create_stitched_tile(
    zoom: int,
    center_lat: float,
    center_lon: float,
    width: int,
    height: int,
) -> bytes:
    """
    Creates a large, high-resolution composite tile by fetching and stitching multiple OWM tiles.
    """
    print(
        f"Creating stitched tile: zoom={zoom}, center=({center_lat}, {center_lon}), "
        f"size=({width}x{height})"
    )
    # 1. Find the pixel coordinates of the center point in the world map
    center_px_x, center_px_y = latlon_to_world_pixels(center_lat, center_lon, zoom)

    # 2. Determine the top-left corner of our composite image in world pixels
    top_left_px_x = center_px_x - width / 2
    top_left_px_y = center_px_y - height / 2

    # 3. Calculate the range of OWM tiles we need to fetch
    start_tile_x = math.floor(top_left_px_x / 256)
    end_tile_x = math.ceil((top_left_px_x + width) / 256)
    start_tile_y = math.floor(top_left_px_y / 256)
    end_tile_y = math.ceil((top_left_px_y + height) / 256)
    
    print(f"Tile grid to fetch: x=[{start_tile_x}...{end_tile_x}], y=[{start_tile_y}...{end_tile_y}]")

    # 4. Fetch all required tiles asynchronously
    tasks = []
    tile_coords = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for y in range(start_tile_y, end_tile_y + 1):
            for x in range(start_tile_x, end_tile_x + 1):
                tasks.append(fetch_tile_async(client, zoom, x, y))
                tile_coords.append((x, y))
        
        fetched_tiles_data = await asyncio.gather(*tasks)

    # 5. Create the composite image and paste the fetched tiles
    composite_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    for i, tile_data in enumerate(fetched_tiles_data):
        if tile_data:
            try:
                tile_image = Image.open(BytesIO(tile_data)).convert("RGBA")
                tile_x, tile_y = tile_coords[i]

                # Calculate the paste position on the composite image
                paste_x = round(tile_x * 256 - top_left_px_x)
                paste_y = round(tile_y * 256 - top_left_px_y)

                composite_image.paste(tile_image, (paste_x, paste_y))
            except Exception as e:
                print(f"Error processing tile {tile_coords[i]}: {e}")

    # 6. Return the final image as bytes
    buf = BytesIO()
    composite_image.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def fetch_and_return_tile(z: int, x: int, y: int) -> bytes:
    """
    Fetch a weather tile from OpenWeatherMap and return it as PNG bytes.
    If fetching or processing fails, return a blank tile.
    """
    tile_url = f"https://tile.openweathermap.org/map/{TILE_LAYER}/{z}/{x}/{y}.png"
    print(f"Fetching OWM tile: {tile_url}")
    try:
        with httpx.Client(timeout=10.0) as client:
            # Fetch the tile from OWM with API key
            resp = client.get(tile_url, params={"appid": OPENWEATHER_API_KEY})
            resp.raise_for_status()
            print(f"OWM tile fetched successfully: {len(resp.content)} bytes")
            # Convert to RGBA to ensure compatibility
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf.getvalue()
    except Exception as e:
        print(f"Tile fetch/process error: {e}")
        print("Returning blank tile due to error")
        return create_blank_tile()

def generate_timestamps() -> Dict[str, Any]:
    """
    Generate RainViewer-compatible timestamp data for radar and satellite layers.
    Returns a dict with 'radar' and 'satellite' keys.
    """
    now = int(time.time())
    now = (now // 600) * 600  # Round to nearest 10 minutes
    past = []
    for i in range(3, -1, -1):
        t = now - i * 600
        past.append({"time": t, "path": f"/v2/radar/{t}"})
    nowcast = []
    for i in range(1, 3):
        t = now + i * 600
        nowcast.append({"time": t, "path": f"/v2/radar/nowcast_{os.urandom(6).hex()}"})
    satellite = []
    for i in range(3, -1, -1):
        t = now - i * 600
        satellite.append({"time": t, "path": f"/v2/satellite/{os.urandom(6).hex()}"})
    return {"radar": {"past": past, "nowcast": nowcast}, "satellite": {"infrared": satellite}}

@app.get("/")
async def root():
    """Root endpoint for health check and info."""
    return {"message": "RainViewer Spoof API for TopSky", "status": "running"}

@app.get("/public/weather-maps.json", response_class=JSONResponse)
@app.get("/public/weather-maps.json/", response_class=JSONResponse)
@app.get("/public/weather-maps.json/{http_stuff:path}", response_class=JSONResponse)
async def weather_maps_json(http_stuff: str = None):
    """
    Serve RainViewer-compatible weather-maps.json for radar and satellite layers.
    Handles trailing slashes and extra path segments for compatibility.
    """
    ts = generate_timestamps()
    data = {
        "version": "2.0",
        "generated": int(time.time()),
        "host": BASE_URL,
        "radar": ts["radar"],
        "satellite": ts["satellite"]
    }
    return JSONResponse(
        content=data,
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/v2/radar/{timestamp}/{z}/{x}/{y}.png")
async def radar_tile_standard(timestamp: int, z: int, x: int, y: int):
    """
    Standard RainViewer radar tile endpoint.
    Returns a PNG tile for the given timestamp, zoom, x, y.
    """
    print(f"Standard radar tile request: timestamp={timestamp}, z={z}, x={x}, y={y}")
    tile_bytes = fetch_and_return_tile(z, x, y)
    return Response(content=tile_bytes, media_type="image/png")

@app.get("/v2/radar/{timestamp}/{size_str}/{zoom_str}/{lat_str}/{lon_str}/.png")
async def radar_tile_topsky_stitched(
    timestamp: str,
    size_str: str,
    zoom_str: str,
    lat_str: str,
    lon_str: str,
):
    """
    New TopSky endpoint that correctly interprets the URL format and generates stitched tiles.
    The URL format is: /v2/radar/{timestamp}/{size}/{zoom}/{lat}/{lon}/.png
    """
    print(f"Stitched TopSky Request: ts={timestamp}, size={size_str}, zoom={zoom_str}, lat={lat_str}, lon={lon_str}")
    try:
        # FastAPI's path converter can sometimes pass values like '512.0'
        # so we handle floats before converting to int.
        width = int(float(size_str))
        height = int(float(size_str))
        # --- ZOOM MODIFICATION ---
        # We add +1 to the zoom level requested by the client.
        # This allows the client to request a wider area (lower zoom)
        # while the server fetches higher-resolution tiles for that area.
        zoom = int(float(zoom_str)) + 1
        print(f"Applying zoom multiplier: client zoom={zoom_str}, server fetch zoom={zoom}")
        # -------------------------
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError as e:
        print(f"Error converting path parameters: {e}")
        # Use a default size for the blank tile if conversion fails early
        return Response(content=create_blank_tile(512, 512), media_type="image/png")

    try:
        image_bytes = await create_stitched_tile(
            zoom=zoom,
            center_lat=lat,
            center_lon=lon,
            width=width,
            height=height,
        )
        return Response(content=image_bytes, media_type="image/png")
    except Exception as e:
        print(f"Error creating stitched tile: {e}")
        # Return a blank tile of the requested size on error
        return Response(content=create_blank_tile(width, height), media_type="image/png")

@app.get("/v2/radar/nowcast_{nowcast_id}/{z}/{x}/{y}.png")
async def nowcast_tile_standard(nowcast_id: str, z: int, x: int, y: int):
    """
    Standard RainViewer nowcast tile endpoint.
    Returns a PNG tile for the given nowcast id, zoom, x, y.
    """
    print(f"Standard nowcast tile request: nowcast_id={nowcast_id}, z={z}, x={x}, y={y}")
    tile_bytes = fetch_and_return_tile(z, x, y)
    return Response(content=tile_bytes, media_type="image/png")

@app.get("/v2/radar/nowcast_{nowcast_id}/{x}/{z}/{lon}/{lat}/.png")
async def nowcast_tile_topsky(nowcast_id: str, x: str, z: int, lon: str, lat: str):
    """
    TopSky/EuroScope specific nowcast tile endpoint with lat/lon parameters.
    Converts lat/lon to tile coordinates and fetches the correct OWM tile.
    """
    print(f"TopSky nowcast tile request: nowcast_id={nowcast_id}, x={x}, z={z}, lon={lon}, lat={lat}")
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except ValueError as e:
        print(f"Error converting nowcast lon/lat: {e}")
        return Response(content=create_blank_tile(), media_type="image/png")

    tile_x, tile_y = latlon_to_tile(lat_f, lon_f, z)
    print(f"Converted lat/lon to tile_x={tile_x}, tile_y={tile_y}")
    
    # Use calculated tile coordinates (not the provided x value)
    print(f"Using calculated coordinates: z={z}, x={tile_x}, y={tile_y}")
    tile_bytes = fetch_and_return_tile(z, tile_x, tile_y)
    return Response(content=tile_bytes, media_type="image/png")

@app.get("/v2/satellite/{satellite_id}/{z}/{x}/{y}.png")
async def satellite_tile(satellite_id: str, z: int, x: int, y: int):
    """
    Satellite tile endpoint - returns blank tile as we're not implementing satellite data.
    """
    print(f"Satellite tile request: satellite_id={satellite_id}, z={z}, x={x}, y={y}")
    return Response(content=create_blank_tile(), media_type="image/png")

@app.get("/health")
async def health():
    """Health check endpoint with version information."""
    return {
        "status": "healthy", 
        "version": __version__,
        "timestamp": int(time.time()),
        "config_source": "config.ini" if os.path.exists("config.ini") else "environment"
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path: str):
    """
    Catch-all route for unmatched requests.
    Returns a blank PNG for .png requests, or a JSON 404 for others.
    """
    print(f"Unexpected request to: /{path}")
    if path.endswith('.png'):
        print("Returning blank tile for unexpected PNG request")
        return Response(content=create_blank_tile(), media_type="image/png")
    return JSONResponse({"error": "Not found", "path": path, "message": "Check your TopSky configuration"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    # Startup info
    print("Starting RainViewer Spoof API for TopSky...")
    print(f"Base URL: {BASE_URL}")
    print(f"OpenWeatherMap API Key: {'*' * (len(OPENWEATHER_API_KEY) - 4) + OPENWEATHER_API_KEY[-4:]}")
    print("Server will be available at: http://localhost:8000")
    print(f"Weather data endpoint: {BASE_URL}/public/weather-maps.json")
    print("Format: RainViewer-compatible API v2.0")
    print("PNG Format: Maximum compatibility for TopSky plugin")
    print("NOTE: Debug route removed - only real OWM tiles or blank tiles will be served")
    uvicorn.run(app, host="0.0.0.0", port=8000) 