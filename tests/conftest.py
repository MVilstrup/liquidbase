# content of conftest.py

import pytest
import pickle


_big_list = [1 for i in range(13000000)]

@pytest.fixture(scope="session")
def big_list():
    return _big_list

@pytest.fixture(scope="session")
def big_list_hash():
    return hash(pickle.dumps(_big_list))

@pytest.fixture(scope="session")
def db_location():
    return ':memory:'