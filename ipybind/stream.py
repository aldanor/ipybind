# -*- coding: utf-8 -*-

import contextlib
import sys

try:
    import fcntl
except ImportError:
    fcntl = None

from ipybind.common import is_kernel
from ipybind.ext.wurlitzer import Wurlitzer

_fwd = None


class Forwarder(Wurlitzer):
    def __init__(self, handler=None):
        self._data_handler = handler if handler is not None else lambda x: x
        super().__init__(stdout=sys.stdout, stderr=sys.stderr)

    def _handle_data(self, data, stream):
        data = self._data_handler(self._decode(data))
        if data and stream:
            stream.write(data)

    def _handle_stdout(self, data):
        self._handle_data(data, self._stdout)

    def _handle_stderr(self, data):
        self._handle_data(data, self._stderr)


@contextlib.contextmanager
def suppress():
    if fcntl:
        with Forwarder(handler=lambda _: None):
            yield
    else:
        yield


@contextlib.contextmanager
def forward(handler=None):
    global _fwd
    if _fwd is None and is_kernel() and fcntl:
        with Forwarder(handler=handler):
            yield
    else:
        yield


def start_forwarding(handler=None):
    global _fwd
    if fcntl:
        if _fwd is None:
            _fwd = Forwarder(handler=handler)
        _fwd.__enter__()


def stop_forwarding(handler=None):
    global _fwd
    if fcntl:
        if _fwd is not None:
            _fwd.__exit__(None, None, None)
            _fwd = None
