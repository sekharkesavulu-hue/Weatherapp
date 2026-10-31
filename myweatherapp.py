import os

import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Heavy rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}


def get_current_weather(city: str) -> dict | None:
    """Look up a city and return its current conditions (Open-Meteo, no key needed)."""
    geo = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=10)
    geo.raise_for_status()
    results = geo.json().get("results")
    if not results:
        return None
    place = results[0]

    wx = requests.get(
        FORECAST_URL,
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "weather_code,wind_speed_10m",
        },
        timeout=10,
    )
    wx.raise_for_status()
    current = wx.json()["current"]
    return {
        "location": f"{place['name']}, {place.get('admin1', '')} {place.get('country', '')}".replace("  ", " ").strip(),
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity_pct": current["relative_humidity_2m"],
        "wind_kmh": current["wind_speed_10m"],
        "conditions": WEATHER_CODES.get(current["weather_code"], "Unknown"),
    }


def summarize(client: OpenAI, weather: dict) -> str:
    """Ask OpenAI to turn the raw readings into a short, friendly summary."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a friendly weather assistant. "
             "In 2-3 sentences, summarize the current weather and say what to wear."},
            {"role": "user", "content": str(weather)},
        ],
    )
    return response.choices[0].message.content


st.set_page_config(page_title="myweatherapp", page_icon="🌤️")
st.title("🌤️ myweatherapp")

THEMES = {
    "dark": {"bg": "#0e1117", "sidebar": "#1a1d24", "text": "#fafafa", "input": "#262730", "border": "#4a4d57"},
    "light": {"bg": "#ffffff", "sidebar": "#f0f2f6", "text": "#31333f", "input": "#ffffff", "border": "#d0d3da"},
}


def apply_theme(mode: str) -> None:
    """Override Streamlit's colours so the in-app toggle works regardless of the browser theme."""
    t = THEMES[mode]
    st.markdown(
        f"""
        <style>
        .stApp, [data-testid="stHeader"] {{ background-color: {t['bg']}; }}
        [data-testid="stSidebar"] {{ background-color: {t['sidebar']}; }}
        .stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3,
        .stApp span, .stApp li, [data-testid="stMetric"] *, [data-testid="stCaptionContainer"] * {{
            color: {t['text']};
        }}
        [data-testid="stTextInput"] input {{
            background-color: {t['input']}; color: {t['text']};
        }}
        [data-testid="stTextInputRootElement"] {{
            background-color: {t['input']}; border-color: {t['border']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_form():
    st.session_state["city"] = ""
    st.session_state["api_key_input"] = ""


api_key = os.getenv("OPENAI_API_KEY") or st.sidebar.text_input(
    "OpenAI API key", type="password", key="api_key_input"
)
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = getattr(st.context.theme, "type", None) == "dark"
dark_mode = st.sidebar.toggle("🌙 Dark mode", key="dark_mode")
apply_theme("dark" if dark_mode else "light")

city = st.text_input("City", placeholder="e.g. London", key="city")

st.markdown(
    """
    <style>
    .st-key-refresh_btn button {
        background-color: #2e9e4f;
        border-color: #2e9e4f;
        color: white;
    }
    .st-key-refresh_btn button:hover {
        background-color: #247d3e;
        border-color: #247d3e;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(horizontal=True, gap="xxsmall"):
    get_clicked = st.button("Get weather", type="primary")
    st.button("Refresh", key="refresh_btn", on_click=reset_form)

if get_clicked and city.strip():
    if not api_key:
        st.error("Set OPENAI_API_KEY or enter your key in the sidebar.")
        st.stop()
    try:
        with st.spinner("Fetching weather..."):
            weather = get_current_weather(city.strip())
            if weather is None:
                st.warning(f"Couldn't find a city named '{city}'.")
                st.stop()
            summary = summarize(OpenAI(api_key=api_key), weather)
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.stop()

    st.subheader(weather["location"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temperature", f"{weather['temperature_c']} °C")
    c2.metric("Feels like", f"{weather['feels_like_c']} °C")
    c3.metric("Humidity", f"{weather['humidity_pct']} %")
    c4.metric("Wind", f"{weather['wind_kmh']} km/h")
    st.caption(f"Conditions: {weather['conditions']}")
    st.info(summary)
