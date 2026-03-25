from __future__ import annotations

import sys

from .config import load_env
from .ui import build_main_window, create_application


def main() -> int:
    load_env()
    app = create_application(sys.argv)
    window = build_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
