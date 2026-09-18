
"""
This module has been moved to :py:mod:`pyrocko.gui.snuffler.marker`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gui.marker\n')
    sys.stderr.write('           -> should now use: pyrocko.gui.snuffler.marker\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gui.marker\n')
    sys.stderr.write('              -> should now use: pyrocko.gui.snuffler.marker\n\n')
    raise ImportError('Pyrocko module "pyrocko.gui.marker" has been renamed to "pyrocko.gui.snuffler.marker".')

from pyrocko.gui.snuffler.marker import *
