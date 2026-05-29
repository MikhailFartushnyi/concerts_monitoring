"""
Скрапер gorbilet.ru — API.
"""

import hashlib
import time
from datetime import date

import requests
from tqdm import tqdm

API_URL = "https://api.gorbilet.ru/v4/events/"
LIMIT = 12

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://gorbilet.ru",
    "Pragma": "no-cache",
    "Referer": "https://gorbilet.ru/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

BASE_PARAMS = {
    "limit": str(LIMIT),
    "is_web": "true",
    "city": "1",
    "status": "active",
    "ordering": "-activated_at",
    "with_cards": "true",
    "categories": ["168", "1688", "2886", "2883", "2884", "2887"],
}


def run() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        r = session.get(API_URL, params={**BASE_PARAMS, "offset": "0"}, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        tqdm.write(f"  [gorbilet] ошибка первого запроса: {e}")
        return []

    total = data.get("count", 0)
    all_items = _parse(data.get("results", []))

    with tqdm(total=total, initial=len(all_items),
              desc="  gorbilet", unit=" концерт", leave=True) as pbar:

        while data.get("next"):
            offset = len(all_items)
            try:
                r = session.get(
                    API_URL,
                    params={**BASE_PARAMS, "offset": str(offset)},
                    timeout=15,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                tqdm.write(f"  [gorbilet] ошибка offset={offset}: {e}")
                break

            batch = _parse(data.get("results", []))
            all_items.extend(batch)
            pbar.update(len(batch))
            time.sleep(0.5)

    return all_items


def _parse(results: list[dict]) -> list[dict]:
    items = []
    today = str(date.today())

    for ev in results:
        slug = ev.get("slug", "")
        url = f"https://gorbilet.ru/msk/actions/{slug}/" if slug else None
        if not url:
            continue

        # Фото: первое изображение png_360
        if type(ev.get('image', {})) == str:
            photo = ev.get('image')
        else:
            photo = ev.get('image', {}).get('png_360')

        # Дата
        date_txt = ev.get("dates_txt", "")
        if not date_txt:
            nearest = ev.get("nearest_event") or {}
            date_txt = nearest.get("start_date", "")

        items.append({
            "id": _make_id(url or ev.get("title", "")),
            "url": url,
            "source": "gorbilet",
            #"title": ev.get("title", ""),
            "title_short": ev.get("title_short", ""),
            "description": ev.get("short_description", ""),
            "venue": ev.get("place_title", ""),
            "address": "",
            "metro": "",
            "date": date_txt,
            "age": ev.get("age_category", ""),
            "price_old": f"{ev['instead_price']} ₽" if ev.get("instead_price") else "",
            "price_new": ev.get("display_price", ""),
            "discount_pct": f"{ev['discount']}%" if ev.get("discount") else "",
            "promo_code": "",
            "photo": photo,
            "found_at": today,
            "duplicate_ids": "",
        })

    return items


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]
