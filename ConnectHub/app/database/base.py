# DECLARATIVE BASE THAT PROVIDES A CONSISTENT FOUNDATION FOR ALL DATABASE MODELS
from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names so Alembic migrations stay stable
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Timestamps are written by the application as UTC. MySQL DATETIME has no
# timezone and, without an explicit precision, only stores whole seconds; both
# matter for unread counts (created_at > last_read_at) and message ordering.
UTCDateTime = DateTime(timezone=True).with_variant(MySQLDateTime(fsp=6), "mysql")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
