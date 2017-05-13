# -*- coding: utf-8 -*-

__version__ = '0.1.0'


def load_ipython_extension(ip):
    from ipybind.magic import Pybind11Magics
    from ipybind.notebook import setup_notebook

    ip.register_magics(Pybind11Magics)
    setup_notebook()
