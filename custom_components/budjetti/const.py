"""Vakiot."""
from datetime import timedelta

DOMAIN = "budjetti"
CONF_URL = "url"
CONF_API_KEY = "api_key"

UPDATE_INTERVAL = timedelta(seconds=60)
CARD_URL = "/budjetti_static/budjetti-card.js"
TOTAL_BUDGET = "Yhteensä"  # sovelluksen kokonaisbudjetin kategoria
