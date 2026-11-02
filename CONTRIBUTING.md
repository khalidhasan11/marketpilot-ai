# Contributing

1. Fork / branch from `main`, keep commits meaningful and scoped per change.
2. Run `pytest backend/tests/ -q` and `node --check frontend/app.js` before pushing.
3. No secrets in code — `.env` only (gitignored). No fabricated data, ever: if a
   provider needs a key, surface `requires_api_key`; do not mock a response.
4. New indicators need known-value unit tests and a no-look-ahead check.
5. UI text is English only; every control must do something real or be removed.
