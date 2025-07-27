# cookiebot/fetch_cookie.py  – verbose version
import os, re, sys, time, random, subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError
import requests

# ── CONFIG ──────────────────────────────────────────────────────────
AUTH_FILE  = os.environ.get("AUTH_FILE", "/shared/auth.env")
EMAIL      = os.environ["X_USER"]          # e-mail or phone
USERNAME   = "username"              # shown on “confirm username” step
PASSWORD   = os.environ["X_PASS"]
ENV_PATH   = os.environ["RSS_ENV"]         # .env file to rewrite
RSS_NAME   = os.environ["RSS_CONTAINER"]   # docker service name
MAX_RETRY  = 5
BACKOFF    = [60, 300, 900, 1800, 3600]    # 1 min → 60 min
PWD_SELECT = [
    'input[autocapitalize="sentences"]',
    'input[autocomplete="current-password"]'
]
# ────────────────────────────────────────────────────────────────────

def log(msg):
    """
    Logs a message with a UTC timestamp to stderr.

    Args:
        msg (str): The message to log.

    Example:
        log("Starting process") -> "[cookiebot 2025-07-27 12:34:56] Starting process"
    """
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[cookiebot {ts}] {msg}", file=sys.stderr, flush=True)

def screenshot(page, tag):
    """
    Takes a full-page screenshot of the current page state.

    Args:
        page (Page): The Playwright page object to screenshot.
        tag (str): A identifier tag for the screenshot filename.

    Returns:
        None. Saves screenshot to /tmp directory with filename format:
        cookiebot_{tag}_{timestamp}.png
    """
    fname = f"/tmp/cookiebot_{tag}_{int(time.time())}.png"
    page.screenshot(path=fname, full_page=True)
    log(f"screenshot saved: {fname}")

def update_auth_file(auth, ct0):
    """
    Updates the authentication file with new Twitter auth token and cookie.

    Args:
        auth (str): The Twitter authentication token.
        ct0 (str): The Twitter ct0 cookie value.

    Returns:
        None. Updates the file specified in AUTH_FILE environment variable.
    """
    content = f"TWITTER_AUTH_TOKEN={auth}\n"
    content += f"TWITTER_COOKIE=auth_token={auth}; ct0={ct0}\n"
    with open(AUTH_FILE, "w") as f:
        f.write(content)
    log(f"Updated auth file at {AUTH_FILE}")

def wait_password(page):
    """
    Waits for any of the password field selectors to become visible on the page.

    Args:
        page (Page): The Playwright page object to check.

    Returns:
        str|None: The selector that became visible, or None if no selector was found
        within the timeout period.
    """
    for sel in PWD_SELECT:
        try:
            page.wait_for_selector(sel, timeout=8000, state="visible")
            return sel
        except TimeoutError:
            continue
    return None

def wait_for_twitter_code(token, max_wait=120, interval=5):
    """
    Polls mail.tm API for Twitter verification code emails. Not used in the implementation, added as
    optional functionality.

    Args:
        token (str): The mail.tm API authentication token.
        max_wait (int, optional): Maximum time to wait in seconds. Defaults to 120.
        interval (int, optional): Time between checks in seconds. Defaults to 5.

    Returns:
        str|None: The 6-digit Twitter verification code if found, None if not found
        within max_wait time or if there's an error.
    """
    headers = {
        "Authorization": f"Bearer {token}"
    }

    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get("https://api.mail.tm/messages", headers=headers)
        if response.status_code != 200:
            print("❌ Failed to get messages:", response.text)
            return None

        messages = response.json().get("hydra:member", [])
        for msg in messages:
            if "twitter" in msg.get("from", {}).get("address", "").lower():
                # Fetch full message content
                message_id = msg["id"]
                full_msg = requests.get(f"https://api.mail.tm/messages/{message_id}", headers=headers).json()
                content = full_msg.get("text", "")

                # Look for a 6-digit code
                match = re.search(r"\b\d{6}\b", content)
                if match:
                    return match.group(0)

        time.sleep(interval)
        print("⏳ Waiting for Twitter code...")

    print("❌ Timed out waiting for Twitter code")
    return None

