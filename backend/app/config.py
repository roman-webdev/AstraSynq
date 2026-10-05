"""Fail closed on unsafe production configuration; never include values in errors."""
import os
from urllib.parse import urlsplit
from sqlalchemy.engine import make_url

VERSION = '0.5.0-rc.1'

def validate_environment(env=None):
    env = os.environ if env is None else env
    mode = env.get('ASTRASYNQ_MODE', 'development')
    if mode not in ('development', 'test', 'production'):
        raise RuntimeError('ASTRASYNQ_MODE must be development, test or production')
    if mode != 'production':
        return
    if env.get('AUTH_COOKIE_SECURE', '').lower() != 'true':
        raise RuntimeError('Production requires AUTH_COOKIE_SECURE=true')
    if env.get('AUTH_COOKIE_SAMESITE', 'lax') not in ('lax', 'strict'):
        raise RuntimeError('Production requires SameSite lax or strict')
    origins = env.get('AUTH_ALLOWED_ORIGINS', '').split(',')
    if not origins or any(urlsplit(o).scheme != 'https' or not urlsplit(o).hostname or urlsplit(o).path or urlsplit(o).query or urlsplit(o).fragment or urlsplit(o).username for o in origins):
        raise RuntimeError('Production requires explicit HTTPS origins without paths')
    if env.get('ASTRASYNQ_ALLOW_PRIVATE_WEBHOOKS', 'false').lower() != 'false':
        raise RuntimeError('Production forbids private webhook overrides')
    try:
        url = make_url(env.get('DATABASE_URL', ''))
        password = url.password or ''
        if url.get_backend_name() != 'postgresql' or len(password) < 16 or password.lower() in ('change-me-password', 'example-password', 'passwordpassword'):
            raise ValueError()
        if url.host not in ('db', 'localhost', '127.0.0.1', '::1') and url.query.get('sslmode') != 'verify-full':
            raise ValueError()
    except Exception:
        raise RuntimeError('Production requires PostgreSQL credentials; remote DB requires sslmode=verify-full') from None

def production():
    return os.getenv('ASTRASYNQ_MODE', 'development') == 'production'
