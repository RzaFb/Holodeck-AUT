import os, requests

class GithubModelsLLM:
    def __init__(self, api_key=None, base_url=None, model=None,
                 max_tokens=2048, temperature=0.2, timeout=120, trust_env=None):
        self.api_key = (api_key or os.getenv("GITHUB_TOKEN") or
                        os.getenv("GH_TOKEN") or os.getenv("OPENAI_API_KEY"))
        self.base_url = (base_url or os.getenv("OPENAI_API_BASE") or
                         os.getenv("OPENAI_BASE_URL") or
                         "https://models.github.ai/inference").rstrip("/")
        # Try both OpenAI-compatible and REST-style endpoints
        self.endpoint_primary = f"{self.base_url}/v1/chat/completions"
        self.endpoint_fallback = f"{self.base_url}/chat/completions"

        self.model = model or os.getenv("HOLODECK_MODEL", "openai/gpt-4o-mini")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        self.session = requests.Session()
        if trust_env is None:
            trust_env = os.getenv("HOLODECK_TRUST_ENV", "0").lower() in ("1", "true", "yes")
        self.session.trust_env = trust_env

    def _post(self, url, payload):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # GitHub recommends these:
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        r = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
        return r

    def __call__(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("No API key. Set GITHUB_TOKEN or OPENAI_API_KEY.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # Try primary (/v1/...) then fallback (/chat/completions)
        for url in (self.endpoint_primary, self.endpoint_fallback):
            r = self._post(url, payload)
            try:
                data = r.json()
            except Exception:
                if r.status_code in (401, 403):
                    raise RuntimeError(
                        f"Unauthorized at {url}. Check token (models:read) and daily limits. Body: {r.text[:300]}"
                    )
                # If path is wrong on this server, try the next url
                if r.status_code in (404, 405):
                    continue
                raise RuntimeError(f"Non-JSON response {r.status_code} from {url}: {r.text[:500]}")

            if r.status_code >= 300 or "error" in data:
                err = data.get("error", {})
                code = err.get("code")
                msg = err.get("message") or str(data)
                # Try fallback once if unknown_model arises on first URL
                if url == self.endpoint_primary and r.status_code in (404, 422):
                    continue
                raise RuntimeError(f"GitHub Models API error {r.status_code} ({code}): {msg[:300]}")

            return data["choices"][0]["message"]["content"]

        raise RuntimeError("Failed to reach a working chat/completions endpoint on GitHub Models.")
