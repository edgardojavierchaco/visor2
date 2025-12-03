
"""
This module has been moved to :py:mod:`pyrocko.plot.response`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.response_plot\n')
    sys.stderr.write('           -> should now use: pyrocko.plot.response\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.response_plot\n')
    sys.stderr.write('              -> should now use: pyrocko.plot.response\n\n')
    raise ImportError('Pyrocko module "pyrocko.response_plot" has been renamed to "pyrocko.plot.response".')

from pyrocko.plot.response import *
