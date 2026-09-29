import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_retry_session(
    retries: int = 5,
    backoff_factor: float = 1.0,
    status_forcelist: tuple = (408, 429, 500, 502, 503, 504),
    session: requests.Session = None
) -> requests.Session:
    """Returns a requests.Session with retry logic and exponential backoff."""
    session = session or requests.Session()
    
    retry_strategy = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
