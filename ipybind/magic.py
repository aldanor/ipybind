# -*- coding: utf-8 -*_

import contextlib
import functools
import hashlib
import imp
import os
import re
import sys
import sysconfig
import tempfile

from distutils.errors import CompileError
from distutils.file_util import copy_file
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.paths import get_ipython_cache_dir

from ipybind.stream import forward


@functools.lru_cache()
def cache_dir():
    root = os.path.abspath(os.path.expanduser(get_ipython_cache_dir()))
    return os.path.join(root, 'pybind11')


class BuildExt(build_ext):
    def has_flag(self, flag):
        with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
            f.write('int main() { return 0; }')
            try:
                self.compiler.compile([f.name], extra_postargs=[flag])
            except CompileError:
                return False
        return True

    def build_extensions(self):
        opts = []
        if self.compiler.compiler_type == 'unix':
            if self.has_flag('-fvisibility=hidden'):
                opts.append('-fvisibility=hidden')
        for ext in self.extensions:
            ext.extra_compile_args.extend(opts)
        super().build_extensions()

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
    @argument('-i', '--prefix-include', action='store_true',
              help='Add $PREFIX/include to include path.')
    @argument('--cc',
              help='Set CC environment variable.')
    @argument('--cxx',
              help='Set CXX environment variable.')
    @argument('--compiler',
              help='Pass --compiler to distutils.')
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

    @contextlib.contextmanager
    def with_env(self, **env_vars):
        env_vars = {k: v for k, v in env_vars.items() if v is not None}
        env = os.environ.copy()
        for k, v in env_vars.items():
            os.environ[k] = v
        try:
            yield
        except:
            raise
        finally:
            for k in env_vars:
                if k not in env:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = env[k]

    def make_extension(self, module, source, args):
        include_dirs = [os.path.dirname(__file__)]
        try:
            import pybind11
            include_dirs.append(pybind11.get_include())
        except ImportError:
            pass
        if args.prefix_include:
            include_dirs.append(os.path.join(sys.prefix, 'include'))
        return Extension(
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

    def forward_handler(self, source):
        def handler(data):
            data = data.replace(source, '<source>')
            data = re.sub(r'^/.+/(pybind11/[\w_]+\.h:)', r'\1', data, flags=re.MULTILINE)
            return data
        return handler

    def build_module(self, module, source, args):
        with self.with_env(**{'CC': args.cc, 'CXX': args.cxx}):
            workdir = os.path.join(cache_dir(), module)
            os.makedirs(workdir, exist_ok=True)
            script_args = ['-v' if args.verbose else '-q']
            script_args += ['build_ext', '--inplace', '--build-temp', workdir]
            if args.compiler is not None:
                script_args += ['--compiler', args.compiler]
            with forward(self.forward_handler(source)):
                setup(
                    name=module,
                    ext_modules=[self.make_extension(module, source, args)],
                    script_args=script_args,
                    cmdclass={'build_ext': BuildExt}
                )

    def import_module(self, module, libfile):
        mod = imp.load_dynamic(module, libfile)
        for k, v in mod.__dict__.items():
            if not k.startswith('__'):
                self.shell.push({k: v})
