"""Core 3.8b: the medium a station's documents live on, picked by its declaration.

TC3's MAIN declares one I_PersistMedium and hands it to the root, the set store
and the user table, so a project chooses where retained data lives without
touching a module. Here the declaration's `ConfigMedium` makes that choice and
the gateway opens it: the controller still owns every value and every
validation, the gateway owns the documents and the medium (Part III AB §3.8b).

The directory is deployment data, one per controller serial and root, never a
declaration literal. The file medium is the first and only implementation; a
database medium is the same interface and is refused until it is named.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import fraktal_ab_declaration as decl

SET_DIR_ENV = 'FRAKTAL_AB_CONFIG_SET_DIR'


class SetStore(Protocol):
    """The four named parameter-set documents (TC3 I_ConfigStore's documents).

    `FileStore` is the shipped implementation. A store moves documents and
    nothing else: it never validates a value or authorizes an operation, and
    every failure is an exception the broker turns into a controller receipt.
    """

    def read(self, name: str) -> list: ...
    def list(self) -> list: ...
    def save(self, document: list) -> None: ...
    def delete(self, name: str) -> None: ...


def directory(app, serial: str, environ=None) -> Path:
    """The set store's folder: one per commissioned root and controller serial."""
    environ = os.environ if environ is None else environ
    chosen = environ.get(SET_DIR_ENV)
    if chosen:
        return Path(chosen)
    base = Path(environ.get('LOCALAPPDATA', str(Path.home())))
    return base / 'Fraktal' / 'ConfigSets' / (serial + '-' + app.name)


def open_set_store(app, serial: str, environ=None) -> SetStore | None:
    """The set store this declaration chose, or None when it keeps no sets."""
    medium = decl.config_medium(app)
    if medium is None:
        return None
    if medium.store != decl.CONFIG_STORE_FILE_JSON:
        raise ValueError(f'configuration medium {medium.store} is not implemented')
    from fraktal_ab_sets import FileStore
    return FileStore(directory(app, serial, environ))
