# -*- coding: utf-8 -*-

import contextlib
import sys

from ipybind.common import is_kernel
from ipybind.ext.wurlitzer import Wurlitzer

_fwd = None


class Forwarder(Wurlitzer):
    def __init__(self, handler=None):
        self._data_handler = handler if handler is not None else lambda x: x
        super().__init__(stdout=sys.stdout, stderr=sys.stderr)

    def _handle_stdout(self, data):
        self._stdout.write(self._data_handler(self._decode(data)))

    def _handle_stderr(self, data):
        self._stderr.write(self._data_handler(self._decode(data)))


@contextlib.contextmanager
def forward(handler=None):
    global _fwd
    if _fwd is None and is_kernel():
        with Forwarder(handler=handler):
            yield
    else:
        yield


def start_forwarding(handler=None):
    global _fwd
    if _fwd is None:
        _fwd = Forwarder(handler=handler)
    _fwd.__enter__()


def stop_forwarding(handler=None):
    global _fwd
    if _fwd is not None:
        _fwd.__exit__(None, None, None)
        _fwd = None
