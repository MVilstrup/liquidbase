import uuid
from datetime import datetime, timezone

import orjson as json

from sqlalchemy import (PickleType, Text, Column, ForeignKey, func,
                        create_engine, event, TypeDecorator, types, TIMESTAMP, DATETIME)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine

Base = declarative_base()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    dbapi_connection.isolation_level = None
    cursor.close()


class Json(TypeDecorator):

    @property
    def python_type(self):
        return object

    impl = types.BLOB
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_literal_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None


class Store(Base):
    __tablename__ = 'Store'
    id = Column(Text, primary_key=True)
    parent_id = Column(Text, ForeignKey("Store.id"), nullable=True)
    content = Column(Json)
    stamp = Column(Text, default=lambda: str(uuid.uuid4()), onupdate=lambda: str(uuid.uuid4()))

    blobs = relationship("Blob", lazy="joined")
    children = relationship("Store", lazy='select')


class Blob(Base):
    __tablename__ = 'Blob'

    id = Column(Text, primary_key=True)
    parent_id = Column(Text, ForeignKey("Store.id", ondelete="CASCADE"), nullable=False)
    content = Column(PickleType)
    hash = Column(PickleType)
    stamp = Column(Text, default=lambda: str(uuid.uuid4()), onupdate=lambda: str(uuid.uuid4()))


def create_model(location):
    engine = create_engine(f'sqlite:///{location}', echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
