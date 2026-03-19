from __future__ import annotations

import sys

from .ui import build_main_window, create_application


def main() -> int:
    app = create_application(sys.argv)
    window = build_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
