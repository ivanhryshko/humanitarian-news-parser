# requirements: requests, beautifulsoup4, feedparser, json
import requests
from bs4 import BeautifulSoup
import feedparser
import json
from urllib.parse import urljoin
from datetime import datetime

CURRENT_YEAR = str(datetime.now().year)

# Завантаження ключових слів з файлу
with open("keywords_config.json", "r", encoding="utf-8") as f:
    raw_keywords = json.load(f)
    KEYWORDS = list(set(k.strip().lower() for k in raw_keywords if k.strip()))

# Завантаження джерел з файлу
with open("sources_config.json", "r", encoding="utf-8") as f:
    raw_sources = json.load(f)
    SOURCES = []
    for s in raw_sources:
        if all(key in s for key in ("name", "url", "type")) and s["url"].strip():
            SOURCES.append(s)

if not SOURCES:
    print("[WARNING] Список джерел порожній або невалідний")

results = []

# HTML
def parse_html(source):
    base_url = source["url"]
    page = 1
    max_pages = 5

    while True:
        url = base_url
        if page > 1:
            if "page=" in base_url:
                url = re.sub(r"page=\d+", f"page={page}", base_url)
            else:
                if "?" in base_url:
                    url += f"&page={page}"
                else:
                    url += f"?page={page}"

        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            texts = soup.get_text().lower()
            found = any(k in texts for k in KEYWORDS)
            if found:
                for tag in soup.find_all(string=True):
                    if CURRENT_YEAR in tag:
                        results.append({"source": source["name"], "url": url})
                        break
        except Exception as e:
            print(f"[ERROR] {source['name']} (page {page}): {e}")
            break

        if page >= max_pages or len(soup.get_text().strip()) < 500:
            break
        page += 1

# RSS
def parse_rss(source):
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            content = f"{entry.title} {entry.summary}".lower()
            if any(k in content for k in KEYWORDS):
                if "published" in entry and CURRENT_YEAR in entry.published:
                    results.append({
                        "source": source["name"],
                        "title": entry.title,
                        "url": entry.link
                    })
    except Exception as e:
        print(f"[ERROR RSS] {source['name']}: {e}")

# API
def parse_api(source):
    try:
        r = requests.get(source["url"], timeout=10)
        data = r.json()
        for item in data.get("data", []):
            attributes = item.get("attributes", {})
            date = attributes.get("date", "")
            if CURRENT_YEAR in date:
                text = attributes.get("title", "").lower() + " " + attributes.get("body-html", "").lower()
                if any(k in text for k in KEYWORDS):
                    results.append({
                        "source": source["name"],
                        "title": attributes.get("title"),
                        "url": attributes.get("url", "https://reliefweb.int")
                    })
    except Exception as e:
        print(f"[ERROR API] {source['name']}: {e}")

# Виконання
for src in SOURCES:
    if src["type"] == "html":
        parse_html(src)
    elif src["type"] == "rss":
        parse_rss(src)
    elif src["type"] == "api":
        parse_api(src)

with open("docs/results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Знайдено результатів: {len(results)}")
