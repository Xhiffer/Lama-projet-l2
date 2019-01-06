#copyright ReportLab Inc. 2000-2017
#see license.txt for license details
Version='3.5.12'

__version__=Version
__date__='20181130'
import sys

if sys.version_info[0:2]!=(2, 7) and sys.version_info<(3, 3):
    raise ImportError("""rlextra requires Python 2.7+ or 3.3+; 3.0-3.2 are not supported.""")

import reportlab
if reportlab.Version < Version:
	raise ImportError("""rlextra version %s requires at least reportlab 3.5.0, and you have reportlab %s; it is strongly recommended that you use the same versions""" % (Version, reportlab.Version))
