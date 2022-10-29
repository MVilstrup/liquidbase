import pickle
from uuid import uuid4

import orjson as json
import pandas as pd
import numpy as np
import dill
from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype

from liquidbase.api.errors import StoreIDAlreadyExists
from liquidbase.api.memory import get_size
from liquidbase.constants import Location, generate_id
from liquidbase.db.model import Store, Blob, create_model


class LiquidDB:
    def __init__(self, location):
        self._session = create_model(location)

    @property
    def session(self):
        return self._session.begin()

    @staticmethod
    def _determine_placement(value):
        # Make blob if data is of complicated types
        if isinstance(value, (pd.DataFrame, pd.Series, np.ndarray)):
            return Location.blob, value

        # Store None if NaN value or None value
        try:
            if pd.isna(value) or value is None:
                return Location.store, None
        except:
            pass

        # Make blob if data takes too up much space
        # TODO: Find a better way of calculating object size
        if get_size(value).mb > 100:
            return Location.blob, value

        # Store if simple typed
        simple_typed = any([
            isinstance(value, (str, int, float, bool)),
            is_string_dtype(value),
            is_numeric_dtype(value),
            is_bool_dtype(value)
        ])

        if simple_typed:
            return Location.store, value

        # Store (if possible) if it cannot be pickled
        if not dill.pickles(value):
            return Location.store, value

        # As default action try to parse it with json, if possible store it otherwise blob it
        try:
            json.dumps(value)
            return Location.store, value
        except:
            return Location.blob, value

    def _divide_data(self, data):
        content, children, blobs = {}, {}, {}
        for key, value in data.items():
            if isinstance(value, dict):
                children[key] = value
                continue

            location, value = self._determine_placement(value)
            if location == Location.store:
                content[key] = value
            elif location == Location.blob:
                blobs[key] = value
            else:
                raise Exception()

        return content, children, blobs

    def create(self, ID, parent_id=None, **data):
        if self.store_exists(ID):
            raise StoreIDAlreadyExists(f"{ID} already exists")

        content, children, blobs = self._divide_data(data)

        if not parent_id and "." in ID:
            parent_id = ".".join(ID.split(".")[:-1])

        with self.session as session:
            # Add primary value
            session.add(Store(id=ID, parent_id=parent_id, content=content))

            # Add all Blobs
            for key, blob in blobs.items():
                pickled = pickle.dumps(blob)
                session.add(Blob(id=generate_id(ID, key), parent_id=ID, content=pickled, hash=hash(pickled)))

        # Add all children with new session
        for key, child in children.items():
            self.create(generate_id(ID, key), parent_id=ID, **child)

        return self.last_stamp(ID)

    def store_exists(self, ID):
        with self.session as session:
            return bool(session.query(Store.id).filter_by(id=ID).first() is not None)

    def blob_exists(self, ID):
        with self.session as session:
            return bool(session.query(Blob.id).filter_by(id=ID).first() is not None)

    def last_stamp(self, ID):
        with self.session as session:
            stamp = session.query(Store.stamp).filter_by(id=ID).first()
            if stamp is None:
                raise Exception()

            return stamp[0]

    def read_field(self, ID, name):
        with self.session as session:
            record = session.query(Store).filter_by(id=ID).first()

            if name in record.content:
                return record.content[name], record.stamp

            for blob in record.blobs:
                blob_key = blob.id.split(".")[-1]
                if name == blob_key:
                    return blob.content, record.stamp

            for child in record.children:
                child_key = child.id.split(".")[-1]
                if name == child_key:
                    return child.content, record.stamp

    def read(self, ID):
        with self.session as session:
            record = session.query(Store).filter_by(id=ID).first()
            if record is None:
                raise Exception()

            content = record.content

            # Fetch all children:
            for child in record.children:
                child_key = child.id.split(".")[-1]
                content[child_key] = child.content

            # Fetch all blobs
            for blob in record.blobs:
                blob_key = blob.id.split(".")[-1]
                content[blob_key] = pickle.loads(blob.content)

            return content, record.stamp

    def set(self, ID, **data):
        # TODO: Improve updates of the underlying json
        with self.session as session:
            record = session.query(Store).filter_by(id=ID).first()
            if record is None:
                raise Exception()

            orig_content = {key: value for key, value in record.content.items()}

            records = list(record.children) + list(record.blobs)

            for key, value in data.items():
                new_id = generate_id(ID, key)
                for child_record in records:
                    if child_record.id == new_id:
                        session.delete(child_record)

                if isinstance(value, dict):
                    session.add(Store(id=new_id, parent_id=ID, content=value))
                    if key in orig_content:
                        orig_content.pop(key)
                    continue

                location, value = self._determine_placement(value)
                if location == Location.store:
                    orig_content[key] = value
                elif location == Location.blob:
                    if key in orig_content:
                        orig_content.pop(key)

                    pickled = pickle.dumps(value)
                    pickle_hash = hash(pickled)
                    session.add(Blob(id=new_id, parent_id=ID, content=pickled, hash=pickle_hash))
                else:
                    raise Exception()

            record.content = orig_content
            record.stamp = str(uuid4())

        return self.last_stamp(ID)

    def unset(self, ID, *fields):
        # TODO: Improve updates of the underlying json
        with self.session as session:
            record = session.query(Store).filter_by(id=ID).first()
            if record is None:
                raise Exception()

            record.content = {key: value for key, value in record.content.items() if key not in fields}

            # Handle if one of the fields is a store on its own
            IDs = {generate_id(ID, field) for field in fields}

            overwritten = []
            for child in record.children:
                if child.id in IDs:
                    overwritten.append(child.id)

            for blob in record.blobs:
                if blob.id in IDs:
                    session.delete(blob)

            record.stamp = str(uuid4())

        for child_ID in overwritten:
            self.delete(child_ID)

        return self.last_stamp(ID)

    def delete(self, ID):
        if not self.store_exists(ID):
            raise Exception()

        with self.session as session:
            all_blobs = []
            all_records = []

            current_records = [session.query(Store).filter_by(id=ID).first()]
            while current_records:
                found_records = []
                for record in current_records:
                    all_blobs += list(record.blobs)
                    found_records += list(record.children)

                all_records += current_records
                current_records = found_records

            for record in all_records + all_blobs:
                session.delete(record)

    def clear(self, ID):
        self.delete(ID)
        self.create(ID)
        return self.last_stamp(ID)
