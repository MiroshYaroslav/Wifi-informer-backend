import requests
from config import TIMEOUT


def get_privatbank_usd() -> str:
    url = "https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    for item in response.json():
        if item["ccy"] == "USD":
            return f"{float(item['buy']):.2f}"
    raise ValueError("USD not found in PrivatBank response")


def get_nbu_usd() -> str:
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    rate = response.json()[0]["rate"]
    return f"{float(rate):.2f}"


def get_usd_rate() -> str:
    try:
        return get_privatbank_usd()
    except Exception as e:
        print(f"[Error PrivatBank]: {e}. Trying NBU...")

        try:
            return get_nbu_usd()
        except Exception as fallback_e:
            print(f"[Error NBU]: {fallback_e}. No more sources available.")
            return "N/A"