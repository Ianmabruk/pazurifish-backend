import os
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from dotenv import load_dotenv

load_dotenv()


class Config:
    _db_url = os.getenv('DATABASE_URL', 'sqlite:///pazurifish.db')
    # Render/Supabase/Neon provide postgres:// or postgresql:// — force psycopg (v3) driver
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif _db_url.startswith('postgresql://') and '+' not in _db_url.split('://')[0]:
        _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    # Remove unsupported query parameters for psycopg v3 (e.g., channel_binding)
    if _db_url.startswith('postgresql+psycopg://'):
        parsed = urlparse(_db_url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        # Remove channel_binding which is not supported by psycopg v3
        query_params.pop('channel_binding', None)
        new_query = urlencode(query_params, doseq=True)
        _db_url = urlunparse(parsed._replace(query=new_query))
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'development-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'development-jwt-secret')
    CDN_BASE_URL = os.getenv('CDN_BASE_URL', '')
    JSON_SORT_KEYS = False
