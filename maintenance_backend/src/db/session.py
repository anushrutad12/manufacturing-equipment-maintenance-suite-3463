from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.settings import get_settings


def _build_mysql_sqlalchemy_url() -> str:
    """Build SQLAlchemy MySQL URL from env vars.

    We intentionally do NOT parse db_connection.txt at runtime; we follow platform-provided
    env vars: MYSQL_URL, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT.

    MYSQL_URL may be:
      - hostname
      - hostname:port
      - mysql://hostname:port (some orchestrators include protocol)

    MYSQL_PORT, if provided, overrides any port embedded in MYSQL_URL.
    """
    s = get_settings()
    if not (s.mysql_url and s.mysql_user and s.mysql_password and s.mysql_db):
        raise RuntimeError(
            "MySQL env vars missing. Required: MYSQL_URL, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB. "
            "Optional: MYSQL_PORT."
        )

    host = s.mysql_url.strip()

    # Tolerate protocol prefixes in MYSQL_URL
    for prefix in ("mysql://", "http://", "https://"):
        if host.startswith(prefix):
            host = host[len(prefix) :]
            break

    port = s.mysql_port

    # If MYSQL_URL already includes :port, keep it unless MYSQL_PORT is explicitly provided.
    if port:
        if ":" in host:
            host = host.split(":", 1)[0]
        hostport = f"{host}:{port}"
    else:
        hostport = host

    return f"mysql+pymysql://{s.mysql_user}:{s.mysql_password}@{hostport}/{s.mysql_db}?charset=utf8mb4"


_ENGINE: Engine | None = None
_SessionLocal: sessionmaker | None = None


# PUBLIC_INTERFACE
def get_engine() -> Engine:
    """Get (or create) the global SQLAlchemy engine."""
    global _ENGINE, _SessionLocal
    if _ENGINE is None:
        url = _build_mysql_sqlalchemy_url()
        _ENGINE = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_ENGINE)
    return _ENGINE


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session and ensures close()."""
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for non-FastAPI use (scripts/background tasks)."""
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
