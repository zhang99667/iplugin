"""预设配置注册与加载。"""

from pathlib import Path

PRESETS_DIR = Path(__file__).parent


def list_presets() -> list[str]:
    """列出所有可用的预设名称。"""
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def get_preset_path(name: str) -> Path:
    """获取预设 JSON 文件路径，不存在时抛 FileNotFoundError。"""
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        available = list_presets()
        raise FileNotFoundError(
            f"预设 {name!r} 不存在。可用预设: {available}"
        )
    return path
