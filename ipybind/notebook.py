# -*- coding: utf-8 -*-

from IPython.core.display import Javascript, HTML, display_javascript, display_html


def setup_notebook():
    # assign text/x-c++src MIME type to pybind11 cells
    code = """
    require(['notebook/js/codecell'], function(cc) {
        cc.CodeCell.options_default.highlight_modes['magic_text/x-c++src'] =
            {reg: [/^\s*%%pybind11/]};
    });
    """
    display_javascript(Javascript(data=code))

    # assign non-black colour to C/C++ keywords
    html = """
    <style>
    .cm-s-ipython span.cm-variable-3 {
        color: #208ffb;
    }
    </style>
    """
    display_html(HTML(data=html))
