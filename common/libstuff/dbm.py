# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

# pyright: reportUnnecessaryIsInstance=false

from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
import dbm.gnu as dbm
from pathlib import Path
from typing import Dict, AsyncGenerator, Optional, Type, Union

from pydantic import BaseModel, ValidationError


class DBMError(Exception):
    _msg: str

    def __init__(self, msg: Optional[str] = None) -> None:
        self._msg = msg if msg is not None else ""

    def __str__(self) -> str:
        return self._msg

    @property
    def msg(self) -> str:
        return self._msg


class DBM:

    _path: Path
    _lock: asyncio.Lock
    _db: "dbm._gdbm"  # type: ignore

    class Transaction:
        _dbm: DBM

        def __init__(self, dbm: DBM):
            self._dbm = dbm

        def get(
            self,
            *,
            ns: Optional[str] = None,
            key: str,
        ) -> Optional[str]:
            return self._dbm._get(ns, key)

        def get_model(
            self, *, ns: Optional[str] = None, key: str, model: Type[BaseModel]
        ) -> Optional[BaseModel]:
            return self._dbm._get_model(ns, key, model)

        def put(
            self,
            ns: Optional[str],
            key: str,
            value: Union[str, bytes, BaseModel],
        ) -> bool:
            return self._dbm._put(ns, key, value)

        def exists(self, ns: Optional[str], key: str) -> bool:
            return self._dbm._exists(ns, key)

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()
        self._lock = asyncio.Lock()

        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists() and not self._path.is_file():
            raise DBMError(
                f"path '{self._path}' already exists and is not a file."
            )

        self._db = dbm.open(self._path.as_posix(), "c")

    def __del__(self) -> None:
        self._db.close()

    def _get_key(self, ns: Optional[str], key: str) -> str:
        _ns = None if ns is None else ns.strip()
        if _ns is not None and len(_ns) == 0:
            raise DBMError("invalid namespace: can't be empty string.")

        _key = key.strip()
        if len(_key) == 0:
            raise DBMError("invalid key: can't be empty string.")

        return _key if _ns is None else f"{_ns}/{_key}"

    async def put(
        self,
        *,
        ns: Optional[str] = None,
        key: str,
        value: Union[str, bytes, BaseModel],
    ) -> bool:
        async with self._lock:
            return self._put(ns, key, value)

    def _put(
        self, ns: Optional[str], key: str, value: Union[str, bytes, BaseModel]
    ) -> bool:
        _key = self._get_key(ns, key)
        if isinstance(value, str) or isinstance(value, bytes):
            self._db[_key] = value
        elif isinstance(value, BaseModel):
            self._db[_key] = value.json()
        else:
            raise DBMError(f"invalid type on put: {type(value)}")
        return True

    async def get_model(
        self, *, ns: Optional[str] = None, key: str, model: Type[BaseModel]
    ) -> Optional[BaseModel]:
        async with self._lock:
            return self._get_model(ns, key, model)

    async def get(
        self,
        *,
        ns: Optional[str] = None,
        key: str,
    ) -> Optional[str]:
        async with self._lock:
            return self._get(ns, key)

    def _get_model(
        self, ns: Optional[str], key: str, model: Type[BaseModel]
    ) -> Optional[BaseModel]:
        _key = self._get_key(ns, key)
        if _key not in self._db:
            return None

        content = self._db[_key].decode("utf-8")
        try:
            value = model.parse_raw(content)
        except ValidationError:
            raise DBMError(
                f"unable to parse value for key '{_key}' as '{type(model)}."
            )
        return value

    def _get(self, ns: Optional[str], key: str) -> Optional[str]:
        _key = self._get_key(ns, key)
        if _key not in self._db:
            return None

        content = self._db[_key].decode("utf-8")
        return content

    async def exists(self, *, ns: Optional[str] = None, key: str) -> bool:
        async with self._lock:
            return self._exists(ns, key)

    def _exists(self, ns: Optional[str], key: str) -> bool:
        _key = self._get_key(ns, key)
        return _key in self._db

    async def entries(
        self,
        *,
        ns: Optional[str] = None,
        prefix: Optional[str] = None,
        model: Type[BaseModel | str] = str,
    ) -> Dict[str, Type[BaseModel | str]]:

        results_model: Dict[str, model] = {}

        _ns: Optional[str] = None
        if ns is not None:
            _ns = ns.strip()
            if len(_ns) == 0:
                raise DBMError("invalid namespace: empty string.")
            _ns = f"{_ns}/"

        _prefix: Optional[str] = None
        if prefix is not None:
            _prefix = prefix.strip()
            if len(_prefix) == 0:
                raise DBMError("invalid prefix: empty string.")

        async with self._lock:
            k = self._db.firstkey()
            while k is not None:
                _key = k.decode("utf-8")
                _key_entry = _key
                k = self._db.nextkey(k)
                if _ns is not None:
                    if not _key.startswith(_ns):
                        continue
                    else:
                        _key_entry = _key[len(_ns) :]
                if len(_key_entry) == 0:
                    raise DBMError(
                        f"empty key found: '{_key}' (namespace: {_ns})"
                    )
                if _prefix is not None and not _key_entry.startswith(_prefix):
                    continue

                assert _key in self._db
                _value: str = self._db[_key].decode("utf-8")
                if issubclass(model, BaseModel):
                    try:
                        results_model[_key_entry] = model.parse_raw(_value)  # type: ignore
                    except ValidationError:
                        raise DBMError(
                            f"unable to parse value for key '{_key}' "
                            f"(namespace: {_ns}) as model '{type(model)}'"
                        )
                elif isinstance(str(), model):
                    results_model[_key_entry] = _value

        return results_model  # type: ignore

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Transaction, None]:
        async with self._lock:
            tx = self.Transaction(self)
            yield tx
