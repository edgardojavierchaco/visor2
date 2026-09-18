
"""
This module has been moved to :py:mod:`pyrocko.gui.util`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.gui_util\n')
    sys.stderr.write('           -> should now use: pyrocko.gui.util\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.gui_util\n')
    sys.stderr.write('              -> should now use: pyrocko.gui.util\n\n')
    raise ImportError('Pyrocko module "pyrocko.gui_util" has been renamed to "pyrocko.gui.util".')

from pyrocko.gui.util import *
