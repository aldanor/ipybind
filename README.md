![](https://travis-ci.org/aldanor/ipybind.svg?branch=master)
![](https://ci.appveyor.com/api/projects/status/github/aldanor/ipybind?branch=master&svg=true)

- [`%%pybind11`](#pybind11)
  - [Enabling the extension](#enabling-the-extension)
  - [Basic usage example](#basic-usage-example)
  - [Caching and recompilation](#caching-and-recompilation)
  - [Error reporting and verbosity](#error-reporting-and-verbosity)
  - [Setting C++ standard](#setting-c-standard)
  - [Compiler and linker flags](#compiler-and-linker-flags)
  - [Include and library directories](#include-and-library-directories)
  - [Build output verbosity](#build-output-verbosity)
- [Notebook integration](#notebook-integration)
- [Compatibility](#compatibility)

`ipybind` is an IPython extension that allows building and importing 
[`pybind11`](https://github.com/pybind/pybind11) modules in IPython environment, 
such as IPython console or Jupyter notebooks running a Python kernel.

### `%%pybind11`

#### Enabling the extension

To enable `ipybind` extension in the current kernel:

```python
%load_ext ipybind
```

In all examples that follow we assume that the extension has been previously loaded.

#### Basic usage example

```cpp
%%pybind11

PYBIND11_PLUGIN(example) {
    py::module m("example");
    m.def("add", [](int x, int y) { return x + y; });
    return m.ptr();
}
```

This will build the extension module and import all symbols from it into the current namespace:

```python
>>> add(1, 2)
3
```

#### Caching and recompilation

Each compiled module is assigned a hash based on the code contents, arguments to `%%pybind` magic and Python 
interpreter version. Sources for compiled modules and the binaries are stored under `$IPYTHONDIR/pybind11`
(on Linux / macOS it's `~/.ipython/pybind11` by default). If a compiled module binary with matching hash 
is found, it is not rebuilt and is instead imported directly.

It is also possible to force recompilation by assigning a new unique hash (this is useful, for instance, 
in cases when module's code depends on 3rd-party code that may change) – this can be done by passing 
`-f` flag:

```cpp
%pybind11 -f
```

#### Error reporting and verbosity

All compiler output is captured and shown in the IPython environment (as opposed to the standard
error of the shell where the kernel was launched). By default, compiler output is shown only if 
compilation fails; to always show all compiler output (like warnings), use `-v`  flag:

```cpp
%pybind11 -v
```

The following example should compile silently if built via `%%pybind11` with no arguments:

```cpp
%%pybind11 -vf;

PYBIND11_PLUGIN(example) {
    int x;                    // cell line 4
    py::module m("example");
    return m.ptr();
}
```

Building it with `-v` flag will display compiler warning:

```log
--------------------------------------------------------------------------------
<source>:4:9: warning: unused variable 'x' [-Wunused-variable]
    int x;
        ^
1 warning generated.
--------------------------------------------------------------------------------
```

As can be seen in the above example, line numbers in reported error and warning messages should
match line numbers in the input cell, including the cell magic line itself. (Line numbers can be 
shown in Jupyter notebooks by pressing `L` in command mode).

#### Setting C++ standard

If C++ standard is not specified, it defaults to C++14. If it's not supported by the compiler,
it falls back to C++11. It is also possible to specify the standard manually by passing `-std` 
option; for example:

```cpp
%%pybind11 -std=c++17
```

#### Compiler and linker flags

Additional compiler and linker flags can be passed via `-c` and `-Wl` options respectively.
Flags containing spaces or starting with a dash should be passed using `-c="..."` syntax; 
double quotes can be escaped via `\"`. Both of these options can be specified multiple times.

```cpp
%%pybind11 -c="-Wextra -fno-inline" -c="-Os"
```

On Linux and macOS, extensions are compiled with `-flto` and `-fvisibility=hidden` provided
those flags are supported by the compiler. On Windows, extensions are built with
`/MP /bigobj /EHsc`. The rest of the flags are provided by distutils.

#### Include and library directories

Include and library directories can be specified via `-I` and `-L` options. Both of these
options can be passed multiple times:

```cpp
%%pybind11 -v -I /foo/bar -I="/foo bar/baz" -L/baz
```

Note: in conda environments, `$PREFIX/include` is always added to include paths and
`$PREFIX/lib` is added to library paths (on Windows, it's `$PREFIX/Library/include`
and `$PREFIX/Library/lib`).

### Notebook integration

#### Syntax highlighting

Starting a cell with `%%pybind11` changes its syntax highlighting to C++ and enables 
additional visual styles (so that C/C++ keywords are highlighted).

#### Code indentation

Since the whole cell starting with `%%pybind11` is considered as C++ by syntax highlighter,
this also includes the cell magic itself (the very first line). If it's not terminated 
with a semicolon, the indentation on the following lines is likely to be off. For this 
reason, a trailing semilocon is always ignored, such as in this example:

```cpp
%%pybind11 -f -v;
```

### Compatibility

| OS | Python | Compiler requirements |
| --- | --- | --- |
| Linux | 3.4+ | GCC 4.8 or newer |
| macOS | 3.4+ | Clang 3.3 or newer |
| Windows | 3.5+ | MSVC 2015 Update 3 or newer |

#### Why no Python 2?

Python 2 support was [dropped](http://blog.jupyter.org/2017/04/19/release-of-ipython-6-0/#sunsettingpython2support) 
in IPython 6.x release entirely and the clock is [ticking](https://pythonclock.org) so it makes little sense for 
us to support it here either.

#### Python 3.5+ on Windows

Starting from Python 3.5, the official Windows distribution switched from MSVC 10.0 to MSVC 14.0 as a default
build toolchain. The former is too ancient to work with pybind11, so we require Python 3.5 or newer.

