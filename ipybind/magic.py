# -*- coding: utf-8 -*_

import functools
import hashlib
import os
import shutil
import sys
import sysconfig
import textwrap

from distutils.file_util import copy_file
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.paths import get_ipython_cache_dir


@functools.lru_cache()
def cache_dir():
    root = os.path.abspath(os.path.expanduser(get_ipython_cache_dir()))
    return os.path.join(root, 'pybind11')


class Pybind11BuildExt(build_ext):
    def copy_extensions_to_source(self):
        for ext in self.extensions:
            filename = self.get_ext_filename(self.get_ext_fullname(ext.name))
            src = os.path.join(self.build_lib, filename)
            dest = os.path.join(cache_dir(), os.path.basename(filename))
            copy_file(src, dest, verbose=self.verbose, dry_run=self.dry_run)


@magics_class
class Pybind11Magics(Magics):
    @cell_magic
    def pybind11(self, line, cell):
        """
        Compile and import everything from a pybind11 C++ code cell.

        The contents of the cell are written to a `.cpp` file in `$IPYTHONDIR/pybind11`
        directory using a filename based on the hash of the code. The file is compiled,
        and the symbols in the produced module are then imported directly into the
        current namespace.
        """

        module = 'pybind11_{}'.format(self.compute_hash(line, cell))
        code = self.format_code(cell, module)
        libfile = os.path.join(cache_dir(), module + self.ext_suffix)
        need_rebuild = not os.path.isfile(libfile)
        if need_rebuild:
            source = self.save_source(code, module)
            self.build_module(module, source)

    def cache_dir(self):
        root = os.path.abspath(os.path.expanduser(get_ipython_cache_dir()))
        return os.path.join(root, 'pybind11')

    def compute_hash(self, line, cell):
        key = cell, line, sys.version_info, sys.executable
        return hashlib.md5(str(key).encode('utf-8')).hexdigest()[:7]

    def format_code(self, cell, module):
        preamble = """
        #include <pybind11/pybind11.h>
        namespace py = pybind11;
        #define PYBIND11_PLUGIN_(m) PYBIND11_PLUGIN({})
        """.format(module)

        code = cell.replace('PYBIND11_PLUGIN', 'PYBIND11_PLUGIN_')
        code = textwrap.dedent(preamble) + code
        code = code.strip() + '\n'

        return code

    def save_source(self, code, module):
        filename = os.path.join(cache_dir(), module + '.cpp')
        os.makedirs(cache_dir(), exist_ok=True)
        with open(filename, 'w') as f:
            f.write(code)
        return filename

    @property
    def ext_suffix(self):
        return sysconfig.get_config_var('EXT_SUFFIX') or sysconfig.get_config_var('SO')

    def build_module(self, module, source):
        import pybind11
        ext = Extension(
            name=module,
            sources=[source],
            include_dirs=[pybind11.get_include()],
            library_dirs=[],
            extra_compile_args=['-std=c++14'],
            extra_link_args=[],
            libraries=[],
            language='c++'
        )
        workdir = os.path.join(cache_dir(), module)
        os.makedirs(workdir, exist_ok=True)
        args = ['build_ext', '--inplace', '--build-temp', workdir, '--build-lib', workdir]
        setup(
            name=module,
            ext_modules=[ext],
            script_args=args,
            cmdclass={'build_ext': Pybind11BuildExt}
        )
        shutil.rmtree(workdir)
