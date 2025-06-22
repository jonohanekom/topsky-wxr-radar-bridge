# TopSky weather radar bridge
[![Status](https://img.shields.io/badge/status-in_development-orange)](https://github.com/your-username/readback)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A FastAPI-based server that mimics the RainViewer API, allowing the TopSky plugin in EuroScope to display real-time weather radar data using OpenWeatherMap (OWM) as the backend.

---

## Features

- **RainViewer-compatible API**: Seamlessly integrates with TopSky/EuroScope and other clients expecting the RainViewer API.
- **Real Precipitation Data**: Fetches and serves live radar tiles from OpenWeatherMap.
- **Multiple Endpoints**: Supports both standard RainViewer and TopSky/EuroScope-specific tile formats.
- **PNG Compatibility**: Always returns valid, fully opaque or transparent 256x256 PNGs for maximum plugin compatibility.
- **CORS & Error Handling**: Handles CORS, logs requests, and returns blank tiles for errors or unknown routes.
- **Configurable**: Easily configure API keys, base URL, and tile layer via environment variables.

---

## How It Works

This server acts as a drop-in replacement for the RainViewer API. When the TopSky plugin requests weather radar tiles, the server:

1. **Receives the tile request** (including non-standard TopSky/EuroScope routes with lat/lon).
2. **Converts lat/lon to OWM tile coordinates** (if needed).
3. **Fetches the corresponding radar tile** from OpenWeatherMap using your API key.
4. **Processes the image** to ensure maximum compatibility (RGBA, 256x256, no advanced PNG features).
5. **Returns the PNG tile** to the client. If OWM returns an error or the area is out of range, a blank tile is returned.
6. **Serves a RainViewer-compatible weather-maps.json** for time navigation.

---

## Quickstart

### 1. Clone the Repository
```sh
git clone https://github.com/jonohanekom/topsky-wxr-radar-bridge.git
cd topsky-wxr-radar-bridge
```

### 2. Install Dependencies
This project uses [uvicorn](https://www.uvicorn.org/), [FastAPI](https://fastapi.tiangolo.com/), [httpx](https://www.python-httpx.org/), and [Pillow](https://python-pillow.org/).

Install [uv](https://github.com/astral-sh/uv) if you don't have it:
```sh
pip install uv
```

Then install dependencies:
```sh
uv pip install -r pyproject.toml
```

### 3. Set Up Environment Variables
Create a `.env` file or set these variables in your shell:

```
OPENWEATHER_API_KEY=your_owm_api_key
BASE_URL=http://localhost:8000
TILE_LAYER=precipitation_new  # or clouds_new, temp_new, etc.
```
### 4. Configure TopSky
Place the following in your `TopSkySettings.txt` file. Then configure the bounds of your coordinates

```
WXR_Server=http://localhost:8000
WXR_TimeStampsURL=http://localhost:8000/public/weather-maps.json
WXR_Page_Prefix=/v2/radar/
WXR_Page_Suffix=.png
```

### 5. Run the Server
```sh
python main.py
```

The server will be available at [http://localhost:8000](http://localhost:8000).

---

## Configuration

- **OPENWEATHER_API_KEY**: Your OpenWeatherMap API key (required).
- **BASE_URL**: The base URL for the API (default: `http://localhost:8000`).
- **TILE_LAYER**: The OWM tile layer to use. Options include:
  - `precipitation_new` (default)
  - `clouds_new`
  - `temp_new`
  - `wind_new`
  - `pressure_new`
  - `humidity_new`

You can set these in a `.env` file or as environment variables.

---

## Endpoints

- `/public/weather-maps.json` — RainViewer-compatible metadata for radar/satellite layers
- `/v2/radar/{timestamp}/{z}/{x}/{y}.png` — Standard RainViewer radar tile
- `/v2/radar/{timestamp}/{x}/{z}/{lon}/{lat}/.png` — TopSky/EuroScope-specific tile (lat/lon)
- `/v2/satellite/...` — Returns blank tiles (satellite not implemented)
- `/health` — Health check

---

## For TopSky/EuroScope Users

- Set your WXR server to `http://localhost:8000` (or your server's address)
- Make sure your plugin's image size and zoom settings match the server's output (default: 256x256, zoom 3-5 recommended)
- The server will automatically convert TopSky's lat/lon requests to the correct OWM tile

---

## Troubleshooting

- **Blank radar tiles?**
  - Check if there is precipitation in your area on [OpenWeatherMap](https://openweathermap.org/weathermap).
  - Ensure your API key is valid and has tile access.
  - Check the server logs for errors.
- **400 Bad Request from OWM?**
  - This usually means the tile coordinates are out of range for the zoom level. The server now auto-corrects this for TopSky.
- **Want higher resolution?**
  - Increase the zoom level in your TopSky config, but note that higher zoom covers a smaller area per tile.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Credits

- Inspired by the RainViewer API and the EuroScope TopSky plugin.
- Uses FastAPI, Pillow, and httpx.
- Weather data provided by [OpenWeatherMap](https://openweathermap.org/).
