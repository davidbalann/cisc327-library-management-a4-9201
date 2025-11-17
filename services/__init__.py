"""Services package initializer.

Also provides a compatibility alias so tests that reference
"library_service" (without the "services." prefix) point to the same
module object as "services.library_service".
"""

import sys

# Import the actual module so we can alias it in sys.modules
from . import library_service as _library_service  # noqa: F401

# Ensure both names resolve to the same module object
sys.modules.setdefault('library_service', _library_service)