def fetch_once(pw):
    """
    Attempts to log into Twitter once and capture authentication tokens.

    Makes a single attempt to:
    1. Launch headless Firefox
    2. Navigate to Twitter
    3. Complete login process
    4. Capture authentication tokens

    Args:
        pw (Playwright): The Playwright instance to use for browser automation.

    Returns:
        tuple(str|None, str|None): A tuple of (auth_token, ct0) if successful,
        (None, None) if login fails.
    """
    log("launching headless Firefox")
    browser = pw.firefox.launch(headless=True, args=["--width=1280", "--height=720"])
    ctx     = browser.new_context()
    page    = ctx.new_page()
    try:
        log("➊ goto twitter.com")
        page.goto("https://twitter.com/", wait_until="domcontentloaded", timeout=45000)

        log("➋ click Sign in")
        page.click('a[href="/login"]', timeout=10000)

        log("➌ enter e-mail / phone")
        page.wait_for_selector('input[autocomplete="username"]', timeout=15000)
        page.fill('input[autocomplete="username"]', EMAIL)
        page.press('input[autocomplete="username"]', "Enter")

        log("➍ check optional confirm-username page")
        try:
            print("[cookiebot] checking for optional username field")
            page.wait_for_selector('input[data-testid="ocfEnterTextTextInput"]', timeout=5000)
            print("[cookiebot] optional username field found, entering it")
            page.fill('input[data-testid="ocfEnterTextTextInput"]', USERNAME)
            page.press('input[data-testid="ocfEnterTextTextInput"]', 'Enter')
        except:
            print("[cookiebot] optional username field not shown, continuing")

        log("➎ wait for password field")
        page.wait_for_selector('input[autocomplete="current-password"]', timeout=15000)
    
        log("➏ enter password")
        page.fill('input[autocomplete="current-password"]', PASSWORD)
        screenshot(page, "after_password_fill")
        page.press('input[autocomplete="current-password"]', "Enter")
        log("➐ wait for timeline or 2FA")
        try:
            #page.wait_for_selector('div[data-testid="SideNav_AccountSwitcher_Button"]', timeout=15000)
            page.wait_for_url(re.compile(r"/home|/timeline"), timeout=30000)
            log("✅ timeline loaded")
        except TimeoutError:
            screenshot(page, "wait_timeline_fail")
            raise Exception("❌ Timeline not detected — possibly 2FA or block encountered.")
        #log("➐ wait for timeline")
        #page.wait_for_url(re.compile(r"/home|/timeline"), timeout=30000)
        log("🧹 warming up session by visiting home timeline")

        # Go to an authenticated page like the timeline
        page.goto("https://twitter.com/home", timeout=15000)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/app/screenshots/warmup.png")

        log("✅ session warmed up by visiting /home")

        cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        print("auth_token", cookies.get("auth_token"))
        print("ct0", cookies.get("ct0"))
        return cookies.get("auth_token"), cookies.get("ct0")

    except TimeoutError as e:
        log(f"timeout: {e}")
        screenshot(page, "timeout")
        return None, None
    except Exception as e:
        log(f"❌ unknown exception: {e}")
        screenshot(page, "unknown")
        return None, None
    finally:
        ctx.close(); browser.close()

def update_env(auth, ct0):
    """
    Updates the environment file with new Twitter authentication credentials.

    Updates or adds TWITTER_AUTH_TOKEN and TWITTER_COOKIE variables in the
    file specified by ENV_PATH.

    Args:
        auth (str): The Twitter authentication token.
        ct0 (str): The Twitter ct0 cookie value.

    Returns:
        None. Modifies the environment file in place.
    """
    with open(ENV_PATH, "r+") as f:
        txt = f.read()
        txt = re.sub(r"^TWITTER_AUTH_TOKEN=.*", f"TWITTER_AUTH_TOKEN={auth}", txt, flags=re.M)
        if "TWITTER_AUTH_TOKEN" not in txt:
            txt += f"\nTWITTER_AUTH_TOKEN={auth}\n"
        txt = re.sub(r"^TWITTER_COOKIE=.*", f"TWITTER_COOKIE=auth_token={auth}; ct0={ct0}", txt, flags=re.M)
        f.seek(0)
        f.write(txt)
        f.truncate()
        f.flush()
        os.fsync(f.fileno())

def is_rsshub_healthy(key):
    """
    Checks if the RSSHub service is responding correctly.

    Makes a test request to a Twitter list RSS feed to verify the service
    is working with the current authentication.

    Args:
        key (str): The authentication token to use in the request.

    Returns:
        bool: True if the service responds with 200 OK, False otherwise.
    """
    try:
        response = requests.get(
            f"https://504e1826.host.njalla.net/rss/twitter/list/1936936171382468729?key={key}&limit=1",
            timeout=60
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def main_cycle():
    """
    Main login cycle that attempts to obtain Twitter authentication.

    Makes multiple attempts to get Twitter authentication tokens using
    exponential backoff between retries. When successful, updates auth
    files and restarts the RSSHub container.

    Returns:
        str|None: The authentication token if successful, None if all retries fail.
    """
    with sync_playwright() as pw:
        for i in range(MAX_RETRY):
            auth, ct0 = fetch_once(pw)
            if auth:
                log("✅ captured auth_token")
                update_auth_file(auth, ct0)
                time.sleep(1)
                subprocess.run(
                    ["docker", "compose", "up", "-d", "rsshub"],
                    cwd="/opt/rssstack",  # path where your docker-compose.yml is located
                    check=True,
                    capture_output=True,
                    text=True
                )
                return auth
            wait = BACKOFF[min(i, len(BACKOFF)-1)] + random.randint(0, 30)
            log(f"retry {i+1}/{MAX_RETRY} in {wait}s")
            time.sleep(wait)
        log("❌ all retries failed – will try again tomorrow")
        return None

if __name__ == "__main__":
    while True:
        auth = main_cycle()
        check_count = 0
        while True:
            check_count += 1
            log(f"Periodic health check {check_count} out of 24")
            if not is_rsshub_healthy(auth):
                log("RSSHub fetch failed, getting new cookies.")
                break
            log("RSSHub is healthy, sleeping 10 minutes before checking again.")
            time.sleep(600)
