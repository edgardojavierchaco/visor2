
"""
This module has been moved to :py:mod:`pyrocko.io.eventdata`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.eventdata\n')
    sys.stderr.write('           -> should now use: pyrocko.io.eventdata\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.eventdata\n')
    sys.stderr.write('              -> should now use: pyrocko.io.eventdata\n\n')
    raise ImportError('Pyrocko module "pyrocko.eventdata" has been renamed to "pyrocko.io.eventdata".')

from pyrocko.io.eventdata import *
