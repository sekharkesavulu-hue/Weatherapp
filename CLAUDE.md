# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
source .venv/bin/activate          # venv lives in .venv
pip install -r requirements.txt
streamlit run myweatherapp.py      # run the app
```

There are no tests or linter configured. Python 3.10+ is required (`dict | None` syntax). `OPENAI_API_KEY` is read from `.env` (git-ignored); if unset, the app shows a sidebar key field instead.

## Architecture

The whole app is a single script, `myweatherapp.py`, that Streamlit re-executes top to bottom on every interaction. There are no modules or classes.

- **Data layer:** `get_current_weather()` calls Open-Meteo geocoding then forecast (no key needed) and returns a flat dict, or `None` if the city isn't found. `WEATHER_CODES` maps WMO codes to text. `summarize()` sends that dict to OpenAI (`gpt-4o-mini`) for a short summary and clothing suggestion.
- **UI layer:** the rest of the file is the Streamlit page. Results render only on the run in which "Get weather" was clicked (`get_clicked`), so any other interaction, such as toggling dark mode, clears the displayed result.

## Streamlit gotchas specific to this app

- **Widget state:** the City and API key inputs and the dark-mode toggle are bound to `st.session_state` keys (`city`, `api_key_input`, `dark_mode`). The Refresh button resets the first two through an `on_click` callback (`reset_form`). Widget-bound state can only be modified in a callback or before the widget is created, so keep resets there. Refresh deliberately does not touch `dark_mode`.
- **Theming:** Streamlit has no runtime theme API, so `apply_theme()` injects CSS overrides built from the `THEMES` palettes. The initial toggle value comes from `st.context.theme.type`. If you add new widgets, check that they stay readable in both modes.
- **Button colours:** the green Refresh button is styled through its `.st-key-refresh_btn` container class (from `key="refresh_btn"`). Don't remove the key, or the styling breaks.
