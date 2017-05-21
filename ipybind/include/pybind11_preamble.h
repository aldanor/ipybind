#include <pybind11/pybind11.h>

namespace py = pybind11;

#define _PYBIND11_PLUGIN(name) PYBIND11_PLUGIN(_IPYBIND_MODULE_NAME)
#define _PYBIND11_MODULE(name, m) PYBIND11_MODULE(_IPYBIND_MODULE_NAME, m)
