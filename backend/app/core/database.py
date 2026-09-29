from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models.entities import Base


class Database:
    def __init__(self, url: str):
        parsed = make_url(url)
        if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, ":memory:"):
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        kwargs = (
            {"connect_args": {"check_same_thread": False, "timeout": 30}}
            if parsed.get_backend_name() == "sqlite"
            else {}
        )
        self.engine = create_engine(url, pool_pre_ping=True, **kwargs)
        if parsed.get_backend_name() == "sqlite":

            @event.listens_for(self.engine, "connect")
            def configure_sqlite(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self):
        Base.metadata.create_all(self.engine)
