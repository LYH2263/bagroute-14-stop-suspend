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


def test_suspended_stop_is_neither_bagged_nor_rejected():
    stops = [
        StopItem(1, 1, 2.0, 3.0),
        StopItem(2, 2, 9.0, 1.0, "停投大件", suspended=True),  # 停投且超限：也不应进拒收
        StopItem(3, 3, 1.0, 1.0),
    ]
    result = pack_route(stops, max_weight=5.0, max_volume=10.0)
    bagged = [i.stop_id for b in result.bags for i in b.items]
    assert 2 not in bagged
    assert all(item.stop_id != 2 for item, _ in result.rejects)
    assert bagged == [1, 3]


def test_resumed_stop_is_packed_again():
    stop = StopItem(2, 2, 1.0, 1.0, "恢复投送", suspended=False)
    result = pack_route([stop], max_weight=5.0, max_volume=5.0)
    assert [i.stop_id for i in result.bags[0].items] == [2]
    assert not result.rejects
