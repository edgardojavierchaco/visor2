
"""
This module has been moved to :py:mod:``.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.fdsn.__init__\n')
    sys.stderr.write('           -> should now use: \n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.fdsn.__init__\n')
    sys.stderr.write('              -> should now use: \n\n')
    raise ImportError('Pyrocko module "pyrocko.fdsn.__init__" has been renamed to "".')

