import os
import json
import time
import requests
from bs4 import BeautifulSoup

# JOUW BOL.COM PRODUCTPAGINA
URLS = [
    "https://www.bol.com/nl/nl/p/playstation-portal-remote-player-midnight-black/9300000222945148/?cid=1771508458538-6341274984562&bltgh=ab850407-c74d-44df-971b-3ed9fbfaa4fc.themeCardCarouselSlotGroup_2_themeCardCarouselGroup.themeCardCarouselItem_0.Banner&promo=brandcampaign_100_De-kracht-van-PlayStation_2_Speel_0__",
]

STATE_FILE = "state.json"

TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def tg_send(msg):
    api = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(api, data={"chat_id": TG_CHAT_ID, "text": msg}, timeout=30)
    r.raise_for_status()

def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def extract_availability_from_jsonld(html: str):
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    for s in scripts:
        try:
            data = json.loads(s.get_text(strip=True))
        except Exception:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            av = item.get("availability")

            offers = item.get("offers")
            if av is None and isinstance(offers, dict):
                av = offers.get("availability")
            if av is None and isinstance(offers, list):
                for off in offers:
                    if isinstance(off, dict) and off.get("availability"):
                        av = off.get("availability")
                        break

            if isinstance(av, str):
                av_l = av.lower()
                if "instock" in av_l:
                    return "in_stock"
                if "outofstock" in av_l or "soldout" in av_l:
                    return "out_of_stock"

    return None

def main():
    state = load_state()

    for url in URLS:
        try:
            html = fetch_html(url)
            availability = extract_availability_from_jsonld(html)
        except Exception as e:
            print(f"Error on {url}: {e}")
            continue

        prev = state.get(url, {}).get("availability")
        state[url] = {"availability": availability, "ts": int(time.time())}

        if prev in ["out_of_stock", None] and availability == "in_stock":
            tg_send(f"✅ OP VOORRAAD (koopbaar): {url}")

        print(f"{url} → {availability}")

        time.sleep(2)

    save_state(state)

if __name__ == "__main__":
    main()
