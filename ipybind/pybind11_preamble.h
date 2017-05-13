#include <pybind11/pybind11.h>

namespace py = pybind11;

#define _PYBIND11_PLUGIN(m) PYBIND11_PLUGIN(_PYBIND11_MODULE_NAME)
