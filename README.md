# Options Signal Bot (Massive.com version)

This bot:
- Pulls stock and options data from Massive.com
- Calculates simple technical indicators for each stock
- Picks a single call or put options contract if conditions look attractive
- Sends you an email with the recommendation

Designed to run on PythonAnywhere as a scheduled task.

## Files

- `config.py` - configuration and API keys
- `options_api.py` - Massive.com REST calls for stocks and options
- `indicators.py` - technical indicator helpers
- `signals.py` - signal logic and options selection
- `emailer.py` - email sending helper
- `main.py` - main entry point
- `requirements.txt` - Python dependencies

## Quick setup

1. Create a Massive.com account and copy your API key from the dashboard.
2. Edit `config.py` and fill in:
   - `MASSIVE_API_KEY`
   - your email SMTP info
   - tickers you care about
3. On PythonAnywhere:
   - Upload this whole folder (or zip) to your account.
   - Create a virtualenv and install `requirements.txt`.
   - Run `python main.py` once to verify it works.
   - Add a scheduled task to run `python /home/USERNAME/options-signal-bot-massive/main.py` every 15 or 30 minutes.
