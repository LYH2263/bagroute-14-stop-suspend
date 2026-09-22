from app.services.pack_engine import StopItem, pack_route


def test_packs_in_route_order_splitting_bags():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 2.5, 3.0),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    assert len(result.bags) == 2
    assert [i.stop_id for i in result.bags[0].items] == [1]
    assert [i.stop_id for i in result.bags[1].items] == [2, 3]
    assert not result.rejects


def test_reject_oversized_stop():
    stops = [StopItem(1, 1, 9.0, 1.0, "大件"), StopItem(2, 2, 1.0, 1.0)]
    result = pack_route(stops, max_weight=5.0, max_volume=5.0)
    assert len(result.rejects) == 1
    assert result.rejects[0][0].stop_id == 1
    assert len(result.bags) == 1
    assert result.bags[0].items[0].stop_id == 2


def test_volume_cap_triggers_new_bag():
    stops = [StopItem(1, 1, 1.0, 4.0), StopItem(2, 2, 1.0, 4.0)]
    result = pack_route(stops, max_weight=10.0, max_volume=5.0)
    assert len(result.bags) == 2


def test_suspended_stop_in_neither_bags_nor_rejects():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 9.0, 1.0, "停投超大件", suspended=True),
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=4.0, max_volume=10.0)
    packed = [i.stop_id for b in result.bags for i in b.items]
    assert packed == [1, 3]
    # 停投站即使超限也不写入拒收
    assert not result.rejects


def test_resumed_stop_packs_again():
    suspended = pack_route(
        [StopItem(1, 1, 2.0, 3.0), StopItem(2, 2, 2.0, 2.0, suspended=True)],
        max_weight=4.0,
        max_volume=10.0,
    )
    assert [i.stop_id for b in suspended.bags for i in b.items] == [1]

    resumed = pack_route(
        [StopItem(1, 1, 2.0, 3.0), StopItem(2, 2, 2.0, 2.0, suspended=False)],
        max_weight=4.0,
        max_volume=10.0,
    )
    assert [i.stop_id for b in resumed.bags for i in b.items] == [1, 2]
    assert not resumed.rejects
