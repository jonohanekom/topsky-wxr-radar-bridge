TopSky Weather Radar Bridge v1.0.0
===================================

Thank you for downloading TopSky Weather Radar Bridge!

QUICK START:
1. Get a free API key from: https://openweathermap.org/api
2. Edit config.ini and add your API key
3. Run topsky-wxr-bridge.exe
4. Configure TopSky to use http://localhost:8000

FILES INCLUDED:
- topsky-wxr-bridge.exe = Main application
- config.ini = Configuration file (EDIT THIS!)
- INSTALL.md = Detailed installation guide
- README.txt = This file

TOPSKY CONFIGURATION:
Add these lines to your TopSkySettings.txt:

WXR_Server=http://localhost:8000
WXR_TimeStampsURL=http://localhost:8000/public/weather-maps.json
WXR_Page_Prefix=/v2/radar/
WXR_Page_Suffix=.png
WXR_ImageSize=512
WXR_Zoom=4

IMPORTANT NOTES:
- You MUST edit config.ini before running
- Keep the console window open while using TopSky
- This application requires an internet connection
- Free OpenWeatherMap accounts have usage limits

NEED HELP?
Read INSTALL.md for detailed instructions or visit:
https://github.com/jonohanekom/topsky-wxr-radar-bridge

Happy flying!