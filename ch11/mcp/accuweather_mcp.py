import os
import json
from typing import Dict
from fastmcp import FastMCP
from dotenv import load_dotenv
from aiohttp import ClientSession

load_dotenv()

mcp = FastMCP("mcp-accuweather")

@mcp.tool(description="""Get weather conditions for a location""")
async def get_weather_conditions(location: str) -> Dict:
    """Get weather conditions for location"""
    api_key = os.getenv("ACCUWEATHER_API_KEY")
    base_url = "http://dataservice.accuweather.com"

    async with ClientSession() as session:
        location_search_url = f"{base_url}/locations/v1/cities/search"
        params = {
            "apikey": api_key,
            "q": location,
        }
        async with session.get(location_search_url, params=params) as response:
            locations = await response.json()
            if response.status != 200:
                raise Exception(f"""Error fetching location data: {response.status}, {locations}""")
            if not locations or len(locations) == 0:
                raise Exception("Location not found")
        location_key = locations[0]["Key"]

        current_conditions_url = f"{base_url}/currentconditions/v1/{location_key}"
        prams = {
            "apikey": "api_key",
            "details": "true"
        }
        async with session.get(current_conditions_url, params=params) as response:
            current_conditions = await response.json()
        
        if current_conditions and len(current_conditions) > 0:
            current = current_conditions[0]
            current_data = {
                "temperature": {
                    "value": current["Temperature"]["Metric"]["Value"],
                    "unit": current["Temperature"]["Metric"]["Unit"]
                },
                "weather_text": current["WeatherText"],
                "relative_humidity": current.get("RelativeHumidity"),
                "precipitation": current.get("HasPrecipitation", False),
                "observation_time": current["LocalObservationDateTime"]
            }
        else:
            current_data = "No current conditions available"

    return {
        "location": locations[0]["LocalizedName"],
        "location_key": location_key,
        "country": locations[0]["Country"]["LocalizedName"],
        "current_conditions": current_data,
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8020, path="/accu-mcp-server")