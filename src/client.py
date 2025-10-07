import requests

class BackendClient:
    def __init__(self, url: str, response_key: str = "reply", timeout_s: int = 30, headers: dict | None = None):
        self.url = url
        self.response_key = response_key
        self.timeout_s = timeout_s
        self.headers = headers or {}

    def ask(self, device: str, text: str) -> str:
        payload = {"device": device, "text": text}
        r = requests.post(self.url, json=payload, timeout=self.timeout_s, headers=self.headers)
        r.raise_for_status()
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"reply": r.text}
        return data.get(self.response_key, "(ingen respons)")
