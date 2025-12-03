
"""
This module has been moved to :py:mod:`pyrocko.io.enhanced_sacpz`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.fdsn.enhanced_sacpz\n')
    sys.stderr.write('           -> should now use: pyrocko.io.enhanced_sacpz\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.fdsn.enhanced_sacpz\n')
    sys.stderr.write('              -> should now use: pyrocko.io.enhanced_sacpz\n\n')
    raise ImportError('Pyrocko module "pyrocko.fdsn.enhanced_sacpz" has been renamed to "pyrocko.io.enhanced_sacpz".')

from pyrocko.io.enhanced_sacpz import *
