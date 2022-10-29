import datetime

import orjson as json
from liquidbase.db.liquid_db import LiquidDB


class Store:

    def __init__(self, location, parent=None, db=None, _id="", _data=None):
        self._location = location
        self._parent = parent
        self.ID = _id
        self._db = db if db is not None else LiquidDB(location)

        self._content = {}
        self._updated = {}
        self._deleted = {}

        self._populated = False if not _data else True
        self._last_stamp = None

        if _data is not None:
            for key, value in _data.items():
                self.__set__(key, value)

            self.save()

    @property
    def is_root(self):
        return self._parent is None and self.ID == ""

    @property
    def _parent_id(self):
        if self._parent is not None:
            return self._parent.ID
        return None

    @property
    def _should_update(self):
        if self._last_stamp is None:
            return True

        current_stamp = self._db.last_stamp(self.ID)
        if current_stamp != self._last_stamp:
            self.__update_stamp__(current_stamp)
            return True

        return False

    def _child(self, child_id, **value):
        child_id = f"{self.ID}.{child_id}" if self.ID else child_id
        return Store(self, parent=self, db=self._db, _id=child_id, _data=value)

    def __populate__(self):
        if not self._populated or self._should_update:
            if self._db.store_exists(self.ID):
                result, current_stamp = self._db.read(self.ID)
                self.__update_stamp__(current_stamp)

                for key, value in result.items():
                    if isinstance(value, dict):
                        value = self._child(key, **value)

                    self.__set__(key, value)
            self._populated = True

    def __set__(self, key, value):
        self._content[key] = value
        self._updated[key] = True
        self._deleted[key] = False

    def __unset__(self, key):
        self._deleted[key] = True
        self._updated.pop(key)
        return self._content.pop(key)

    def __update_stamp__(self, new_time):
        self._last_stamp = new_time

    def refresh(self):
        self._populated = False
        return self

    def save(self):
        to_update = {key: self._content[key] for key in self._updated.keys() if self._updated[key]}
        to_delete = [key for key, value in self._deleted.items() if value]

        store_keys = []
        for key, value in to_update.items():
            if isinstance(value, Store):
                value.save()
                store_keys.append(key)

        for key in store_keys:
            to_update.pop(key)

        if not self._db.store_exists(self.ID):
            self.__update_stamp__(self._db.create(self.ID, self._parent_id, **to_update))
        else:
            self.__update_stamp__(self._db.set(self.ID, **to_update))
            self.__update_stamp__(self._db.unset(self.ID, *to_delete))

            for key in to_update.keys():
                self._updated[key] = False

            for key in to_delete:
                self._deleted.pop(key)

    def keys(self):
        self.__populate__()
        all_keys = self._content.keys()
        return [k for k in all_keys if not self._deleted.get(k, False)]

    def values(self):
        self.__populate__()
        return [self[key] for key in self.keys()]

    def items(self):
        self.__populate__()
        return [(key, self[key]) for key in self.keys()]

    def pop(self, key):
        self.__populate__()
        if key not in self._content:
            return self._content.pop(key)

        value = self.__unset__(key)
        self.__update_stamp__(self._db.unset(self.ID, key))
        return value

    def get(self, key, default=None):
        self.__populate__()
        return self._content.get(key, default)

    def update(self, other):
        self.__populate__()
        assert isinstance(other, dict), "Can only update with a dictionary"
        for key, value in other.items():
            if isinstance(value, dict):
                value = self._child(key, **value)

            self.__set__(key, value)

        self.save()
        return self

    def clear(self):
        self._content.clear()
        self.__update_stamp__(self._db.clear(self.ID))

    def tree(self):
        from asciitree import LeftAligned

    def __setitem__(self, name, value):
        self.__populate__()
        if isinstance(value, dict):
            value = self._child(name, **value)

        self.__set__(name, value)
        self.save()

    def __getitem__(self, name):
        self.__populate__()
        return self._content[name]

    def __contains__(self, name):
        self.__populate__()
        return name in self._content

    def __len__(self):
        self.__populate__()
        return len(self._content)

    def __repr__(self):
        self.__populate__()
        info = {}
        for name, value in self._content.items():
            if name in ["__id__", "__root__"]:
                continue

            try:
                json.dumps(value)
                info[name] = value
            except TypeError:
                info[name] = str(value)

        return f"Store({json.dumps(info).decode('utf-8')})"

    def __str__(self):
        return f"Store"
