"""Security service unit test fixtures."""

import sys
from pathlib import Path

service_dir = Path(__file__).parent.parent.parent
if str(service_dir) not in sys.path:
    sys.path.insert(0, str(service_dir))