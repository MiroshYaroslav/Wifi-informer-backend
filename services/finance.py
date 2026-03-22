import requests

from config import TIMEOUT

PRIVATBANK_URL = "https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5"
NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"


def get_privatbank_rates(session: requests.Session) -> tuple[str, str]:
    response = session.get(PRIVATBANK_URL, timeout=TIMEOUT)
    response.raise_for_status()
    usd, eur = "N/A", "N/A"
    for item in response.json():
        if item.get("ccy") == "USD":
            usd = f"{float(item['buy']):.2f}"
        elif item.get("ccy") == "EUR":
            eur = f"{float(item['buy']):.2f}"
    return usd, eur

def get_nbu_rates(session: requests.Session) -> tuple[str, str]:
    response = session.get(NBU_URL, timeout=TIMEOUT)
    response.raise_for_status()
    usd, eur = "N/A", "N/A"
    for item in response.json():
        if item.get("cc") == "USD":
            usd = f"{float(item['rate']):.2f}"
        elif item.get("cc") == "EUR":
            eur = f"{float(item['rate']):.2f}"
    return usd, eur

def get_exchange_rates(session: requests.Session) -> tuple[str, str]:
    try:
        return get_privatbank_rates(session)
    except Exception as error:
        print(f"[Error PrivatBank]: {error}. Trying NBU...")
    try:
        return get_nbu_rates(session)
    except Exception as error:
        print(f"[Error NBU]: {error}. No sources.")
        return "N/A", "N/A"