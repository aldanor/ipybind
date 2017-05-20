# -*- coding: utf-8 -*-

import pytest
import time

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


def module(code):
    return """PYBIND11_PLUGIN(test) {{
        py::module m("test");
        {}
        return m.ptr();
    }}""".format(code)


def test_pybind11_capture(ip, capsys):
    ip.run_line_magic('pybind11_capture', '')
    out, _ = capsys.readouterr()
    assert 'capturing is not available' in out


def test_import_all(ip):
    ip.run_cell_magic('pybind11', '-f', module("""
        m.attr("x") = py::cast(1);
        m.attr("_y") = py::cast(2);
        m.attr("__z") = py::cast(3);
    """))
    assert ip.user_ns['x'] == 1
    assert ip.user_ns['_y'] == 2
    assert '__z' not in ip.user_ns


def test_recompile(ip):
    mk_code = lambda: module("""
        m.def("f", []() { return 42; });
    // """ + str(time.time()))

    code = mk_code()
    ip.run_cell_magic('pybind11', '', code)
    f = ip.user_ns['f']
    assert f() == 42

    ip.run_cell_magic('pybind11', ';', code)
    assert f is ip.user_ns['f']

    ip.run_cell_magic('pybind11', '-f', code)
    assert f is not ip.user_ns['f']
    assert ip.user_ns['f']() == 42

    code = mk_code()
    ip.run_cell_magic('pybind11', '-f', code)
    f = ip.user_ns['f']
    assert f() == 42

    ip.run_cell_magic('pybind11', '', code)
    assert f is not ip.user_ns['f']
    assert ip.user_ns['f']() == 42
