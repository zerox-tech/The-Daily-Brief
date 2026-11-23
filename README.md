# The Daily Brief – your personal news agent

A news app that works like a mini WSJ / NYT front page on your phone and laptop.

- **Sections:** Top, World, Pakistan, Finance, Sports, Tech
- **Outlets:** BBC, NYT, WSJ, Al Jazeera, The Guardian, CNBC, ESPN, ESPNcricinfo, Dawn, Express Tribune, The News, Geo
- **Agent features:** pulls feeds in parallel, removes duplicate stories (same story from many outlets shows once, with "+N more"), sorts newest first, optional AI briefing per section
- **Search + filter by outlet**, light/dark mode, installable like an app, works offline with the last copy

## How it works

```
fetch_news.py  ──►  news.json  ──►  index.html (the website)
 (the agent)       (the data)       (phone + laptop)
```

`fetch_news.py` reads `feeds.json` (the list of outlets) and writes `news.json`. The website just displays it.
To add or remove an outlet, edit `feeds.json` – no code changes needed.
If a feed is down or has moved, the agent skips it and carries on.

## Try it on your laptop (2 minutes)

```
pip install -r requirements.txt
python fetch_news.py
python -m http.server 8000
```

Open http://localhost:8000

## Get it on your phone too (free, updates itself every hour)

1. Create a free account on github.com and make a **new public repository** (e.g. `daily-brief`).
2. Upload everything in this folder, **including the hidden `.github` folder**, to the repo.
3. In the repo go to **Settings → Pages**, set Source to **Deploy from a branch**, branch `main`, folder `/ (root)`, and save.
4. Go to the **Actions** tab, open **Update news**, click **Run workflow**. It now refreshes every hour on its own.
5. After a minute or two your site is live at `https://YOUR-USERNAME.github.io/daily-brief/`.
6. Open that link on your phone:
   - **Android (Chrome):** menu → *Add to Home screen* / *Install app*
   - **iPhone (Safari):** Share → *Add to Home Screen*
   - **Laptop (Chrome/Edge):** click the install icon in the address bar

## Optional: AI briefing

Each section can show a 3-bullet "AI BRIEFING" written by Claude from the latest headlines.

1. Get an API key from console.anthropic.com (API use is billed separately from a Claude chat plan, and Haiku keeps the cost very low).
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**, name it `ANTHROPIC_API_KEY`.

Without a key everything still works; you just won't see the briefing box.

## Notes

- Feeds show headlines and short summaries and link to the original article. Paywalled sites (WSJ, NYT) will still ask you to subscribe to read the full story.
- Publishers sometimes change their feed addresses. If an outlet stops appearing, check the Actions log and update its URL in `feeds.json`.
