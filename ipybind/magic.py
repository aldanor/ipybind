# -*- coding: utf-8 -*_

from IPython.core.magic import Magics, magics_class, cell_magic


@magics_class
class Pybind11Magics(Magics):
    @cell_magic
    def pybind11(self, line, cell):
        return line, cell
