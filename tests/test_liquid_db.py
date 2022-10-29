from liquidbase.api.errors import StoreIDAlreadyExists
from liquidbase.db.liquid_db import LiquidDB
import pytest
import pandas as pd


def test_exists(db_location):
    # Ensure root can always be found
    db = LiquidDB(db_location)

    # Ensure no other ID can be found
    assert not db.store_exists("random")


def test_create_simple(db_location):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test", **data)

    assert db.store_exists("test")

    # Ensure only one element can be crated
    with pytest.raises(StoreIDAlreadyExists):
        db.create("test", **data)


def test_create_with_child(db_location):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": {"child": True}}
    db.create("test", **data)

    assert db.store_exists("test")
    assert db.store_exists("test.pew_pew")

    # Ensure only one element can be crated
    with pytest.raises(StoreIDAlreadyExists):
        db.create("test.pew_pew", **data)


def test_create_blob_from_type(db_location):
    db = LiquidDB(db_location)

    df = pd.DataFrame({"cool": ["stuff"]})
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "pandas": df}
    db.create("test", **data)

    assert db.store_exists("test")


def test_create_blob_from_size(db_location, big_list, big_list_hash):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "big": big_list}
    db.create("test", **data)

    assert db.store_exists("test")


def test_read_simple(db_location):
    db = LiquidDB(db_location)

    df = pd.DataFrame({"cool": ["stuff"]})
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "pandas": df}
    db.create("test__", **data)

    result, _ = db.read("test__")
    for key in data.keys():
        assert key in result
        assert type(data[key]) == type(result[key])

    assert data == data


def test_read_with_blob(db_location, big_list, big_list_hash):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "big": big_list}
    db.create("test_", **data)

    result, _ = db.read("test_")
    for key in data.keys():
        assert key in result
        assert type(data[key]) == type(result[key])

    assert len(result["big"]) == len(data["big"])


def test_set_simple(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)
    db.set("test_", cool="Not")
    result, _ = db.read("test_")
    assert result["cool"] == "Not"


def test_set_child(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)
    db.set("test_", cool={"child": 1})

    assert db.store_exists("test_.cool")
    result, _ = db.read("test_")
    assert result["cool"] == {"child": 1}


def test_set_overwrite_child(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": {"child": 1}}
    db.create("test_", **data)
    db.set("test_", pew_pew=[1.2, 3, 4])

    assert db.store_exists("test_")
    assert not db.store_exists("test_.pew_pew")
    result, _ = db.read("test_")
    assert result["pew_pew"] == [1.2, 3, 4]


def test_set_blob(db_location, big_list):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)
    db.set("test_", cool=big_list)

    assert db.blob_exists("test_.cool")
    result, _ = db.read("test_")
    assert len(result["cool"]) == len(big_list)
    assert type(result["cool"]) == type(big_list)


def test_set_overwrite_blob(db_location, big_list):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": big_list}
    db.create("test_", **data)
    db.set("test_", pew_pew=[1.2, 3, 4])

    assert db.store_exists("test_")
    assert not db.blob_exists("test_.pew_pew")

    pew, _ = db.read("test_")
    assert pew["pew_pew"] == [1.2, 3, 4]


def test_unset_simple(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)
    db.unset("test_", "cool")

    result, _ = db.read("test_")
    assert "cool" not in result


def test_unset_child(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": {"child": 1}}
    db.create("test_", **data)
    db.unset("test_", "pew_pew")

    result, _ = db.read("test_")
    assert "pew_pew" not in result
    assert not db.store_exists("test_.pew_pew")


def test_unset_blob(db_location, big_list):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": big_list}
    db.create("test_", **data)
    db.unset("test_", "pew_pew")

    result, _ = db.read("test_")
    assert "pew_pew" not in result
    assert not db.blob_exists("test_.pew_pew")


def test_delete_simple(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)
    assert db.store_exists("test_")

    db.delete("test_")

    assert not db.store_exists("test_")


def test_delete_with_child(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "child": {"cool": "stuff"}}
    db.create("test_", **data)
    assert db.store_exists("test_")
    assert db.store_exists("test_.child")

    db.delete("test_")

    assert not db.store_exists("test_")
    assert not db.store_exists("test_.child")


def test_delete_with_blob(db_location, big_list):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "big": big_list}
    db.create("test_", **data)

    assert db.store_exists("test_")
    assert db.blob_exists("test_.big")

    db.delete("test_")

    assert not db.store_exists("test_")
    assert not db.blob_exists("test_.big")


def test_clear_simple(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)
    assert db.store_exists("test_")

    db.clear("test_")

    assert db.store_exists("test_")
    result, _ = db.read("test_")
    assert result == {}


def test_clear_child(db_location):
    db = LiquidDB(db_location)
    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "child": {"cool": "stuff"}}
    db.create("test_", **data)
    assert db.store_exists("test_")
    assert db.store_exists("test_.child")

    db.clear("test_")

    assert db.store_exists("test_")
    assert not db.store_exists("test_.child")


def test_clear_blob(db_location, big_list):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4], "big": big_list}
    db.create("test_", **data)

    assert db.store_exists("test_")
    assert db.blob_exists("test_.big")

    db.clear("test_")

    assert db.store_exists("test_")
    assert not db.blob_exists("test_.big")


def test_stamp_is_updated(db_location):
    db = LiquidDB(db_location)

    data = {"cool": "Stuff", "and": 1, "man": 2.3, "pew_pew": [1.2, 3, 4]}
    db.create("test_", **data)

    last_updated = db.last_stamp("test_")

    db.set("test_", new="value")
    assert last_updated < db.last_stamp("test_")
