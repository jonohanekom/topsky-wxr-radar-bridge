import os
import math
import time
from io import BytesIO
from typing import Tuple, Dict, Any
import httpx
from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Add dotenv support to load .env file automatically
from dotenv import load_dotenv
load_dotenv()

# Config
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TILE_LAYER = os.getenv("TILE_LAYER", "precipitation_new")  # Now also loaded from .env if set
# Available OWM tile layers:
# - "precipitation_new" = Rain/snow intensity (current)
# - "clouds_new" = Cloud cover percentage
# - "temp_new" = Temperature
# - "wind_new" = Wind speed
# - "pressure_new" = Atmospheric pressure
# - "humidity_new" = Relative humidity

app = FastAPI(title="RainViewer Spoof API for TopSky")

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

def create_blank_tile() -> bytes:
    """
    Create a fully transparent 256x256 PNG tile.
    Used as a fallback for errors or missing data.
    """
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
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

@app.get("/v2/radar/{timestamp}/{x}/{z}/{lon}/{lat}/.png")
async def radar_tile_topsky(timestamp: int, x: int, z: int, lon: str, lat: str):
    """
    TopSky/EuroScope specific radar tile endpoint with lat/lon parameters.
    Converts lat/lon to tile coordinates and fetches the correct OWM tile.
    """
    print(f"TopSky radar tile request: timestamp={timestamp}, x={x}, z={z}, lon={lon}, lat={lat}")
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except Exception as e:
        print(f"Error converting lon/lat: {e}")
        return Response(content=create_blank_tile(), media_type="image/png")
    
    # Convert lat/lon to tile coordinates
    tile_x, tile_y = latlon_to_tile(lat_f, lon_f, z)
    print(f"Converted lat/lon to tile_x={tile_x}, tile_y={tile_y}")
    
    # Use calculated tile coordinates (not the provided x value)
    print(f"Using calculated coordinates: z={z}, x={tile_x}, y={tile_y}")
    tile_bytes = fetch_and_return_tile(z, tile_x, tile_y)
    return Response(content=tile_bytes, media_type="image/png")

@app.get("/v2/radar/nowcast_{nowcast_id}/{z}/{x}/{y}.png")
async def nowcast_tile_standard(nowcast_id: str, z: int, x: int, y: int):
    """
    Standard RainViewer nowcast tile endpoint.
    Returns a PNG tile for the given nowcast id, zoom, x, y.
    """
    print(f"Standard nowcast tile request: nowcast_id={nowcast_id}, z={z}, x={x}, y={y}")
    tile_bytes = fetch_and_return_tile(z, x, y)
    return Response(content=tile_bytes, media_type="image/png")

@app.get("/v2/radar/nowcast_{nowcast_id}/{x}/{z}/{lon:float}/{lat:float}/.png")
async def nowcast_tile_topsky(nowcast_id: str, x: int, z: int, lon: float, lat: float):
    """
    TopSky/EuroScope specific nowcast tile endpoint with lat/lon parameters.
    Converts lat/lon to tile coordinates and fetches the correct OWM tile.
    """
    print(f"TopSky nowcast tile request: nowcast_id={nowcast_id}, x={x}, z={z}, lon={lon}, lat={lat}")
    tile_x, tile_y = latlon_to_tile(lat, lon, z)
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
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": int(time.time())}

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