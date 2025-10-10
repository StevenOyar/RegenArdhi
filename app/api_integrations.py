"""
RegenArdhi - Comprehensive API Integrations Module (improved)
Handles all external API calls and data processing
Improvements:
- Robust HTTP calls with retries and backoff
- Correct chronological ordering of NASA POWER timeseries
- Resilient Hugging Face querying with model fallbacks and error logging
- Defensive handling when APIs return None/empty data
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import math
import traceback

load_dotenv()

# ========================
# API CONFIGURATIONS
# ========================

# NASA POWER API (Free - Climate & Solar Data)
NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_API_KEY = os.getenv('NASA_POWER_API_KEY', 'DEMO_KEY')

# OpenWeather API (Weather Data)
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Hugging Face API (AI/ML Models)
HUGGINGFACE_BASE_URL = "https://api-inference.huggingface.co/models"
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

# OpenStreetMap Nominatim (Geocoding - Free)
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"

# Open-Elevation API (Elevation Data - Free)
ELEVATION_BASE_URL = "https://api.open-elevation.com/api/v1"

# A shared requests session and default headers
DEFAULT_HEADERS = {'User-Agent': 'RegenArdhi/1.0 (Land Restoration Platform)'}
SESSION = requests.Session()


# ------------------------
# Helper: robust request
# ------------------------
def _http_get(url, params=None, headers=None, timeout=15, retries=3, backoff_factor=0.5):
    headers = {**DEFAULT_HEADERS, **(headers or {})}
    attempt = 0
    while attempt < retries:
        try:
            resp = SESSION.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp
            # Retry on common transient server errors and 429 (rate limit)
            if resp.status_code in (429, 500, 502, 503, 504):
                attempt += 1
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_time)
                continue
            # For 4xx other than 429, return the response so caller can inspect
            return resp
        except requests.RequestException as e:
            attempt += 1
            time.sleep(backoff_factor * (2 ** (attempt - 1)))
            last_exc = e
    # If we exhausted retries, raise last exception or return None
    try:
        return resp  # last response if present
    except UnboundLocalError:
        raise last_exc


def _http_post(url, json_payload=None, headers=None, timeout=30, retries=3, backoff_factor=0.5):
    headers = {**DEFAULT_HEADERS, **(headers or {})}
    attempt = 0
    while attempt < retries:
        try:
            resp = SESSION.post(url, headers=headers, json=json_payload, timeout=timeout)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                attempt += 1
                time.sleep(backoff_factor * (2 ** (attempt - 1)))
                continue
            return resp
        except requests.RequestException as e:
            attempt += 1
            time.sleep(backoff_factor * (2 ** (attempt - 1)))
            last_exc = e
    try:
        return resp
    except UnboundLocalError:
        raise last_exc


# ========================
# CLIMATE DATA APIs
# ========================

class NASAPowerAPI:
    """
    NASA POWER API Integration
    Provides historical and real-time climate data
    """

    @staticmethod
    def get_climate_data(latitude, longitude, start_date, end_date):
        try:
            params = {
                'parameters': 'T2M,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN',
                'community': 'AG',
                'longitude': longitude,
                'latitude': latitude,
                'start': start_date.strftime('%Y%m%d'),
                'end': end_date.strftime('%Y%m%d'),
                'format': 'JSON'
            }
            response = _http_get(NASA_POWER_BASE_URL, params=params, timeout=30)
            if response is None:
                print("NASA POWER: no response (network error).")
                return None
            if response.status_code == 200:
                data = response.json()
                return NASAPowerAPI._process_climate_data(data)
            else:
                print(f"NASA POWER API error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"Error fetching NASA POWER data: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def _process_climate_data(raw_data):
        """Process NASA POWER API response and ensure chronological ordering"""
        try:
            parameters = raw_data.get('properties', {}).get('parameter', {})
            if not parameters:
                print("NASA POWER: empty 'parameter' in response.")
                return None

            # We'll sort dates so values and 'current' come from the latest date
            def ordered_series(param_name):
                series = parameters.get(param_name, {})
                if not series:
                    return [], []
                # keys are date strings like '20220101' - sort them ascending
                items = sorted(series.items(), key=lambda kv: kv[0])
                dates = [k for k, v in items]
                values = [v for k, v in items]
                return dates, values

            dates_t2m, temps = ordered_series('T2M')
            _, rainfall = ordered_series('PRECTOTCORR')
            _, humidity = ordered_series('RH2M')
            _, wind_speed = ordered_series('WS2M')
            _, solar_rad = ordered_series('ALLSKY_SFC_SW_DWN')

            # safe stats
            def safe_stats(arr):
                if not arr:
                    return {'avg': 0, 'min': 0, 'max': 0, 'current': 0}
                return {'avg': sum(arr) / len(arr), 'min': min(arr), 'max': max(arr), 'current': arr[-1]}

            result = {
                'temperature': safe_stats(temps),
                'rainfall': {
                    'total': sum(rainfall) if rainfall else 0,
                    'avg_daily': (sum(rainfall) / len(rainfall)) if rainfall else 0,
                    'days_with_rain': sum(1 for r in rainfall if r is not None and r > 0)
                },
                'humidity': {
                    'avg': sum(humidity) / len(humidity) if humidity else 0,
                    'current': humidity[-1] if humidity else 0
                },
                'wind_speed': {
                    'avg': sum(wind_speed) / len(wind_speed) if wind_speed else 0
                },
                'solar_radiation': {
                    'avg': sum(solar_rad) / len(solar_rad) if solar_rad else 0
                },
                'time_series': {
                    'dates': dates_t2m,
                    'temperature': temps,
                    'rainfall': rainfall,
                    'humidity': humidity,
                    'wind_speed': wind_speed,
                    'solar_radiation': solar_rad
                }
            }
            return result
        except Exception as e:
            print(f"Error processing NASA POWER data: {e}")
            traceback.print_exc()
            return None


class OpenWeatherAPI:
    """
    OpenWeather API Integration
    Provides current weather and forecast data
    """

    @staticmethod
    def get_current_weather(latitude, longitude):
        """Get current weather conditions"""
        try:
            if not OPENWEATHER_API_KEY:
                print("OpenWeather warning: API key not set, using fallback estimator.")
                return OpenWeatherAPI._get_fallback_weather(latitude, longitude)

            url = f"{OPENWEATHER_BASE_URL}/weather"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': OPENWEATHER_API_KEY,
                'units': 'metric'
            }
            response = _http_get(url, params=params, timeout=10)
            if response is None:
                return OpenWeatherAPI._get_fallback_weather(latitude, longitude)

            if response.status_code == 200:
                data = response.json()
                return {
                    'temperature': round(data['main']['temp'], 1),
                    'feels_like': round(data['main'].get('feels_like', data['main']['temp']), 1),
                    'humidity': data['main'].get('humidity', 0),
                    'pressure': data['main'].get('pressure', 0),
                    'description': data.get('weather', [{}])[0].get('description', ''),
                    'wind_speed': data.get('wind', {}).get('speed', 0),
                    'clouds': data.get('clouds', {}).get('all', 0),
                    'visibility': (data.get('visibility', 10000) / 1000) if data.get('visibility') is not None else 10,
                    'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).isoformat() if data.get('sys') else None,
                    'sunset': datetime.fromtimestamp(data['sys']['sunset']).isoformat() if data.get('sys') else None
                }
            else:
                print(f"OpenWeather API returned {response.status_code}: {getattr(response,'text', '')[:200]}")
                return OpenWeatherAPI._get_fallback_weather(latitude, longitude)
        except Exception as e:
            print(f"Error fetching OpenWeather data: {e}")
            traceback.print_exc()
            return OpenWeatherAPI._get_fallback_weather(latitude, longitude)

    @staticmethod
    def _get_fallback_weather(latitude, longitude):
        """Fallback weather estimation"""
        abs_lat = abs(latitude)
        base_temp = 30 - (abs_lat * 0.6)
        # keep temp within realistic range
        base_temp = max(min(base_temp, 45), -20)

        if abs_lat < 23.5:
            humidity = 70 + (abs(longitude) % 20)
        else:
            humidity = 50 + (abs(longitude) % 30)

        return {
            'temperature': round(base_temp, 1),
            'feels_like': round(base_temp + 2, 1),
            'humidity': int(humidity),
            'pressure': 1013,
            'description': 'estimated',
            'wind_speed': 0,
            'clouds': 50,
            'visibility': 10,
            'sunrise': datetime.now().replace(hour=6, minute=0).isoformat(),
            'sunset': datetime.now().replace(hour=18, minute=0).isoformat()
        }


# ========================
# GEOCODING APIs
# ========================

class NominatimAPI:
    @staticmethod
    def reverse_geocode(latitude, longitude):
        try:
            url = f"{NOMINATIM_BASE_URL}/reverse"
            params = {'lat': latitude, 'lon': longitude, 'format': 'json', 'zoom': 10}
            headers = {'User-Agent': 'RegenArdhi/1.0 (Land Restoration Platform)'}
            response = _http_get(url, params=params, headers=headers, timeout=10)
            if response and response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                parts = []
                if address.get('town') or address.get('city'):
                    parts.append(address.get('town') or address.get('city'))
                if address.get('county'):
                    parts.append(address.get('county'))
                if address.get('state'):
                    parts.append(address.get('state'))
                if address.get('country'):
                    parts.append(address.get('country'))
                return ', '.join(parts) if parts else f"{latitude:.4f}, {longitude:.4f}"
            return f"{latitude:.4f}, {longitude:.4f}"
        except Exception as e:
            print(f"Error in reverse geocoding: {e}")
            traceback.print_exc()
            return f"{latitude:.4f}, {longitude:.4f}"

    @staticmethod
    def geocode(address):
        try:
            url = f"{NOMINATIM_BASE_URL}/search"
            params = {'q': address, 'format': 'json', 'limit': 1}
            headers = {'User-Agent': 'RegenArdhi/1.0 (Land Restoration Platform)'}
            response = _http_get(url, params=params, headers=headers, timeout=10)
            if response and response.status_code == 200:
                data = response.json()
                if data:
                    return {'latitude': float(data[0]['lat']), 'longitude': float(data[0]['lon']), 'display_name': data[0]['display_name']}
            return None
        except Exception as e:
            print(f"Error in geocoding: {e}")
            traceback.print_exc()
            return None


class ElevationAPI:
    @staticmethod
    def get_elevation(latitude, longitude):
        try:
            url = f"{ELEVATION_BASE_URL}/lookup"
            params = {'locations': f"{latitude},{longitude}"}
            response = _http_get(url, params=params, timeout=10)
            if response and response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0].get('elevation', 0)
            return 0
        except Exception as e:
            print(f"Error getting elevation: {e}")
            traceback.print_exc()
            return 0


# ========================
# AI/ML APIs
# ========================

class HuggingFaceAPI:
    """
    Hugging Face API Integration
    More robust: will try model fallbacks and log response bodies when not 200
    """

    MODELS = {
        'chat': 'microsoft/DialoGPT-large',
        'text_generation': 'gpt2',
        'sentiment': 'distilbert-base-uncased-finetuned-sst-2-english',
        'summarization': 'facebook/bart-large-cnn'
    }

    @staticmethod
    def query_model(prompt, model='chat', max_length=300, temperature=0.7):
        try:
            if not HUGGINGFACE_API_KEY:
                print("HuggingFace warning: API key not set.")
                return None

            # Build an ordered list of candidate models: requested type -> fallbacks
            candidates = []
            requested_model = HuggingFaceAPI.MODELS.get(model)
            if requested_model:
                candidates.append(requested_model)
            # add other obvious fallbacks
            for m in HuggingFaceAPI.MODELS.values():
                if m not in candidates:
                    candidates.append(m)

            headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
            payload = {"inputs": prompt, "parameters": {"max_length": max_length, "temperature": temperature, "top_p": 0.9, "do_sample": True}}

            for model_name in candidates:
                url = f"{HUGGINGFACE_BASE_URL}/{model_name}"
                try:
                    resp = _http_post(url, json_payload=payload, headers=headers, timeout=30)
                    if resp is None:
                        continue
                    if resp.status_code == 200:
                        result = resp.json()
                        # Many HF text models return list[{'generated_text': ...}]
                        if isinstance(result, list) and result and isinstance(result[0], dict):
                            gen = result[0].get('generated_text') or result[0].get('generated_text', '')
                            # if HF returns continuation including prompt, remove prompt if present
                            if isinstance(gen, str) and prompt and gen.startswith(prompt):
                                gen = gen[len(prompt):].strip()
                            return gen.strip()
                        # Some models return dict or other structures
                        if isinstance(result, dict) and 'generated_text' in result:
                            gen = result['generated_text']
                            if isinstance(gen, str) and prompt and gen.startswith(prompt):
                                gen = gen[len(prompt):].strip()
                            return gen.strip()
                        return str(result)
                    else:
                        # Log body for debugging; 404 often means model not hosted for inference-api
                        print(f"Hugging Face model {model_name} returned {resp.status_code}: {resp.text[:400]}")
                        # try next candidate
                except Exception as e:
                    print(f"Error querying Hugging Face model {model_name}: {e}")
                    traceback.print_exc()
                    continue

            print("Hugging Face: all candidate models failed or returned non-200.")
            return None
        except Exception as e:
            print(f"Error querying Hugging Face: {e}")
            traceback.print_exc()
            return None


# ========================
# COMPREHENSIVE DATA SERVICE
# ========================

class LandAnalysisService:
    @staticmethod
    def analyze_location(latitude, longitude, area_hectares):
        try:
            print(f"🔍 Starting comprehensive analysis for {latitude}, {longitude}")

            # 1. Location
            location_name = NominatimAPI.reverse_geocode(latitude, longitude)
            print(f"✓ Location: {location_name}")

            # 2. Weather
            weather = OpenWeatherAPI.get_current_weather(latitude, longitude)
            print(f"✓ Weather: {weather.get('temperature')}°C, {weather.get('humidity')}% humidity")

            # 3. Climate history
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            climate_history = NASAPowerAPI.get_climate_data(latitude, longitude, start_date, end_date)
            if climate_history is None:
                print("⚠️ NASA POWER returned no climate history; proceeding with available data.")
            else:
                print("✓ Climate history retrieved")

            # 4. Elevation
            elevation = ElevationAPI.get_elevation(latitude, longitude)
            print(f"✓ Elevation: {elevation}m")

            # 5. NDVI estimate (robust to missing climate_history)
            ndvi = LandAnalysisService._estimate_ndvi(latitude, longitude, weather, climate_history)
            print(f"✓ NDVI estimate: {ndvi}")

            # 6. Climate zone
            climate_zone = LandAnalysisService._determine_climate_zone(latitude, weather.get('temperature', 20))
            print(f"✓ Climate zone: {climate_zone}")

            # 7. Soil type
            soil_type = LandAnalysisService._analyze_soil_type(latitude, longitude, elevation)
            print(f"✓ Soil type: {soil_type}")

            # 8. Soil pH
            soil_ph = LandAnalysisService._calculate_soil_ph(soil_type, weather or {})
            print(f"✓ Soil pH: {soil_ph}")

            # 9. Annual rainfall estimate
            annual_rainfall = LandAnalysisService._estimate_annual_rainfall(climate_zone, weather.get('humidity', 50), longitude)
            print(f"✓ Annual rainfall: {annual_rainfall}mm")

            # 10. Degradation assessment
            degradation_level = LandAnalysisService._assess_degradation(ndvi, soil_ph, area_hectares)
            print(f"✓ Degradation level: {degradation_level}")

            # 11. Recommendations
            recommendations = LandAnalysisService._generate_recommendations(climate_zone, soil_type, soil_ph, degradation_level, annual_rainfall)
            print(f"✓ Recommendations generated")

            analysis = {
                'location_name': location_name,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation,
                'current_weather': weather,
                'climate_history': climate_history,
                'climate_zone': climate_zone,
                'annual_rainfall': annual_rainfall,
                'soil_type': soil_type,
                'soil_ph': soil_ph,
                'soil_fertility': LandAnalysisService._calculate_fertility(soil_ph, ndvi),
                'vegetation_index': ndvi,
                'land_degradation_level': degradation_level,
                'recommended_crops': recommendations['crops'],
                'recommended_trees': recommendations['trees'],
                'restoration_techniques': recommendations['techniques'],
                'estimated_timeline_months': recommendations['timeline_months'],
                'estimated_budget': recommendations['budget_per_hectare'] * area_hectares
            }

            print("✅ Analysis complete!")
            return analysis
        except Exception as e:
            print(f"❌ Error in comprehensive analysis: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def _estimate_ndvi(latitude, longitude, weather, climate_history):
        try:
            abs_lat = abs(latitude)
            temp = weather.get('temperature', 20) if weather else 20
            humidity = weather.get('humidity', 50) if weather else 50

            if abs_lat < 10:
                base_ndvi = 0.6
            elif abs_lat < 23.5:
                base_ndvi = 0.5
            elif abs_lat < 35:
                base_ndvi = 0.4
            elif abs_lat < 50:
                base_ndvi = 0.35
            else:
                base_ndvi = 0.2

            if temp > 25 and humidity > 60:
                base_ndvi += 0.1
            elif temp < 10 or humidity < 30:
                base_ndvi -= 0.15

            variation = (abs(longitude) % 10) * 0.02
            ndvi = max(0.0, min(1.0, base_ndvi + variation - 0.1))

            # If there is real climate history and it includes a temperature time_series,
            # bias NDVI slightly up or down based on recent temp anomalies (simple heuristic)
            try:
                if climate_history and isinstance(climate_history.get('time_series', {}).get('temperature', []), list):
                    temps = climate_history['time_series']['temperature']
                    if temps:
                        recent = temps[-1]
                        mean_recent = sum(temps) / len(temps)
                        if recent > mean_recent + 2:
                            ndvi = min(1.0, ndvi + 0.03)
                        elif recent < mean_recent - 2:
                            ndvi = max(0.0, ndvi - 0.03)
            except Exception:
                pass

            return round(ndvi, 2)
        except Exception as e:
            print(f"Error estimating NDVI: {e}")
            traceback.print_exc()
            return 0.0

    # (rest of helper methods are unchanged except defensive get() usage)
    @staticmethod
    def _determine_climate_zone(latitude, temperature):
        abs_lat = abs(latitude)
        if abs_lat > 66.5:
            return "Polar"
        elif abs_lat > 60:
            return "Subpolar"
        elif abs_lat > 45:
            return "Warm Temperate" if temperature > 20 else "Cool Temperate"
        elif abs_lat > 30:
            return "Subtropical" if temperature > 25 else "Warm Temperate"
        elif abs_lat > 23.5:
            return "Tropical"
        else:
            return "Equatorial"

    @staticmethod
    def _analyze_soil_type(latitude, longitude, elevation):
        abs_lat = abs(latitude)
        if elevation > 2000:
            soil_types = ["Rocky", "Mountain Soil", "Thin Soil"]
        elif elevation > 1000:
            soil_types = ["Loamy", "Clay-Loam", "Sandy-Loam"]
        else:
            if abs_lat < 10:
                soil_types = ["Laterite", "Tropical Red", "Alluvial"]
            elif abs_lat < 30:
                soil_types = ["Alluvial", "Loamy", "Red Soil"]
            elif abs_lat < 50:
                soil_types = ["Loamy", "Clay", "Podzol"]
            else:
                soil_types = ["Tundra", "Permafrost", "Gleysol"]
        index = int(abs(longitude)) % len(soil_types) if soil_types else 0
        return soil_types[index]

    @staticmethod
    def _calculate_soil_ph(soil_type, weather):
        base_ph = {
            "Laterite": 5.5, "Tropical Red": 6.0, "Alluvial": 7.0,
            "Loamy": 6.5, "Clay": 7.2, "Sandy": 6.8, "Rocky": 7.5,
            "Mountain Soil": 6.3, "Podzol": 5.0, "Tundra": 5.5
        }
        ph = base_ph.get(soil_type, 6.5)
        humidity = weather.get('humidity', 50) if weather else 50
        if humidity > 70:
            ph -= 0.3
        elif humidity < 40:
            ph += 0.3
        return round(ph, 1)

    @staticmethod
    def _calculate_fertility(soil_ph, ndvi):
        if 6.0 <= soil_ph <= 7.5 and ndvi > 0.5:
            return "high"
        elif (5.5 <= soil_ph < 6.0 or 7.5 < soil_ph <= 8.0) and ndvi > 0.35:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _estimate_annual_rainfall(climate_zone, humidity, longitude):
        base_rainfall = {
            "Equatorial": 2500, "Tropical": 1800, "Subtropical": 1000,
            "Warm Temperate": 800, "Cool Temperate": 700,
            "Subpolar": 500, "Polar": 250
        }
        rainfall = base_rainfall.get(climate_zone, 800)
        if humidity > 70:
            rainfall *= 1.3
        elif humidity < 40:
            rainfall *= 0.6
        variation = (abs(longitude) % 15) * 20
        rainfall += variation
        return int(rainfall)

    @staticmethod
    def _assess_degradation(ndvi, soil_ph, area_hectares):
        score = 0
        if ndvi < 0.2:
            score += 4
        elif ndvi < 0.35:
            score += 3
        elif ndvi < 0.5:
            score += 2
        else:
            score += 1
        if soil_ph < 5.0 or soil_ph > 8.5:
            score += 1
        if area_hectares > 100:
            score += 1
        if score >= 5:
            return "critical"
        elif score >= 4:
            return "severe"
        elif score >= 2:
            return "moderate"
        else:
            return "minimal"

    @staticmethod
    def _generate_recommendations(climate_zone, soil_type, soil_ph, degradation, rainfall):
        crops_db = {
            "Equatorial": ["Rice", "Bananas", "Cassava", "Yams", "Cocoa", "Coffee"],
            "Tropical": ["Maize", "Beans", "Cassava", "Sweet Potato", "Millet", "Sorghum"],
            "Subtropical": ["Wheat", "Maize", "Citrus", "Grapes", "Cotton", "Rice"],
            "Warm Temperate": ["Wheat", "Barley", "Potato", "Apple", "Cherry", "Corn"],
            "Cool Temperate": ["Oats", "Barley", "Potato", "Cabbage", "Berries", "Rye"]
        }
        trees_db = {
            "Equatorial": ["Mahogany", "Teak", "Rubber", "Oil Palm", "Bamboo"],
            "Tropical": ["Acacia", "Neem", "Mango", "Moringa", "Grevillea", "Eucalyptus"],
            "Subtropical": ["Oak", "Citrus", "Olive", "Pine", "Cypress"],
            "Warm Temperate": ["Oak", "Maple", "Ash", "Pine", "Walnut"],
            "Cool Temperate": ["Spruce", "Fir", "Birch", "Alder", "Larch"]
        }
        techniques_db = {
            "minimal": [
                "Regular mulching and organic matter addition",
                "Crop rotation practices",
                "Water conservation techniques"
            ],
            "moderate": [
                "Contour farming and terracing",
                "Agroforestry integration",
                "Soil amendment with compost",
                "Cover cropping"
            ],
            "severe": [
                "Intensive afforestation program",
                "Deep tillage and soil loosening",
                "Watershed management systems",
                "Biochar application"
            ],
            "critical": [
                "Emergency restoration protocols",
                "Comprehensive soil remediation",
                "Intensive irrigation system installation",
                "Professional consultation required"
            ]
        }
        timeline_map = {"minimal": 12, "moderate": 24, "severe": 36, "critical": 48}
        budget_map = {"minimal": 50000, "moderate": 150000, "severe": 350000, "critical": 700000}
        budget = budget_map.get(degradation, 100000)
        if rainfall < 600:
            budget *= 1.5
        return {
            'crops': crops_db.get(climate_zone, ["Consult agronomist"])[:5],
            'trees': trees_db.get(climate_zone, ["Consult forester"])[:5],
            'techniques': techniques_db.get(degradation, []),
            'timeline_months': timeline_map.get(degradation, 24),
            'budget_per_hectare': round(budget, 2)
        }


# ========================
# EXPORT ALL
# ========================

__all__ = [
    'NASAPowerAPI',
    'OpenWeatherAPI',
    'NominatimAPI',
    'ElevationAPI',
    'HuggingFaceAPI',
    'LandAnalysisService'
]
