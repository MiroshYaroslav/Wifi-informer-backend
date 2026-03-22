import re
import requests
from bs4 import BeautifulSoup
from config import TIMEOUT


def get_fuel_prices(session: requests.Session) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = session.get("https://index.minfin.com.ua/ua/markets/fuel/", headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        a95p, a95, a92, dp, gas = "N/A", "N/A", "N/A", "N/A", "N/A"

        table = soup.find('table', class_='line')
        if not table:
            print("[Error Fuel]: Таблицю class='line' не знайдено.")
            return "A-95+: N/A \nA-95: N/A \nA-92: N/A \nDP: N/A \nGas: N/A"

        for row in table.find_all('tr'):
            cols = row.find_all('td')

            if len(cols) >= 3:
                name = cols[0].get_text(strip=True).upper()
                raw_price = cols[2].get_text(strip=True).replace(',', '.')
                price = "".join(re.findall(r'[0-9.]', raw_price))

                if not price:
                    continue

                is_premium = "+" in name or "ПРЕМ" in name or "PULLS" in name or "MUSTANG" in name

                if ("А-95" in name or "A-95" in name) and is_premium and a95p == "N/A":
                    a95p = price[:5]
                elif ("А-95" in name or "A-95" in name) and not is_premium and a95 == "N/A":
                    a95 = price[:5]
                elif ("А-92" in name or "A-92" in name) and a92 == "N/A":
                    a92 = price[:5]
                elif ("ДП" in name or "ДИЗЕЛЬ" in name) and dp == "N/A":
                    dp = price[:5]
                elif ("ГАЗ" in name or "АВТОГАЗ" in name) and gas == "N/A":
                    gas = price[:5]

        if a95 != "N/A" or dp != "N/A" or gas != "N/A" or a95p != "N/A" or a92 != "N/A":
            return f"A-95+: {a95p}\nA-95: {a95}\nA-92: {a92}\nDP: {dp}\nGas: {gas}"
        else:
            print("[Error Fuel]: Рядки з пальним не знайдені.")

    except Exception as error:
        print(f"[Error Fuel]: {error}")

    return "A-95+: N/A \nA-95: N/A \nA-92: N/A \nDP: N/A \nGas: N/A"