# -*- coding: utf-8 -*-

# ipybind includes have to be first so distutils.spawn is patched
from ipybind.common import override_vars
from ipybind.spawn import spawn_capture

import os
import pytest
import tempfile
import sys
import time

import distutils.ccompiler
import distutils.sysconfig

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


def test_link_external(ip):
    with tempfile.TemporaryDirectory() as root_dir:
        lib_dir = os.path.join(root_dir, 'lib dir')
        os.makedirs(lib_dir)
        cpp = os.path.join(lib_dir, 'foo.cpp')
        with open(cpp, 'w') as f:
            f.write('namespace baz { int foo(int x) { return x * 10; } }\n')
        inc_dir = os.path.join(root_dir, 'inc dir')
        os.makedirs(inc_dir)
        hdr = os.path.join(inc_dir, 'foo.h')
        with open(hdr, 'w') as f:
            f.write('namespace baz { int foo(int x); }\n')

        config = distutils.sysconfig.get_config_vars()
        override = {}
        if sys.platform == 'darwin':
            override['LDSHARED'] = config.get('LDSHARED', '').replace('-bundle', '-dynamiclib')
        with override_vars(config, **override):
            compiler = distutils.ccompiler.new_compiler()
            distutils.sysconfig.customize_compiler(compiler)
            with spawn_capture():
                objects = compiler.compile([cpp], output_dir=lib_dir)
                if os.name == 'nt':
                    linker = compiler.create_static_lib
                else:
                    linker = compiler.link_shared_lib
                linker(objects, 'foo', lib_dir, target_lang='c++')

        flags = '-f -I "{}" -L "{}" -l foo'.format(inc_dir, lib_dir)
        ip.run_cell_magic('pybind11', flags, """
        #include <foo.h>

        PYBIND11_PLUGIN(foo) {
            py::module m("foo");
            m.def("bar", [](int x) { return baz::foo(x); });
            return m.ptr();
        }
        """)

        assert ip.user_ns['bar'](42) == 420
