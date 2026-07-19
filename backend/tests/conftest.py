import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.deps import get_db
from app.main import app
from app.models.base import Base
from app.seed import run_seed

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://examcraft:examcraft@localhost:55432/examcraft_test",
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    """Session chạy trong 1 transaction ngoài + savepoint lồng bên trong.

    Cho phép code ứng dụng gọi db.commit() (kết thúc savepoint) mà vẫn rollback
    sạch toàn bộ khi kết thúc test — cô lập test mà không cần tạo/xoá bảng mỗi lần.
    """
    connection = engine.connect()
    outer_trans = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_trans.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def seeded_db(db):
    run_seed(db)
    return db
