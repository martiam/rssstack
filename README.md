# RSSStack
A dockerised solution for scraping a single twitter list, serving it as a RSSFeed and saving it to a local database.

# 🐳 Twitter List RSS Stack

This project sets up a self-hosted system to monitor Twitter Lists via RSS using Docker Compose. It consists of three main containers:

- **RSSHub**: Fetches tweets from Twitter Lists using Twitter cookies.
- **FreshRSS**: Aggregates and stores tweet updates from RSSHub.
- **Cookiebot**: Automatically logs into Twitter and refreshes cookies used by RSSHub.

## 🧱 Containers

---

### 1. 🚀 RSSHub

**Image**: [`diygod/rsshub:latest`](https://github.com/DIYgod/RSSHub)  
**Purpose**: Fetches Twitter List content and exposes it as RSS.

**Key Details**:
- Reads authentication cookies (`auth_token`, `ct0`) from `shared/auth.env`.
- Supports `ACCESS_KEY` and `CACHE_EXPIRE` configuration.
- Protected by Traefik reverse proxy.
- Only restarts when explicitly told to (e.g., when new cookies are available).

---

### 2. 📖 FreshRSS

**Image**: [`freshrss/freshrss`](https://github.com/FreshRSS/FreshRSS)  
**Purpose**: A lightweight, web-based RSS reader.

**Key Details**:
- Periodically polls RSSHub for new tweets every 20 minutes.
- Stores fetched tweets in a persistent SQLite database volume.
- Access via web UI using Traefik reverse proxy.

---

### 3. 🍪 Cookiebot

**Image**: Custom (uses Playwright)  
**Purpose**: Headless browser that logs into Twitter using provided credentials and refreshes `auth_token`.

**Key Details**:
- Rewrites `shared/auth.env` with fresh cookies.
- Optionally restarts RSSHub using Docker API or `docker compose`.
- Can detect RSSHub errors and retry if 503 is encountered.
- Screenshot and debug support via X11 forwarding and Playwright.

---

## 🔐 Environment Configuration (`.env`)

```env
# Twitter credentials
X_USER=your_email@domain.com
X_PASS=your_password

# Auth token and cookie (auto-refreshed by Cookiebot)
TWITTER_AUTH_TOKEN=...
TWITTER_COOKIE=...

# RSSHub access
ACCESS_KEY=your_rsshub_key
CACHE_EXPIRE=600

# mail.tm API token (optional for 2FA), needs to be implemented using a function fetch_cookie.py from the cookiebot container
MAIL_TOKEN=...
```

Origally located in /opt/rssstack running on a VPS.

# Dependencies
- docker

# Run with
```docker compose up -d```