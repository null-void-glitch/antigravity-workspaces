#!/usr/bin/env python3
"""
extract_emails.py

Visits each item's website in results2_copy.json, finds the Impressum page,
extracts an email address, and saves it back to the JSON file.

Usage:
    python3 extract_emails.py

The script is resumable: items that already have an 'email' field (even if None)
are skipped, so you can re-run after interruptions.
"""

import json
import re
import time
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_FILE  = "results2_copy.json"
OUTPUT_FILE = "results2_copy.json"   # overwrite in-place; change if you prefer

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
TIMEOUT     = 10   # seconds per request
DELAY       = 1.0  # polite delay between sites (seconds)
MAX_RETRIES = 1    # retries on connection error

# Regex that matches a typical e-mail address
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Keywords (lowercase) used to detect an Impressum link
IMPRESSUM_KEYWORDS = [
    "impressum",
    "imprint",
    "legal",
    "kontakt",       # sometimes contact page also has an email
    "anbieterkennzeichnung",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url: str, session: requests.Session) -> requests.Response | None:
    """Fetch a URL; return Response or None on failure."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT,
                               allow_redirects=True)
            return resp
        except Exception as exc:
            if attempt == MAX_RETRIES:
                print(f"    [FAIL] {url} — {exc}")
                return None
            time.sleep(1)


def find_impressum_urls(base_url: str, soup: BeautifulSoup) -> list[str]:
    """
    Return a ranked list of candidate Impressum page URLs found in <a> tags.
    The best match (link text or href containing 'impressum') comes first.
    """
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True).lower()
        combined = (href + " " + text).lower()
        if any(kw in combined for kw in IMPRESSUM_KEYWORDS):
            full = urljoin(base_url, href)
            # only follow same-domain or relative links
            if urlparse(full).netloc in ("", urlparse(base_url).netloc):
                score = 2 if "impressum" in combined else 1
                candidates.append((score, full))

    # Deduplicate, keeping highest score, then sort best-first
    seen: dict[str, int] = {}
    for score, url in candidates:
        seen[url] = max(seen.get(url, 0), score)
    return [u for u, _ in sorted(seen.items(), key=lambda x: -x[1])]


def extract_email_from_html(html: str) -> str | None:
    """Return the first e-mail address found in raw HTML, or None."""
    # 1) Try visible text first (avoids mailto: duplicates)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")
    m = EMAIL_RE.search(text)
    if m:
        return m.group(0).lower()
    # 2) Fallback: search raw HTML (catches mailto: obfuscation variants)
    m = EMAIL_RE.search(html)
    if m:
        return m.group(0).lower()
    return None


def get_email_for_website(website: str, session: requests.Session) -> str | None:
    """
    Visit the website homepage, find the Impressum link, fetch that page,
    and return the first email found. Returns None if nothing is found.
    """
    # Normalise URL
    if not website.startswith(("http://", "https://")):
        website = "http://" + website

    # 1) Fetch homepage
    resp = fetch(website, session)
    if resp is None or not resp.ok:
        return None

    homepage_html = resp.text
    base_url = resp.url  # may differ from `website` after redirects

    # 2) Look for Impressum links on the homepage
    soup = BeautifulSoup(homepage_html, "html.parser")
    impressum_urls = find_impressum_urls(base_url, soup)

    # 3) Try each Impressum candidate
    for imp_url in impressum_urls[:3]:   # limit to top 3 candidates
        if imp_url == base_url:
            # Same page – extract directly
            email = extract_email_from_html(homepage_html)
        else:
            imp_resp = fetch(imp_url, session)
            if imp_resp is None or not imp_resp.ok:
                continue
            email = extract_email_from_html(imp_resp.text)
        if email:
            return email

    # 4) Fallback: try common Impressum paths if none were linked
    for path in ["/impressum", "/impressum.html", "/impressum.php",
                 "/imprint", "/kontakt"]:
        fallback_url = urljoin(base_url, path)
        if fallback_url in impressum_urls:
            continue  # already tried
        fb_resp = fetch(fallback_url, session)
        if fb_resp is None or not fb_resp.ok:
            continue
        email = extract_email_from_html(fb_resp.text)
        if email:
            return email

    # 5) Last resort: scan the homepage itself
    return extract_email_from_html(homepage_html)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    total   = len(items)
    skipped = sum(1 for it in items if "email" in it)
    print(f"Loaded {total} items. {skipped} already processed, "
          f"{total - skipped} remaining.\n")

    session = requests.Session()

    for idx, item in enumerate(items, 1):
        if "email" in item:
            continue  # already done (even if email is None)

        website = (item.get("website") or "").strip()
        label   = item.get("agency_name", website)[:50]

        if not website:
            print(f"[{idx}/{total}] No website — skipping: {label}")
            item["email"] = None
            continue

        print(f"[{idx}/{total}] {website} …", end=" ", flush=True)

        email = get_email_for_website(website, session)
        item["email"] = email
        print(email if email else "(not found)")

        # Save after every item so progress is not lost on interruption
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        time.sleep(DELAY)

    print("\nDone. Results saved to", OUTPUT_FILE)


if __name__ == "__main__":
    # Quick dependency check
    try:
        import requests      # noqa: F401
        import bs4           # noqa: F401
    except ImportError as e:
        print(f"Missing dependency: {e}.\nInstall with:  pip install requests beautifulsoup4")
        sys.exit(1)

    main()
