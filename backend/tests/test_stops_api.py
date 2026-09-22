"""API 级停投测试：切换持久化、停投不进袋也不进拒收、恢复后可再装入。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import DeliveryRoute, SubscriberStop


@pytest.fixture()
def api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    route = DeliveryRoute(name="测试线", max_weight_kg=4.0, max_volume_l=10.0)
    db.add(route)
    db.flush()
    route_id = route.id
    db.add_all(
        [
            SubscriberStop(route_id=route_id, seq=1, name="甲站", weight_kg=2.0, volume_l=3.0),
            SubscriberStop(route_id=route_id, seq=2, name="乙站", weight_kg=2.5, volume_l=3.0),
            SubscriberStop(route_id=route_id, seq=3, name="丙站", weight_kg=1.0, volume_l=1.0),
            SubscriberStop(route_id=route_id, seq=4, name="超大件", weight_kg=9.5, volume_l=6.0),
        ]
    )
    db.commit()
    stop_ids = dict(
        db.execute(
            select(SubscriberStop.seq, SubscriberStop.id).where(
                SubscriberStop.route_id == route_id
            )
        ).all()
    )
    db.close()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # 不以上下文管理器方式使用，避免触发 lifespan 连接真实数据库
    yield TestClient(app), route_id, stop_ids
    app.dependency_overrides.clear()
    engine.dispose()


def _packed_ids(client, route_id):
    bags = client.post("/api/pack", json={"route_id": route_id}).json()
    return [item["stop_id"] for bag in bags for item in bag["items"]]


def test_toggle_suspension_persists_across_requests(api):
    client, route_id, stop_ids = api
    sid = stop_ids[2]
    r = client.patch(f"/api/stops/{sid}", json={"is_suspended": True})
    assert r.status_code == 200
    assert r.json()["is_suspended"] is True
    # 再次查询（重新进入页面）仍保持停投
    stops = client.get(f"/api/stops?route_id={route_id}").json()
    assert {s["id"]: s["is_suspended"] for s in stops}[sid] is True

    r = client.patch(f"/api/stops/{sid}", json={"is_suspended": False})
    assert r.json()["is_suspended"] is False
    stops = client.get(f"/api/stops?route_id={route_id}").json()
    assert {s["id"]: s["is_suspended"] for s in stops}[sid] is False


def test_suspend_unknown_stop_returns_404(api):
    client, _, _ = api
    r = client.patch("/api/stops/9999", json={"is_suspended": True})
    assert r.status_code == 404


def test_suspended_stop_in_neither_bags_nor_rejects(api):
    client, route_id, stop_ids = api
    # 基线：超大件超限，进入拒收
    client.post("/api/pack", json={"route_id": route_id})
    assert "超大件" in [r["stop_name"] for r in client.get("/api/rejects").json()]

    client.patch(f"/api/stops/{stop_ids[2]}", json={"is_suspended": True})
    client.patch(f"/api/stops/{stop_ids[4]}", json={"is_suspended": True})
    bags = client.post("/api/pack", json={"route_id": route_id}).json()
    packed = [item["stop_id"] for bag in bags for item in bag["items"]]
    names = [item["stop_name"] for bag in bags for item in bag["items"]]
    assert set(packed) == {stop_ids[1], stop_ids[3]}
    assert "乙站" not in names
    assert "超大件" not in names
    # 停投站（含超限的超大件）不写入拒收
    assert client.get("/api/rejects").json() == []


def test_resumed_stop_packs_again(api):
    client, route_id, stop_ids = api
    sid = stop_ids[2]
    client.patch(f"/api/stops/{sid}", json={"is_suspended": True})
    assert sid not in _packed_ids(client, route_id)

    client.patch(f"/api/stops/{sid}", json={"is_suspended": False})
    assert sid in _packed_ids(client, route_id)
