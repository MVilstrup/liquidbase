import sys
from numbers import Number
from collections import deque
from collections.abc import Set, Mapping
import sys
import gc

ZERO_DEPTH_BASES = (str, bytes, Number, range, bytearray)


class ObjectSize:
    def __init__(self, s):
        self.kb = s // round(1e3, 2)
        self.mb = s // round(1e6, 2)
        self.gb = s // round(1e9, 2)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"{self.mb}MB"

    def __int__(self):
        return int(self.mb)

    def __float__(self):
        return self.mb


def get_size(obj):
    def actualsize(input_obj):
        memory_size = 0
        ids = set()
        objects = [input_obj]
        while objects:
            new = []
            for obj in objects:
                if id(obj) not in ids:
                    ids.add(id(obj))
                    memory_size += sys.getsizeof(obj)
                    new.append(obj)
            objects = gc.get_referents(*new)
        return memory_size

    return ObjectSize(actualsize(obj))
