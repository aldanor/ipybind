# -*- coding: utf-8 -*-

import pytest

from IPython.testing.globalipapp import get_ipython
from IPython.core.history import HistoryManager


@pytest.fixture(scope='session')
def kernel():
    HistoryManager.enabled = False
    ip = get_ipython()
    ip.extension_manager.load_extension('ipybind')
    return ip


@pytest.fixture(scope='function')
def ip(kernel):
    kernel.reset()
    return kernel


def test_pybind11_capture(ip, capsys):
    ip.run_line_magic('pybind11_capture', '')
    out, _ = capsys.readouterr()
    assert 'capturing is not available' in out
