"""Vakiot."""
from datetime import timedelta

DOMAIN = "budjetti"
CONF_URL = "url"
CONF_API_KEY = "api_key"

UPDATE_INTERVAL = timedelta(seconds=60)
CARD_URL = "/budjetti_static/budjetti-card.js"
TOTAL_BUDGET = "Yhteensä"  # sovelluksen kokonaisbudjetin kategoria

CONF_LARGE_EXPENSE = "large_expense_eur"
DEFAULT_LARGE_EXPENSE = 100  # euroa; 0 = ei tapahtumaa

# Home Assistant -tapahtumat automaatioille
EVENT_BUDGET_THRESHOLD = "budjetti_budget_threshold"
EVENT_LARGE_EXPENSE = "budjetti_large_expense"
BUDGET_THRESHOLDS = (80, 100)
