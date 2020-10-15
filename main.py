import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL_FIRST = "https://www.mebelshara.ru/contacts"
URL_SECOND = (
    "https://apigate.tui.ru"
    "/api"
    "/office"
    "/list"
    "?cityId=1"
    "&subwayId="
    "&hoursFrom="
    "&hoursTo="
    "&serviceIds=all"
    "&toBeOpenOnHolidays=false"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    "accept": "*/*",
}


def save_records(records: list):
    out_file = Path(__file__).parent / "results.json"
    with out_file.open("w") as out:
        json.dump(records, out, sort_keys=True, indent=2, ensure_ascii=False)


def get_response(url, params=""):
    response = requests.get(url, headers=HEADERS, params=params)
    return response


def get_payload_from_url(url: str) -> dict:
    resp = requests.get(url)
    if resp.status_code != 200:
        return {"offices": []}

    payload = resp.json()
    return payload


def transform_site2_record(record: dict) -> dict:
    result = {
        "address": record["address"],
        "latlon": [record["latitude"], record["longitude"]],
        "name": record["name"],
        "phones": [phone_record["phone"].strip() for phone_record in record["phones"]],
        "working_hours": build_working_hours(record["hoursOfOperation"]),
    }
    return result


def build_working_hours(item: dict) -> list:
    workday_start = item["workdays"]["startStr"]
    workday_end = item["workdays"]["endStr"]
    workday_dayoff = item["workdays"]["isDayOff"]

    saturday_start = item.get("saturday", {}).get("startStr")
    saturday_end = item.get("saturday", {}).get("endStr")
    saturday_dayoff = item.get("saturday", {}).get("isDayOff")

    sunday_start = item.get("sunday", {}).get("startStr")
    sunday_end = item.get("sunday", {}).get("endStr")
    sunday_dayoff = item.get("sunday", {}).get("isDayOff")

    result = []

    saturday_added = False
    sunday_added = False

    if all((not workday_dayoff, workday_start, workday_end)):
        day_start = "пн"
        day_end = "пт"
        time_start = workday_start
        time_end = workday_end

        if all(
            (
                not saturday_dayoff,
                saturday_start,
                saturday_end,
                saturday_start == time_start,
                saturday_end == time_end,
            )
        ):
            saturday_added = True
            day_end = "сб"

        if all(
            (
                saturday_added,
                not sunday_dayoff,
                sunday_start,
                sunday_end,
                sunday_start == time_start,
                sunday_end == time_end,
            )
        ):
            sunday_added = True
            day_end = "вс"

        result.append(f"{day_start} - {day_end} с {time_start} до {time_end}")

    if all((not saturday_added, not saturday_dayoff, saturday_start, saturday_end)):
        day_start = "сб"
        time_start = saturday_start
        time_end = saturday_end

        if all(
            (
                not sunday_dayoff,
                sunday_start,
                sunday_end,
                sunday_start == time_start,
                sunday_end == time_end,
            )
        ):
            sunday_added = True

        day_end = "" if not sunday_added else f" - вс"

        result.append(f"{day_start}{day_end} с {time_start} до {time_end}")

    if all((not sunday_added, not sunday_dayoff, sunday_start, sunday_end)):
        result.append(f"вс с {sunday_start} до {sunday_end}")

    return result


def get_content_from_first_url(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("div", class_="city-item")

    for item in items:
        contacts = {
            "address": "{}, {}".format(
                item.find("h4", class_="js-city-name").get_text(),
                item.find("div", class_="shop-list-item").get("data-shop-address"),
            ),
            "latlon": [
                float(
                    item.find("div", class_="shop-list-item").get("data-shop-latitude")
                ),
                float(
                    item.find("div", class_="shop-list-item").get("data-shop-longitude")
                ),
            ],
            "name": item.find("div", class_="shop-name").get_text(),
            "phones": item.find("div", class_="shop-list-item")
            .get("data-shop-phone")
            .replace("(", "")
            .replace(")", ""),
            "working_hours": "{} {}".format(
                item.find("div", class_="shop-list-item").get("data-shop-mode1"),
                item.find("div", class_="shop-list-item").get("data-shop-mode2"),
            ),
        }

        yield contacts


def get_content_from_second_url(url, params="") -> list:
    payload = get_payload_from_url(URL_SECOND)
    records = [transform_site2_record(record) for record in payload["offices"]]

    return records


def main():
    records_site1 = list(get_content_from_first_url(get_response(URL_FIRST).text))
    records_site2 = get_content_from_second_url(URL_SECOND)
    records = records_site1 + records_site2
    save_records(records)


if __name__ == "__main__":
    main()
