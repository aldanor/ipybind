# -*- coding: utf-8 -*_

import functools
import hashlib
import imp
import os
import sys
import sysconfig

from distutils.file_util import copy_file
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
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
    @magic_arguments()
    @argument('-f', '--force', action='store_true',
              help='Force recompilation of the module.')
    @argument('-v', '--verbose', action='store_true',
              help='Display compilation output.')
    @argument('-std', choices=['c++11', 'c++14', 'c++17'], default='c++14',
              help='One of: c++11, c++14 or c++17. Default: c++14.')
    @argument('--prefix-include', action='store_true',
              help='Add $PREFIX/include to include path.')
    @cell_magic
    def pybind11(self, line, cell):
        """
        Compile and import everything from a pybind11 C++ code cell.

        The contents of the cell are written to a `.cpp` file in `$IPYTHONDIR/pybind11`
        directory using a filename based on the hash of the code. The file is compiled,
        and the symbols in the produced module are then imported directly into the
        current namespace.
        """

        line = line.strip().rstrip(';')
        args = parse_argstring(self.pybind11, line)
        module = 'pybind11_{}'.format(self.compute_hash(line, cell))
        code = self.format_code(cell)
        libfile = os.path.join(cache_dir(), module + self.ext_suffix)
        need_rebuild = not os.path.isfile(libfile) or args.force
        if need_rebuild:
            source = self.save_source(code, module)
            self.build_module(module, source, args)
        self.import_module(module, libfile)

    def compute_hash(self, line, cell):
        key = cell, line, sys.version_info, sys.executable
        return hashlib.md5(str(key).encode('utf-8')).hexdigest()[:7]

    def format_code(self, cell):
        code = cell.replace('PYBIND11_PLUGIN', '_PYBIND11_PLUGIN')
        code = '#include <pybind11_preamble.h>\n' + code
        code += '\n' * (not code.endswith('\n'))
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

    def build_module(self, module, source, args):
        include_dirs = [os.path.dirname(__file__)]
        try:
            import pybind11
            include_dirs.append(pybind11.get_include())
        except ImportError:
            pass
        if args.prefix_include:
            include_dirs.append(os.path.join(sys.prefix, 'include'))
        ext = Extension(
            name=module,
            sources=[source],
            include_dirs=include_dirs,
            library_dirs=[],
            extra_compile_args=[
                ('/std:' if os.name == 'nt' else '-std=') + args.std,
            ],
            extra_link_args=[],
            libraries=[],
            language='c++',
            define_macros=[
                ('_PYBIND11_MODULE_NAME', module)
            ]
        )
        workdir = os.path.join(cache_dir(), module)
        os.makedirs(workdir, exist_ok=True)
        args = ['-v' if args.verbose else '-q']
        args += ['build_ext', '--inplace', '--build-temp', workdir]
        setup(
            name=module,
            ext_modules=[ext],
            script_args=args,
            cmdclass={'build_ext': Pybind11BuildExt}
        )

    def import_module(self, module, libfile):
        mod = imp.load_dynamic(module, libfile)
        for k, v in mod.__dict__.items():
            if not k.startswith('__'):
                self.shell.push({k: v})
