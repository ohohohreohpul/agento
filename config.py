import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

MODEL = "claude-opus-4-6"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Agento-SEO-Bot/1.0; "
        "+https://github.com/ohohohreohpul/agento)"
    )
}

REQUEST_TIMEOUT = 15
