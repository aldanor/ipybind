# -*- coding: utf-8 -*-

import functools
import os
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
    return sysconfig.get_config_var('EXT_SUFFIX') or sysconfig.get_config_var('SO')


def ext_path(*path):
    """Return an absolute path given a relative path within cache directory."""
    return os.path.join(cache_dir(), *path)
