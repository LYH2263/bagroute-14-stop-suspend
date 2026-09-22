"""停投（suspended）端到端行为：不入袋、不入拒收、状态持久、恢复后可再装。"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.router import bags, pack, rejects, set_suspension, stops
from app.database import Base
from app.models.models import DeliveryRoute, RejectRecord, SubscriberStop
from app.schemas.schemas import PackRequest, SuspensionUpdate


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def route(db):
    r = DeliveryRoute(name="测试线", max_weight_kg=5.0, max_volume_l=10.0)
    db.add(r)
    db.flush()
    db.add_all(
        [
            SubscriberStop(route_id=r.id, seq=1, name="正常站", weight_kg=1.0, volume_l=1.0),
            SubscriberStop(route_id=r.id, seq=2, name="停投站", weight_kg=2.0, volume_l=2.0),
            SubscriberStop(route_id=r.id, seq=3, name="超大件", weight_kg=9.0, volume_l=1.0),
        ]
    )
    db.commit()
    return r


def _stop_by_name(db, name):
    return db.scalar(select(SubscriberStop).where(SubscriberStop.name == name))


def _bagged_stop_ids(bag_out_list):
    return {item.stop_id for bag in bag_out_list for item in bag.items}


def test_suspended_stop_not_in_bags_nor_rejects(db, route):
    target = _stop_by_name(db, "停投站")
    set_suspension(target.id, SuspensionUpdate(suspended=True), db)

    out = pack(PackRequest(route_id=route.id), db)
    bagged = _bagged_stop_ids(out)
    assert target.id not in bagged

    reject_rows = db.scalars(select(RejectRecord)).all()
    assert reject_rows, "超大件应产生拒收，确保拒收表非空"
    assert all(r.stop_id != target.id for r in reject_rows)
    assert all(r.stop_name != "停投站" for r in reject_rows)


def test_suspension_persists_across_reads(db, route):
    target = _stop_by_name(db, "停投站")
    updated = set_suspension(target.id, SuspensionUpdate(suspended=True), db)
    assert updated.suspended is True

    # 模拟再次进入站点页：重新查询仍是停投
    db.expire_all()
    fetched = {s.id: s for s in stops(route_id=route.id, db=db)}
    assert fetched[target.id].suspended is True


def test_bags_and_rejects_endpoints_hide_suspended_stop(db, route):
    # 先正常装袋：停投站此时在袋中
    out = pack(PackRequest(route_id=route.id), db)
    target = _stop_by_name(db, "停投站")
    assert target.id in _bagged_stop_ids(out)

    # 装袋后才标记停投：袋明细与拒收列表也不应再看到该站名称
    set_suspension(target.id, SuspensionUpdate(suspended=True), db)
    bag_list = bags(db)
    assert all(i.stop_name != "停投站" for b in bag_list for i in b.items)
    assert all(r.stop_name != "停投站" for r in rejects(db))


def test_resumed_stop_is_packed_again(db, route):
    target = _stop_by_name(db, "停投站")
    set_suspension(target.id, SuspensionUpdate(suspended=True), db)
    out = pack(PackRequest(route_id=route.id), db)
    assert target.id not in _bagged_stop_ids(out)

    set_suspension(target.id, SuspensionUpdate(suspended=False), db)
    out = pack(PackRequest(route_id=route.id), db)
    assert target.id in _bagged_stop_ids(out)
