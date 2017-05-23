# -*- coding: utf-8 -*-

import contextlib
import os
import re
import sys
import tempfile

import distutils.errors
import distutils.file_util
import distutils.log
import setuptools.command.build_ext

from ipybind.common import cache_path
from ipybind.spawn import spawn_capture


class build_ext(setuptools.command.build_ext.build_ext):
    @property
    def is_unix(self):
        return self.compiler.compiler_type == 'unix'

    @property
    def is_msvc(self):
        return self.compiler.compiler_type == 'msvc'

    @contextlib.contextmanager
    def silence(self):
        verbose = self.compiler.verbose
        self.compiler.verbose = 0
        level = distutils.log.set_threshold(5)
        try:
            with spawn_capture('never'):
                yield
        finally:
            self.compiler.verbose = verbose
            distutils.log.set_threshold(level)

    def has_flag(self, flag):
        with tempfile.TemporaryDirectory() as d:
            cpp = os.path.join(d, 'test.cpp')
            with open(cpp, 'w') as f:
                f.write('int main() { return 0; }')
            try:
                with self.silence():
                    self.compiler.compile([f.name], extra_postargs=[flag], output_dir=d)
            except distutils.errors.CompileError:
                return False
        return True

    def std_flags(self, std):
        if self.is_msvc:
            if std == 'c++11':  # cl.exe is always at least C++11
                return []
            elif std is not None:
                if not self.has_flag('/std:' + std):
                    sys.exit('Compiler does not seem to support ' + std.upper())
                return ['/std:' + std]
            elif self.has_flag('/std:c++14'):
                return ['/std:c++14']
            return []
        if std is not None:
            if not self.has_flag('-std=' + std):
                sys.exit('Compiler does not seem to support ' + std.upper())
            return ['-std=' + std]
        elif self.has_flag('-std=c++14'):
            return ['-std=c++14']
        elif self.has_flag('-std=c++11'):
            return ['-std=c++11']
        sys.exit('Unsupported compiler: at least C++11 support is required')

    def remove_flag(self, flag):
        for target in ('compiler', 'compiler_so'):
            cmd = getattr(self.compiler, target)
            if flag in cmd:
                cmd.remove(flag)

    def format_log(self, log):
        for ext in self.extensions:
            for source in ext.sources:
                log = log.replace(source, '<source>')
                basename = os.path.basename(source)
                log = re.sub('^' + re.escape(basename) + r'\s+', '', log)
        log = re.sub(r'^/.+/(pybind11/[\w_]+\.h:)', r'\1',
                     log, flags=re.MULTILINE)
        log = re.sub(r'^/.+/pybind11_preamble.h:', 'pybind11_preamble.h:',
                     log, flags=re.MULTILINE)
        return log

    def build_extensions(self):
        if self.is_unix:
            self.remove_flag('-Wstrict-prototypes')  # may be an invalid flag on gcc
        for ext in self.extensions:
            compile_args = self.std_flags(ext.args.std)
            link_args = []
            if self.is_unix:  # gcc / clang
                if self.has_flag('-fvisibility=hidden'):
                    # set the default symbol visibility to hidden to obtain smaller binaries
                    compile_args.append('-fvisibility=hidden')
                if self.has_flag('-flto'):
                    # enable link-time optimization if available
                    compile_args.append('-flto')
                    link_args.append('-flto')
            elif self.is_msvc:  # msvc
                compile_args.append('/MP')      # enable multithreaded builds
                compile_args.append('/bigobj')  # because of 64k addressable sections limit
                compile_args.append('/EHsc')    # catch synchronous C++ exceptions only
            ext.extra_compile_args = compile_args + ext.extra_compile_args
            ext.extra_link_args = link_args + ext.extra_link_args
        with spawn_capture(self.verbose and 'always' or 'on_error', fmt=self.format_log,
                           log_commands=bool(self.verbose)):
            super().build_extensions()

    def copy_extensions_to_source(self):
        for ext in self.extensions:
            filename = self.get_ext_filename(self.get_ext_fullname(ext.name))
            src = os.path.join(self.build_lib, filename)
            dest = cache_path(os.path.basename(filename))
            distutils.file_util.copy_file(
                src, dest, verbose=self.verbose, dry_run=self.dry_run)
