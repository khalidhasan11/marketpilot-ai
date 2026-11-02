# MarketPilot AI — Chrome Extension (Manifest V3)

## Load (unpacked, free)
1. Open `chrome://extensions` in Chrome/Chromium.
2. Enable **Developer mode** (top right).
3. Click **Load unpacked** and select this `extension/` folder.
4. Pin the extension; click it for live BTC/ETH/SOL/BNB status + top scores.

## What it does
- Popup: live prices (Binance public API, no key) + opportunity scores (EMA trend scorer).
- Options: optional backend API base, notification toggle (15-min BTC score check via service worker).
- Watchlist sync note: the extension reads the same symbol set as the web dashboard defaults; full account sync requires the backend API base to be set and the backend deployed.

## What it never does
- No API keys or credentials inside the extension.
- No interaction with Quotex or any trading page; no order placement, ever.
