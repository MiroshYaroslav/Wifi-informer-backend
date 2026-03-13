import requests

from config import TIMEOUT

PRIVATBANK_URL = "https://api.privatbank.ua/p24api/pubinfo?exchange&coursid=5"
NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"


def get_privatbank_usd(session: requests.Session) -> str:
    response = session.get(PRIVATBANK_URL, timeout=TIMEOUT)
    response.raise_for_status()

    for item in response.json():
        if item.get("ccy") == "USD":
            return f"{float(item['buy']):.2f}"

    raise ValueError("USD not found in PrivatBank response")


def get_nbu_usd(session: requests.Session) -> str:
    response = session.get(NBU_URL, timeout=TIMEOUT)
    response.raise_for_status()

    data = response.json()
    if not data:
        raise ValueError("Empty NBU response")

    rate = data[0]["rate"]
    return f"{float(rate):.2f}"


def get_usd_rate(session: requests.Session) -> str:
    try:
        return get_privatbank_usd(session)
    except Exception as error:
        print(f"[Error PrivatBank]: {error}. Trying NBU...")

    try:
        return get_nbu_usd(session)
    except Exception as error:
        print(f"[Error NBU]: {error}. No more sources available.")
        return "N/A"