# -*- coding: utf-8 -*_

import contextlib
import hashlib
import imp
import os
import re
import sys
import time
import warnings

from setuptools import setup, Extension

from IPython.core.magic import Magics, magics_class, cell_magic, line_magic, on_off
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from ipybind.build_ext import build_ext
from ipybind.common import ext_suffix, ext_path, is_kernel, split_args, pybind11_get_include
from ipybind.stream import start_forwarding, stop_forwarding


@magics_class
class Pybind11Magics(Magics):
    @magic_arguments()
    @argument('-f', '--force', action='store_true',
              help='Force recompilation of the module.')
    @argument('-v', '--verbose', action='store_true',
              help='Display compilation output.')
    @argument('-std', choices=['c++11', 'c++14', 'c++1z', 'c++17'],
              help='C++ standard, defaults to C++14 if available.')
    @argument('--cc',
              help='Set CC environment variable.')
    @argument('--cxx',
              help='Set CXX environment variable.')
    @argument('--compiler',
              help='Pass --compiler to distutils.')
    @argument('-c', '--compile-args', action='append', default=[], metavar='ARGS',
              help='Extra flags to pass to the compiler.')
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
        code = self.format_code(cell)
        module = 'pybind11_{}'.format(self.compute_hash(code, args))
        libfile = ext_path(module + ext_suffix())
        need_rebuild = not os.path.isfile(libfile) or args.force
        if need_rebuild:
            source = self.save_source(code, module)
            self.build_module(module, source, args)
        self.import_module(module, libfile)

    @line_magic
    def pybind11_capture(self, parameter_s=''):
        """
        Control the automatic capturing of C++ stdout and stderr streams.

        To enable:  `%pybind11_capture 1` or `%pybind11_capture on`.
        To disable: `%pybind11_capture 0` or `%pybind11_capture off`.
        To toggle:  `%pybind11_capture`.
        """

        if not is_kernel():
            print('C++ stdout/stderr capturing is not available in the terminal environment.')
            return

        p = parameter_s.strip().lower()
        if p:
            try:
                capture = {'off': 0, '0': 0, 'on': 1, '1': 1}[p]
            except KeyError:
                print('Incorrect argument. Use on/1, off/0, or nothing for a toggle.')
                return
        else:
            capture = not getattr(self.shell, 'pybind11_capture', False)
        self.shell.pybind11_capture = capture
        (start_forwarding if capture else stop_forwarding)()
        print('C++ stdout/stderr capturing has been turned', on_off(capture))

    def compute_hash(self, code, args):
        args = vars(args).copy()
        args['version_info'] = sys.version_info
        args['executable'] = sys.executable
        args['code'] = code
        args.pop('verbose', None)
        if args.pop('force', False):
            # Force-rebuilding changes the hash on Windows; we have to do that because
            # python.exe keeps open handles to the loaded .pyd files, and we can't
            # overwrite them safely. On Linux / macOS overwriting the .so files
            # seems to work fine, however importing the module with the same name as
            # already imported module may be flaky, so we have to make it unique too.
            args['timestamp'] = int(round(time.time() * 1e6))
        key = str(sorted(args.items()))
        return hashlib.md5(key.encode('utf-8')).hexdigest()[:7]

    def format_code(self, cell):
        code = cell.replace('PYBIND11_PLUGIN', '_PYBIND11_PLUGIN')
        code = code.replace('PYBIND11_MODULE', '_PYBIND11_MODULE')
        code = '#include <pybind11_preamble.h>\n' + code
        code += '\n' * (not code.endswith('\n'))
        return code

    def save_source(self, code, module):
        filename = ext_path(module + '.cpp')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write(code)
        return filename

    @contextlib.contextmanager
    def with_env(self, **env_vars):
        env_vars = {k: v for k, v in env_vars.items() if v is not None}
        env = os.environ.copy()
        for k, v in env_vars.items():
            os.environ[k] = v
        try:
            yield
        finally:
            for k in env_vars:
                if k not in env:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = env[k]

    def make_extension(self, module, source, args):
        include_dirs = [os.path.join(os.path.dirname(__file__), 'include')]
        include_dirs += pybind11_get_include()
        extension = Extension(
            name=module,
            sources=[source],
            include_dirs=include_dirs,
            library_dirs=[],
            extra_compile_args=split_args(args.compile_args),
            extra_link_args=[],
            libraries=[],
            language='c++',
            define_macros=[
                ('_IPYBIND_MODULE_NAME', module)
            ]
        )
        extension.args = args
        return extension

    def build_module(self, module, source, args):
        with self.with_env(**{'CC': args.cc, 'CXX': args.cxx}):
            workdir = ext_path(module)
            os.makedirs(workdir, exist_ok=True)
            script_args = ['-v' if args.verbose else '-q']
            script_args += ['build_ext', '--inplace', '--build-temp', workdir]
            if args.force:
                script_args.append('--force')
            if args.compiler is not None:
                script_args += ['--compiler', args.compiler]
            warnings.filterwarnings('ignore', 'To exit')
            setup(
                name=module,
                ext_modules=[self.make_extension(module, source, args)],
                script_args=script_args,
                cmdclass={'build_ext': build_ext}
            )

    def import_module(self, module, libfile):
        mod = imp.load_dynamic(module, libfile)
        for k, v in mod.__dict__.items():
            if not k.startswith('__'):
                self.shell.push({k: v})
