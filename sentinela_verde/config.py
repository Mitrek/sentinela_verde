# config.py
from dotenv import load_dotenv
import os

load_dotenv()

FIRMS_API_KEY: str = os.getenv("FIRMS_API_KEY", "")
REGION_BBOX: str   = os.getenv("REGION_BBOX", "-51.5,-23.3,-39.0,-14.0")
FETCH_DAYS: int    = int(os.getenv("FETCH_DAYS", "1"))
FETCH_INTERVAL_MINUTES: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "5"))
DB_PATH: str       = os.getenv("DB_PATH", "fire_catcher.db")
HOST: str          = os.getenv("HOST", "0.0.0.0")
PORT: int          = int(os.getenv("PORT", "8000"))

if not FIRMS_API_KEY:
    raise ValueError("FIRMS_API_KEY is required. Set it in your .env file.")

# INPE Queimadas KML feed (optional complementary source)
INPE_ENABLED: bool = os.getenv("INPE_ENABLED", "true").lower() in ("1", "true", "yes")
INPE_KML_URL: str  = os.getenv("INPE_KML_URL", "https://dataserver-coids.inpe.br/queimadas/queimadas/eventos/ativos/eventos_ativos.kml")
INPE_FETCH_INTERVAL_MINUTES: int = int(os.getenv("INPE_FETCH_INTERVAL_MINUTES", "5"))
