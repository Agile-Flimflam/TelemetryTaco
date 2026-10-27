# Demo assets

The screenshots and walkthrough in [`docs/assets`](../assets) come from these scripts, run against a real stack. Rerun them after a UI change so the README stays current.

| Script | What it does |
|---|---|
| `demo_traffic.py` | Sends believable product events through the Python SDK: 24 hours of history, then a live stream |
| `screenshots.mjs` | `dashboard`, `insights` and `event-stream` at 1x and 2x, plus `hero.png`, a window-framed copy for social previews and portfolio pages |
| `walkthrough.mjs` | A ~15 second tour, saved as `walkthrough.mp4`, `walkthrough.webm` and `walkthrough.gif` |

You need the app running (`make dev` or `docker compose up`), Node with [Playwright](https://playwright.dev) (`npm i -g playwright && npx playwright install chromium`), and `ffmpeg` for the walkthrough.

```bash
# The demo sends far more than the default 1000 captures an hour, so raise the limit first,
# for example RATE_LIMIT_CAPTURE_EVENT=100000/h in backend/.env, and restart the API.
make seed ARGS="--clean --count 0"              # optional: start from an empty event table
PYTHONPATH=sdk python docs/demo/demo_traffic.py # leave this running

node docs/demo/screenshots.mjs http://localhost:5173 docs/assets
node docs/demo/walkthrough.mjs http://localhost:5173 docs/assets
```

The scripts shoot late in a minute, because the chart's last point is the current, partial minute and would otherwise look like a traffic drop.
