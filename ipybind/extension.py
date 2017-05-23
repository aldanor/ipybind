# -*- coding: utf-8 -*-

import os
import sys

import setuptools

from ipybind.common import pybind11_get_include, is_win, is_osx


class Extension(setuptools.Extension):
    def __init__(self, module, sources, include_dirs=None, library_dirs=None,
                 libraries=None, extra_compile_args=None, cpp_std=None):
        ext_include_dirs = []
        ext_library_dirs = []
        ext_extra_compile_args = []
        ext_runtime_library_dirs = None

        # add ipybind/include folder which contains pybind11_preamble.h
        include = [os.path.join(os.path.dirname(__file__), 'include')]

        # add pybind11 include dirs if it's installed as a Python package
        include.extend(pybind11_get_include())

        # for conda environments, add conda-specific include/lib dirs
        if os.path.isdir(os.path.join(sys.prefix, 'conda-meta')):
            conda_lib_root = sys.prefix
            if is_win():
                conda_lib_root = os.path.join(sys.prefix, 'Library')
            include.append(os.path.join(conda_lib_root, 'include'))
            ext_library_dirs.append(os.path.join(conda_lib_root, 'lib'))

        # add pybind11 and conda include dirs as -isystem on gcc/clang
        if is_win():
            ext_include_dirs = include
        else:
            include = list(sum(zip(['-isystem'] * len(include), include), ()))
            ext_extra_compile_args.extend(include)

        # add user-specified include and library directories
        ext_include_dirs.extend(include_dirs or [])
        ext_library_dirs.extend(library_dirs or [])

        # on non-OSX / non-Windows, also set rpath if required
        if not is_win() and not is_osx():
            ext_runtime_library_dirs = library_dirs

        # add user-specified compile args
        ext_extra_compile_args.extend(extra_compile_args or [])

        # store C++ standard so it can be used by build_ext to figure out the flags
        self.cpp_std = cpp_std

        super().__init__(
            name=module,
            sources=sources,
            include_dirs=ext_include_dirs,
            library_dirs=ext_library_dirs,
            runtime_library_dirs=ext_runtime_library_dirs,
            extra_compile_args=ext_extra_compile_args,
            extra_link_args=[],
            libraries=libraries or [],
            language='c++',
            define_macros=[
                ('_IPYBIND_MODULE_NAME', module)
            ]
        )
