
"""
This module has been moved to :py:mod:`pyrocko.plot.cake_plot`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.cake_plot\n')
    sys.stderr.write('           -> should now use: pyrocko.plot.cake_plot\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.cake_plot\n')
    sys.stderr.write('              -> should now use: pyrocko.plot.cake_plot\n\n')
    raise ImportError('Pyrocko module "pyrocko.cake_plot" has been renamed to "pyrocko.plot.cake_plot".')

from pyrocko.plot.cake_plot import *
