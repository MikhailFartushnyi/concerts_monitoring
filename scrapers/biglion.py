
"""
Скрапер biglion.ru — POST API.
Получаем:
- акции
- venue
- address
- нормальные дату и время через graphql
"""

import hashlib
import re
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo
import requests
from tqdm import tqdm

API_URL = "https://www.biglion.ru/gateway/dealOfferService/api/v1/deal-offer"

GRAPHQL_URL = "https://ticket-service.biglion.ru/graphql"

LIMIT = 60

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.biglion.ru",
    "Pragma": "no-cache",
    "Referer": "https://www.biglion.ru/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

BASE_BODY = {
    "filters": [
        {
            "base": [
                {
                    "field": "categorySlug",
                    "operator": "in",
                    "value": "/services/other/kontserty-klassicheskoy-muzyki/"
                },
                {
                    "field": "citySlug",
                    "operator": "=",
                    "value": "moscow"
                },
                {
                    "operator": "and"
                },
                {
                    "field": "holdDay",
                    "operator": "=",
                    "value": "0"
                },
            ]
        }
    ],
    "sort": "startDate desc",
    "limit": LIMIT,
    "category": {
        "slug": "/services/other/kontserty-klassicheskoy-muzyki/",
        "site": "biglion",
        "city": "moscow",
        "mainPage": "off",
        "popular": "off",
    },
}


def run() -> list[dict]:

    session = requests.Session()
    session.headers.update(HEADERS)

    all_items = []

    offset = 0

    with tqdm(desc="  biglion", unit=" концерт", leave=True) as pbar:

        while True:

            body = {
                **BASE_BODY,
                "offset": offset
            }

            try:
                r = session.post(
                    API_URL,
                    json=body,
                    timeout=15
                )

                r.raise_for_status()

                data = r.json()

            except Exception as e:
                tqdm.write(f"  [biglion] ошибка offset={offset}: {e}")
                break

            deals = (
                data.get("data", {})
                .get("data", {})
                .get("deals", [])
            )

            if not deals:
                break

            batch = _parse(session, deals)

            all_items.extend(batch)

            pbar.update(len(batch))

            if len(deals) < LIMIT:
                break

            offset += LIMIT

            time.sleep(0.5)

    return all_items


def _parse(
        session: requests.Session,
        deals: list[dict]
) -> list[dict]:

    items = []

    today = str(date.today())

    for d in deals:

        do_id = d.get("id")

        deal_url = d.get("url", "")

        url = (
            f"https://www.biglion.ru/deals/{deal_url}"
            if deal_url else ""
        )

        locations = d.get("locations") or []

        metro = (
            locations[0].get("metro", "")
            if locations else ""
        )

        activity_id = get_activity_id(
            session=session,
            url=url
        )

        event_data = get_event_data(
            session=session,
            do_id=do_id,
            activity_id=activity_id
        )

        venue = event_data.get("venue", "")

        address = (
            event_data.get("address")
            or (
                locations[0].get("friendlyAddress", "")
                if locations else ""
            )
        )

        event_ts = event_data.get("date")

        date_txt = ""
        time_txt = ""

        if event_ts:
            dt = datetime.utcfromtimestamp(event_ts)

            date_txt = dt.strftime("%d.%m.%Y")

            time_txt = dt.strftime("%H:%M")

        price_old = d.get("price", "")

        price_new = d.get("priceDiscounted", "")

        discount = d.get("discount", "")

        items.append({
            "id": _make_id(url or d.get("title", "")),
            "url": url,
            "source": "biglion",

            #"title": "",

            "title_short": d.get("title", ""),

            "description": "",

            "venue": venue,

            "address": address,

            "metro": metro,

            "date": f'{date_txt}, {time_txt}',

            "age": "",

            "price_old": (
                f"{price_old} ₽"
                if price_old else ""
            ),

            "price_new": (
                f"{price_new} ₽"
                if price_new else ""
            ),

            "discount_pct": (
                f"{discount}%"
                if discount else ""
            ),

            "promo_code": "",

            "photo": d.get("image", ""),

            "found_at": today,

            "duplicate_ids": "",
        })

    return items


def get_activity_id(
        session: requests.Session,
        url: str
) -> str:

    if not url:
        return ""

    try:

        r = session.get(
            url,
            timeout=15
        )

        r.raise_for_status()

        match = re.search(
            r'"ticketActivityExtId"\s*:\s*"(\d+)"',
            r.text
        )

        if match:
            return match.group(1)

    except Exception as e:
        print(f"[biglion] activityId error: {e}")

    return ""


def get_event_data(
        session: requests.Session,
        do_id: int,
        activity_id: str
) -> dict:

    if not activity_id:
        return {}

    json_data = {
        "query": f"""
        mutation {{
            fetchAndSaveEvents(
                input: {{
                    doId: {do_id},
                    activityId: "{activity_id}",
                    ticketSystemId: 2,
                    yandexCityId: null
                }}
            ) {{
                id
                doId
                date
                eventExtId
                name
                venue
                address
                ticketsSystemId
                hallId
            }}
        }}
        """
    }

    try:

        r = session.post(
            GRAPHQL_URL,
            json=json_data,
            timeout=15
        )

        r.raise_for_status()

        data = r.json()

        events = (
            data.get("data", {})
            .get("fetchAndSaveEvents", [])
        )

        if events:
            return events[0]

    except Exception as e:
        print(f"[biglion] graphql error: {e}")

    return {}


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

