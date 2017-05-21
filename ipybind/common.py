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
    if os.name == 'nt':
        return imp.get_suffixes()[0][0]
    else:
        return sysconfig.get_config_var('EXT_SUFFIX')


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
        arg = arg.strip()
        if arg.startswith('"') and arg.endswith('"') and len(arg) >= 2:
            arg = arg[1:-1]
        if recursive:
            result.extend(shlex.split(arg))
        else:
            result.append(arg)
    return result


@contextlib.contextmanager
def override_vars(target, **override):
    """Context manager for overriding variables in an arbitrary dict."""
    override = {k: v for k, v in override.items() if v is not None}
    orig = target.copy()
    for k, v in override.items():
        target[k] = v
    try:
        yield
    finally:
        for k in override:
            if k not in orig:
                target.pop(k, None)
            else:
                target[k] = orig[k]
