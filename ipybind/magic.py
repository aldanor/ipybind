# -*- coding: utf-8 -*_

import hashlib
import os
import re
import sys
import textwrap

from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.paths import get_ipython_cache_dir


@magics_class
class Pybind11Magics(Magics):
    @cell_magic
    def pybind11(self, line, cell):
        """
        Compile and import everything from a pybind11 C++ code cell.

        The contents of the cell are written to a `.cpp` file in `$IPYTHONDIR/pybind11`
        directory using a filename based on the hash of the code. The file is compiled,
        and the symbols in the produced module are then imported directly into the
        current namespace.
        """

        module = 'pybind11_{}'.format(self.compute_hash(line, cell))
        code = self.format_code(cell, module)
        filename = self.save_source(code, module)

    @property
    def cache_dir(self):
        root = os.path.abspath(os.path.expanduser(get_ipython_cache_dir()))
        return os.path.join(root, 'pybind11')

    def compute_hash(self, line, cell):
        key = cell, line, sys.version_info, sys.executable
        return hashlib.md5(str(key).encode('utf-8')).hexdigest()[:7]

    def format_code(self, cell, module):
        preamble = """
        #include <pybind11/pybind11.h>
        namespace py = pybind11;
        #define PYBIND11_PLUGIN_(m) PYBIND11_PLUGIN({})
        """.format(module)

        code = cell.replace('PYBIND11_PLUGIN', 'PYBIND11_PLUGIN_')
        code = textwrap.dedent(preamble) + code
        code = code.strip() + '\n'

        return code

    def save_source(self, code, module):
        filename = os.path.join(self.cache_dir, module + '.cpp')
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(filename, 'w') as f:
            f.write(code)
        return filename
