import os
import time
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

def get_supabase_client(force_new: bool = False) -> Client:
    global _client
    if _client is None or force_new:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment or analysis/.env")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def fetch_table_df(table_or_view: str, select_cols: str = "*", page_size: int = 1000, max_retries: int = 3) -> pd.DataFrame:
    """
    Fetches all rows from a Supabase table or view into a pandas DataFrame.
    Handles pagination and retries network disconnects automatically.
    """
    all_data = []
    start = 0
    
    while True:
        end = start + page_size - 1
        data = None
        
        for attempt in range(max_retries):
            try:
                client = get_supabase_client(force_new=(attempt > 0))
                res = client.table(table_or_view).select(select_cols).range(start, end).execute()
                data = res.data
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Error fetching {table_or_view} (attempt {attempt+1}/{max_retries}): {e}")
                    raise e
                time.sleep(1.0 * (attempt + 1))
        
        if not data:
            break
        all_data.extend(data)
        if len(data) < page_size:
            break
        start += page_size
        
    return pd.DataFrame(all_data)
