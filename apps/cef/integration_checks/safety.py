"""Barreras para pruebas offline y auditorías de lectura; sin mecanismos de escritura."""
import builtins
import hashlib
import importlib.abc
import io
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from unittest.mock import patch

CUES = ("220169000", "220169100")
STATUSES = frozenset(("PASS", "FAIL", "BLOCKED", "PARCIAL", "NO_CUBIERTA"))


class Blocked(Exception):
    pass


class Skipped(Exception):
    """Precondición sintética no representable; se informa NO_CUBIERTA."""


def require(condition, code):
    if not condition:
        raise Blocked(code)


def verify_sources(folder):
    manifest = json.loads((folder / "source_manifest.json").read_text("utf-8"))
    for name, digest in manifest.items():
        require(name.endswith(".py") and "/" not in name and "\\" not in name,
                "MANIFIESTO_INVALIDO")
        require(hashlib.sha256((folder.parent / name).read_bytes()).hexdigest() == digest,
                "FUENTES_CAMBIARON_REQUIERE_REVISION")


@contextmanager
def offline_guard():
    """Prohíbe Django/settings, drivers, red y procesos, incluso por accidente."""
    original = builtins.__import__
    folder = __import__("pathlib").Path(__file__).resolve().parent
    sources = set(json.loads((folder / "source_manifest.json").read_text("utf-8")))
    allowed = {folder.parent / name for name in sources}
    allowed |= {p for p in folder.iterdir() if p.suffix == ".py"}
    allowed.add(folder / "source_manifest.json")
    allowed = {str(p.resolve()).casefold() for p in allowed}
    original_open, original_io_open = builtins.open, io.open
    prohibited = ("django", "apps", "psycopg", "psycopg2", "sqlite3", "asyncpg",
                  "sqlalchemy", "pymysql", "MySQLdb", "_sqlite3", "_psycopg")

    def forbidden(name):
        return name.split(".")[0] in prohibited or "settings" in name.split(".")

    def guarded_import(name, *args, **kwargs):
        if forbidden(name):
            raise Blocked("IMPORTACION_PROHIBIDA_EN_OFFLINE")
        return original(name, *args, **kwargs)

    def denied(*args, **kwargs):
        raise Blocked("EFECTO_EXTERNO_PROHIBIDO_EN_OFFLINE")

    class ImportBarrier(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if forbidden(fullname):
                raise Blocked("IMPORTACION_PROHIBIDA_EN_OFFLINE")

    def checked_open(opener, file, mode="r", *args, **kwargs):
        if not isinstance(file, (str, os.PathLike)):
            raise Blocked("ARCHIVO_NO_AUTORIZADO_EN_OFFLINE")
        name = os.fspath(file)
        if name == os.devnull:
            return opener(file, mode, *args, **kwargs)
        if any(flag in mode for flag in "wax+"):
            raise Blocked("ESCRITURA_PROHIBIDA_EN_OFFLINE")
        if str(folder.__class__(name).resolve()).casefold() not in allowed:
            raise Blocked("LECTURA_NO_AUTORIZADA_EN_OFFLINE")
        return opener(file, mode, *args, **kwargs)

    require(not any(forbidden(name) for name in sys.modules), "PROCESO_NO_AISLADO")
    barrier = ImportBarrier()
    with ExitStack() as stack:
        sys.meta_path.insert(0, barrier)
        stack.callback(lambda: sys.meta_path.remove(barrier))
        stack.enter_context(patch.object(builtins, "open", lambda *a, **k: checked_open(original_open, *a, **k)))
        stack.enter_context(patch.object(io, "open", lambda *a, **k: checked_open(original_io_open, *a, **k)))
        stack.enter_context(patch.object(Path, "open", lambda path, *a, **k: checked_open(original_io_open, path, *a, **k)))
        stack.enter_context(patch.object(builtins, "__import__", guarded_import))
        for owner, name in ((socket, "getaddrinfo"), (socket, "gethostbyname"),
                            (socket, "gethostbyname_ex"), (socket.socket, "connect"), (socket.socket, "connect_ex"),
                            (socket.socket, "sendto"), (subprocess, "Popen"),
                            (os, "system"), (os, "open"), (os, "remove"), (os, "unlink"),
                            (os, "rename"), (os, "replace"), (os, "mkdir"),
                            (socket.socket, "bind"), (socket.socket, "listen"),
                            (threading.Thread, "start")):
            stack.enter_context(patch.object(owner, name, denied))
        yield


@contextmanager
def suppress_raw_output():
    previous = logging.root.manager.disable
    logging.disable(sys.maxsize)
    try:
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink), redirect_stderr(sink):
                yield
    finally:
        logging.disable(previous)


def safe_code(exc):
    # No incorpora str(exc), SQL, identidades ni tracebacks al informe.
    if isinstance(exc, Skipped):
        return "PRECONDICION_OFFLINE_NO_REPRESENTADA"
    if isinstance(exc, AssertionError):
        return "EXPECTATIVA_NO_CUMPLIDA"
    if isinstance(exc, Blocked):
        return "CONTROL_DE_SEGURIDAD_O_ADAPTADOR"
    return "ERROR_INTERNO_SANEADO"
