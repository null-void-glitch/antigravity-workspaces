#!/usr/bin/env python3
"""
extract_company_names.py

Visits each item's website in results2_copy.json, finds the Impressum page,
extracts the legal company name, and saves it back as "company_name" in the
JSON file.

Usage:
    python3 extract_company_names.py

The script is resumable: items that already have a 'company_name' field (even
if None) are skipped, so you can re-run after interruptions.

Strategy for extracting the company name:
  1. Fetch the Impressum / Imprint page (same logic as extract_emails.py).
  2. Look for the company name using several heuristics (in priority order):
     a. Structured data: JSON-LD "name" property of a LocalBusiness / Organization.
     b. <meta property="og:site_name"> or <meta name="application-name">.
     c. Text patterns on the Impressum page that follow German legal keywords
        like "Angaben gemäß §5 TMG", "Firma:", "Inhaber:", "Betreiber:" etc.
     d. The <title> tag of the Impressum page (cleaned up).
     e. Fallback: the <title> tag of the homepage.
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

# Keywords (lowercase) used to detect an Impressum link
IMPRESSUM_KEYWORDS = [
    "impressum",
    "imprint",
    "anbieterkennzeichnung",
]

# German Impressum section headings / labels that typically precede the name
LEGAL_LABELS = re.compile(
    r"(?:angaben\s+gem[äa][ß]\s+[§§]+\s*5|"
    r"firma\s*:|"
    r"inhaber\s*:|"
    r"betreiber\s*:|"
    r"verantwortlich\s*:|"
    r"unternehmen\s*:|"
    r"anbieterkennzeichnung)",
    re.IGNORECASE,
)

# Noise suffixes/words to strip from page titles
TITLE_STRIP_RE = re.compile(
    r"\s*[|–\-—]\s*.+$"           # " | Company" or " - Impressum" etc.
)

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
    """
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True).lower()
        combined = (href + " " + text).lower()
        if any(kw in combined for kw in IMPRESSUM_KEYWORDS):
            full = urljoin(base_url, href)
            if urlparse(full).netloc in ("", urlparse(base_url).netloc):
                score = 2 if "impressum" in combined else 1
                candidates.append((score, full))

    seen: dict[str, int] = {}
    for score, url in candidates:
        seen[url] = max(seen.get(url, 0), score)
    return [u for u, _ in sorted(seen.items(), key=lambda x: -x[1])]


def extract_name_from_jsonld(soup: BeautifulSoup) -> str | None:
    """Try to find an Organization / LocalBusiness name in JSON-LD blocks."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        # data can be a list or a dict (or nested @graph)
        items = data if isinstance(data, list) else [data]
        # flatten @graph if present
        flat = []
        for item in items:
            if isinstance(item, dict) and "@graph" in item:
                flat.extend(item["@graph"])
            else:
                flat.append(item)
        for item in flat:
            if not isinstance(item, dict):
                continue
            types = item.get("@type", "")
            if isinstance(types, str):
                types = [types]
            org_types = {
                "Organization", "LocalBusiness", "RealEstateAgent",
                "Corporation", "Company",
            }
            if any(t in org_types for t in types):
                name = item.get("name") or item.get("legalName")
                if name and isinstance(name, str) and len(name.strip()) > 1:
                    return name.strip()
    return None


def extract_name_from_meta(soup: BeautifulSoup) -> str | None:
    """Try og:site_name or application-name meta tags."""
    for prop in [("property", "og:site_name"), ("name", "application-name")]:
        tag = soup.find("meta", {prop[0]: prop[1]})
        if tag and tag.get("content"):
            name = tag["content"].strip()
            if name:
                return name
    return None


def extract_name_from_impressum_text(html: str) -> str | None:
    """
    Look for text lines that follow German Impressum section labels and return
    the next non-empty line as the company name.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines()]

    for i, line in enumerate(lines):
        if LEGAL_LABELS.search(line):
            # scan the next few lines for the first non-trivial value
            for candidate in lines[i + 1: i + 6]:
                # skip lines that look like pure labels or are too short
                if len(candidate) < 3:
                    continue
                if LEGAL_LABELS.search(candidate):
                    break  # hit another label, stop
                # skip if it's just a repeat of the label keyword
                return candidate
    return None


def clean_title(title: str) -> str:
    """Strip trailing ' | Impressum' style suffixes from a page title."""
    title = title.strip()
    # Remove common suffixes like "- Impressum", "| Startseite", etc.
    title = TITLE_STRIP_RE.sub("", title)
    return title.strip()


def extract_name_from_title(soup: BeautifulSoup) -> str | None:
    """Return a cleaned page <title> as a last resort."""
    tag = soup.find("title")
    if tag and tag.string:
        cleaned = clean_title(tag.string)
        if cleaned:
            return cleaned
    return None


def get_company_name_for_website(
    website: str, session: requests.Session
) -> str | None:
    """
    Visit the website, find the Impressum page, and extract the company name.
    Returns None if nothing useful is found.
    """
    if not website.startswith(("http://", "https://")):
        website = "http://" + website

    # 1) Fetch homepage
    resp = fetch(website, session)
    if resp is None or not resp.ok:
        return None

    homepage_html = resp.text
    base_url = resp.url
    homepage_soup = BeautifulSoup(homepage_html, "html.parser")

    # Quick check: JSON-LD / meta on homepage
    name = extract_name_from_jsonld(homepage_soup)
    if name:
        return name
    name = extract_name_from_meta(homepage_soup)
    if name:
        return name

    # 2) Find Impressum links
    impressum_urls = find_impressum_urls(base_url, homepage_soup)

    # 3) Try each Impressum candidate
    imp_html = None
    for imp_url in impressum_urls[:3]:
        if imp_url == base_url:
            imp_html = homepage_html
        else:
            imp_resp = fetch(imp_url, session)
            if imp_resp is None or not imp_resp.ok:
                continue
            imp_html = imp_resp.text
        if imp_html:
            break

    # 4) Fallback: try common Impressum paths
    if not imp_html:
        for path in ["/impressum", "/impressum.html", "/impressum.php",
                     "/imprint", "/imprint.html"]:
            fallback_url = urljoin(base_url, path)
            if fallback_url in impressum_urls:
                continue
            fb_resp = fetch(fallback_url, session)
            if fb_resp is None or not fb_resp.ok:
                continue
            imp_html = fb_resp.text
            break

    if imp_html:
        imp_soup = BeautifulSoup(imp_html, "html.parser")

        name = extract_name_from_jsonld(imp_soup)
        if name:
            return name

        name = extract_name_from_meta(imp_soup)
        if name:
            return name

        name = extract_name_from_impressum_text(imp_html)
        if name:
            return name

        name = extract_name_from_title(imp_soup)
        if name:
            return name

    # 5) Last resort: homepage title
    return extract_name_from_title(homepage_soup)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    total   = len(items)
    skipped = sum(1 for it in items if "company_name" in it)
    print(f"Loaded {total} items. {skipped} already processed, "
          f"{total - skipped} remaining.\n")

    session = requests.Session()

    for idx, item in enumerate(items, 1):
        if "company_name" in item:
            continue  # already done (even if company_name is None)

        website = (item.get("website") or "").strip()
        label   = item.get("agency_name", website)[:50]

        if not website:
            print(f"[{idx}/{total}] No website — skipping: {label}")
            item["company_name"] = None
            continue

        print(f"[{idx}/{total}] {website} …", end=" ", flush=True)

        company_name = get_company_name_for_website(website, session)
        item["company_name"] = company_name
        print(company_name if company_name else "(not found)")

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
