from liquidbase.store import Store


def test_initialisation(db_location):
    store = Store(db_location)
    assert store.is_root


def test_insertion(db_location, big_list):
    store = Store(db_location)
    store["cool"] = "Stuff"
    store["child"] = {"cool": "man"}
    store["blob"] = big_list


def test_retrieval(db_location, big_list):
    store = Store(db_location)
    store["cool"] = "Stuff"
    assert store["cool"] == "Stuff"

    store["child"] = {"cool": "man"}
    assert "cool" in store["child"]
    assert store._db.store_exists("child")

    store["child"] = big_list
    assert store["child"] == big_list


def test_multi_access(db_location):
    store_a = Store(db_location)
    store_b = Store(db_location, db=store_a._db)

    store_a["cool"] = "stuff"

    assert store_b["cool"] == "stuff"

    store_a["cool"] = "other stuff"

    assert store_b["cool"] == "other stuff"