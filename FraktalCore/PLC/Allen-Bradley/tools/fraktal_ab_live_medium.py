"""Core 3.8b live documents on the host medium, declaration-free.

The keyed documents, the index of confirmed keys and the two failure kinds a
restore distinguishes. Shared by the engineering keeper (`fraktal_ab_live`)
and the host adapter, which knows a root only by its published name.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fraktal_ab_set_documents as sets

LIVE_NAME = '_live'  # TC3's SetName for live documents
INDEX_NAME = 'index.json'
INDEX_SCHEMA = 'fraktal.ab.live-documents'
INDEX_VERSION = 1
STORE_OK, STORE_LOST = 1, 2  # the station load's StoreResult


class MediumUnreadable(OSError):
    """The medium did not answer. Retry; never treat it as "nothing there"."""


class DocumentLost(ValueError):
    """A confirmed document is missing, or a document does not parse."""


def keys(root, line, models):
    """The document keys of one root: its station, its line if any, and models 1..n."""
    return [f'{root}.station', *([f'{root}.line'] if line else []), *(f'{root}.model{i}' for i in range(1, models + 1))]


def content(document):
    """What a document says, without when it was written."""
    header = {k: v for k, v in document[0].items() if k not in ('created', 'clock')}
    return json.dumps([header, *document[1:]], sort_keys=True, separators=(',', ':'))


class FileMedium:
    """Keyed live documents in one folder, plus the index of confirmed keys.

    Each document is the existing JSON-lines set document, written atomically
    by the set store's own replacement; the index is written after it, so a
    crash between the two leaves a valid newer document and an older index.
    """
    def __init__(self, directory):
        self.directory = Path(directory)

    def _path(self, key):
        sets._text(key, sets.NAME_MAX, nonempty=True)
        return self.directory / (hashlib.sha256(key.encode('ascii')).hexdigest() + '.jsonl')

    def index(self):
        path = self.directory / INDEX_NAME
        try:
            text = path.read_text(encoding='ascii')
        except FileNotFoundError:
            return {}
        except OSError as error:
            raise MediumUnreadable(f'live document index unreadable: {error}') from error
        try:
            held = json.loads(text)
            if (held.get('schema'), held.get('schemaVersion')) != (INDEX_SCHEMA, INDEX_VERSION):
                raise ValueError('schema')
            confirmed = held['documents']
            if not isinstance(confirmed, dict) or any(
                    not isinstance(v, dict) or type(v.get('generation')) is not int for v in confirmed.values()):
                raise ValueError('documents')
            return confirmed
        except (ValueError, KeyError, AttributeError, UnicodeError) as error:
            # Which keys were confirmed is unknown: a loss could not be told
            # from a first start, so the medium has not answered.
            raise MediumUnreadable('live document index is damaged') from error

    def read(self, key):
        """The document, None if never confirmed, or DocumentLost."""
        confirmed = self.index()
        path = self._path(key)
        try:
            if path.is_symlink():
                raise DocumentLost(f'{key}: store symlink')
            if path.stat().st_size > (sets.MAX_RECORDS + 1) * (sets.LINE_MAX + 1):
                raise DocumentLost(f'{key}: document exceeds capacity')
            text = path.read_text(encoding='ascii')
        except FileNotFoundError:
            if key in confirmed:
                raise DocumentLost(f'{key}: confirmed document is missing') from None
            return None
        except (UnicodeError, ValueError) as error:
            raise DocumentLost(f'{key}: {error}') from error
        except OSError as error:
            raise MediumUnreadable(f'{key}: {error}') from error
        try:
            return sets.checked_document([sets.parse_line(line) for line in text.splitlines()])
        except sets.SetRejected as error:
            raise DocumentLost(f'{key}: {error}') from error

    def write(self, key, document):
        document = sets.checked_document(document)
        text = '\n'.join(sets.render_line(v) for v in document) + '\n'
        confirmed = self.index()
        sets.replace_text(self.directory, self._path(key), text)
        entry = confirmed.get(key, {'generation': 0})
        confirmed[key] = {'generation': entry['generation'] + 1,
                          'sha256': hashlib.sha256(text.encode('ascii')).hexdigest()}
        index = {'schema': INDEX_SCHEMA, 'schemaVersion': INDEX_VERSION, 'documents': confirmed}
        sets.replace_text(self.directory, self.directory / INDEX_NAME,
                          json.dumps(index, sort_keys=True, indent=1) + '\n')
