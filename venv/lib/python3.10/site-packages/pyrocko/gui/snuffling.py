
"""
This module has been moved to :py:mod:`pyrocko.gui.snuffler.snuffling`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gui.snuffling\n')
    sys.stderr.write('           -> should now use: pyrocko.gui.snuffler.snuffling\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gui.snuffling\n')
    sys.stderr.write('              -> should now use: pyrocko.gui.snuffler.snuffling\n\n')
    raise ImportError('Pyrocko module "pyrocko.gui.snuffling" has been renamed to "pyrocko.gui.snuffler.snuffling".')

from pyrocko.gui.snuffler.snuffling import *
