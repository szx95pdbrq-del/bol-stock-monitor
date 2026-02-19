import os, json, time
import requests
from bs4 import BeautifulSoup

URLS = [
    URLS = [
    "https://www.bol.com/nl/nl/p/pokemon-me02-5-ascended-heroes-elite-trainer-box/9300000256665012/",
]
,
]

STATE_FILE = "state.json"
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

HEADERS = {
    "User-Agent": "StockMonitor/1.0 (personal use; low frequency)"
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

        time.sleep(2)

    save_state(state)

if __name__ == "__main__":
    main()
