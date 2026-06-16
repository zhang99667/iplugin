"""支持 `python -m z_agent` 形式启动 CLI。"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
