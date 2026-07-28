import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd

# Load environment variables
ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Client = None

def get_supabase_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment or analysis/.env")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def fetch_table_df(table_or_view: str, select_cols: str = "*", page_size: int = 1000) -> pd.DataFrame:
    """
    Fetches all rows from a Supabase table or view into a pandas DataFrame.
    Handles pagination automatically.
    """
    client = get_supabase_client()
    all_data = []
    start = 0
    
    while True:
        end = start + page_size - 1
        res = client.table(table_or_view).select(select_cols).range(start, end).execute()
        data = res.data
        if not data:
            break
        all_data.extend(data)
        if len(data) < page_size:
            break
        start += page_size
        
    return pd.DataFrame(all_data)
