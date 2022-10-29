from enum import Enum



class Location(Enum):
    store = "STORE"
    blob = "BLOB"


def generate_id(*ids):
    return ".".join(ids)
