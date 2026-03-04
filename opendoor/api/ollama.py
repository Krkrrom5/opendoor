import json, os
from .base import BaseLLM

try:
    import urllib.request, urllib.error
    _OK = True
except ImportError:
    _OK = False


class OllamaLLM(BaseLLM):
    def __init__(self, model="llama3", host="http://localhost:11434"):
        self.model = model
        self.host = host

    def is_available(self):
        try:
            req = urllib.request.urlopen(f"{self.host}/api/tags", timeout=2)
            return req.status == 200
        except Exception:
            return False

    def send(self, messages: list, stream: bool = True):
        import urllib.request
        url = f"{self.host}/api/chat"
        payload = json.dumps({"model":self.model,"messages":messages,"stream":stream}).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            if stream:
                for line in resp:
                    if line:
                        data = json.loads(line)
                        text = data.get("message",{}).get("content","")
                        if text:
                            yield text
                        if data.get("done"):
                            break
            else:
                data = json.loads(resp.read())
                yield data["message"]["content"]

    def list_models(self):
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as resp:
                data = json.loads(resp.read())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
