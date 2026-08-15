
"""
This module has been moved to :py:mod:`pyrocko.gui.snuffler.pile_viewer`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gui.pile_viewer\n')
    sys.stderr.write('           -> should now use: pyrocko.gui.snuffler.pile_viewer\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gui.pile_viewer\n')
    sys.stderr.write('              -> should now use: pyrocko.gui.snuffler.pile_viewer\n\n')
    raise ImportError('Pyrocko module "pyrocko.gui.pile_viewer" has been renamed to "pyrocko.gui.snuffler.pile_viewer".')

from pyrocko.gui.snuffler.pile_viewer import *
