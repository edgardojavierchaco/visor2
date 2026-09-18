
"""
This module has been moved to :py:mod:`pyrocko.io.resp`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.fdsn.resp\n')
    sys.stderr.write('           -> should now use: pyrocko.io.resp\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.fdsn.resp\n')
    sys.stderr.write('              -> should now use: pyrocko.io.resp\n\n')
    raise ImportError('Pyrocko module "pyrocko.fdsn.resp" has been renamed to "pyrocko.io.resp".')

from pyrocko.io.resp import *
