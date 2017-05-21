# -*- coding: utf-8 -*-

import contextlib
import functools
import imp
import os
import shlex
import sysconfig

from IPython import get_ipython
from IPython.paths import get_ipython_cache_dir


@functools.lru_cache()
def is_kernel():
    """Check whether we are within kernel (notebook) environment."""
    return get_ipython().has_trait('kernel')


@functools.lru_cache()
def cache_dir():
    """Root cache directory for pybind11 extension."""
    root = os.path.abspath(os.path.expanduser(get_ipython_cache_dir()))
    return os.path.join(root, 'pybind11')


@functools.lru_cache()
def ext_suffix():
    """Get extension suffix for C extensions on this platform."""
    try:
        return imp.get_suffixes()[0][0]  # normally, this should not fail
    except:
        return sysconfig.get_config_var('EXT_SUFFIX') or sysconfig.get_config_var('SO')


def ext_path(*path):
    """Return an absolute path given a relative path within cache directory."""
    return os.path.join(cache_dir(), *path)


def pybind11_get_include():
    """Get pybind11 include paths if it's installed as a Python package."""
    try:
        import pybind11
        try:
            return [pybind11.get_include(True), pybind11.get_include(False)]
        except AttributeError:
            return []
    except ImportError:
        return []


def split_args(args, recursive=False):
    """Unquote arguments in the list using `shlex.split`."""
    if not args:
        return []
    result = []
    for arg in args:
        for s in shlex.split(arg):
            result.extend(shlex.split(s) if recursive else [s])
    return result


@contextlib.contextmanager
def with_env(**env_vars):
    """Context manager for overriding environment variables."""
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
