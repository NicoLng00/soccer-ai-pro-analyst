"""Create or update the database roles from the SAP_DB_URL_* variables (development and CI only).

Thin wrapper around soccer_analyst.db.provision, which the integration tests reuse.
"""

from __future__ import annotations

import sys

from soccer_analyst.core.config import load_database_settings
from soccer_analyst.core.errors import ConfigError
from soccer_analyst.db.provision import provision_roles


def main() -> None:
    try:
        for line in provision_roles(load_database_settings()):
            print(line)
    except ConfigError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
