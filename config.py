"""
Configuration for the options signal bot using Massive.com data.
Edit the values in this file before running.
"""

import os

# Massive.com API configuration
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY", "7uOSedbH7wbqyivzocKfjhKX_cosJ_eC")
MASSIVE_BASE_URL = "https://api.massive.com"

# Tickers to scan
TICKERS = ["AAPL", "NVDA", "AMZN", "META", "MSFT", "TSLA", "GOOG", "WDC"]

# Technical indicator parameters
LOOKBACK_DAYS = 90  # how many calendar days of history to pull
MA_SHORT = 10       # short moving average length (trading days)
MA_LONG = 20        # long moving average length
RSI_PERIOD = 14

# Options filters
MIN_DTE = 10        # minimum days to expiration
MAX_DTE = 60        # maximum days to expiration
TARGET_DELTA_CALL = 0.35
TARGET_DELTA_PUT = -0.35
MIN_OPEN_INTEREST = 100

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "thedanielkopp@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "lmed tzkp hbbg hoen")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)
EMAIL_TO = [addr.strip() for addr in os.getenv("EMAIL_TO", EMAIL_FROM).split(",")]

# Misc
DEBUG = bool(int(os.getenv("DEBUG", "0")))
TIMEOUT_SECONDS = 10
