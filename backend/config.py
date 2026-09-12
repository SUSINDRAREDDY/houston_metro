import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'metro.sqlite3'
GTFS_URL = os.getenv('GTFS_URL', 'https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip')
