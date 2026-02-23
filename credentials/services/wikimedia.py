import requests

def shorten_url(long_url: str) -> str | None:
    endpoint = "https://meta.wikimedia.org/w/api.php"
    headers = {"User-Agent": "WMB/1.0 (eder.porto@wmnobrasil.org)"}
    params = {"action": "shortenurl", "url": long_url,"format": "json"}

    try:
        response = requests.post(endpoint, headers=headers, data=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        return data.get("shortenurl", {}).get("shorturl")

    except Exception:
        return None