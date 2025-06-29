# TopSky Weather Radar Bridge - Installation Guide

## Quick Start

1. **Extract** this ZIP file to any folder on your computer
2. **Get an API key** from OpenWeatherMap (free): https://openweathermap.org/api
3. **Edit** `config.ini` and replace `YOUR_API_KEY_HERE` with your actual API key
4. **Run** `topsky-wxr-bridge.exe` 
5. **Configure** TopSky to use the server (see below)

## Step-by-Step Installation

### 1. OpenWeatherMap API Key Setup

1. Go to https://openweathermap.org/api
2. Click "Get API Key" or "Sign Up"
3. Create a free account
4. Verify your email address
5. Go to your API keys page
6. Copy your API key

### 2. Configure the Application

1. Open `config.ini` in any text editor (Notepad, Notepad++, etc.)
2. Replace `YOUR_API_KEY_HERE` with your actual API key:
   ```
   api_key = your_actual_api_key_here
   ```
3. Optionally change the radar layer (default is precipitation):
   - `precipitation_new` = Rain/snow intensity
   - `clouds_new` = Cloud cover
   - `temp_new` = Temperature
   - `wind_new` = Wind speed
   - `pressure_new` = Atmospheric pressure
   - `humidity_new` = Relative humidity
4. Save the file

### 3. Run the Server

1. Double-click `topsky-wxr-bridge.exe`
2. A console window will open showing the server status
3. You should see: "Loading configuration from config.ini"
4. The server will start on http://localhost:8000
5. **Keep this window open** while using TopSky

### 4. Configure TopSky

Add these lines to your `TopSkySettings.txt` file:

```
WXR_Server=http://localhost:8000
WXR_TimeStampsURL=http://localhost:8000/public/weather-maps.json
WXR_Page_Prefix=/v2/radar/
WXR_Page_Suffix=.png
WXR_ImageSize=512
WXR_Zoom=4
```

### 5. Test the Installation

1. Open your web browser
2. Go to: http://localhost:8000/health
3. You should see a JSON response with status "healthy"
4. Start EuroScope with TopSky
5. Weather radar should now display in TopSky

## Troubleshooting

### Server Won't Start

- **"ERROR: Please edit config.ini and set your OpenWeatherMap API key"**
  - Make sure you replaced `YOUR_API_KEY_HERE` with your actual API key
  - Check that there are no extra spaces or quotes around the API key

- **Port 8000 already in use**
  - Close any other applications using port 8000
  - Or restart your computer

### No Weather Data in TopSky

- **Check the server console** for error messages
- **Verify your API key** is working: http://localhost:8000/health
- **Check TopSky settings** are exactly as shown above
- **Ensure there's actual weather** in your area on https://openweathermap.org/weathermap

### Weather Tiles Show Errors

- **Network issues**: Check your internet connection
- **API rate limits**: Free OpenWeatherMap accounts have usage limits
- **Invalid coordinates**: Make sure TopSky is configured for a valid map area

## Advanced Configuration

### Changing the Server Port

The default port is 8000. To change it, you'll need to modify the source code and rebuild the application.

### Using Different Weather Layers

Edit `config.ini` and change the `tile_layer` setting:

- `precipitation_new` - Rain and snow (recommended for aviation)
- `clouds_new` - Cloud cover percentage
- `temp_new` - Surface temperature
- `wind_new` - Wind speed
- `pressure_new` - Atmospheric pressure
- `humidity_new` - Relative humidity

## Getting Help

- **GitHub Issues**: https://github.com/jonohanekom/topsky-wxr-radar-bridge/issues
- **OpenWeatherMap API Help**: https://openweathermap.org/faq
- **TopSky Documentation**: Check your TopSky plugin documentation

## License

This software is released under the MIT License. See the project repository for full license terms.