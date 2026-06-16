"""必需字段的内置别名表。

若 CSV 中某个标准字段名缺失，但出现了下面任一别名（精确相等，不做子串/大小写转换），
工具会自动建立映射 alias → 标准名，无需用户手动传 --field-map。

新增别名时直接在 FIELD_ALIASES 中追加即可；优先级按列表顺序。
"""

FIELD_ALIASES: dict[str, list[str]] = {
    "exp_id":  ["exp", "eid"],
    "eshow":   ["eshows"],
    "click":   ["clicks"],
    "tcharge": ["total_target_charge"],
    "conv":    ["total_convert_num", "cv", "total_conv"],
}


def auto_apply_aliases(
    headers: list[str],
    standard_names: list[str],
    user_map: dict[str, str] | None,
) -> dict[str, str]:
    """为每个不在 headers 中的 standard_name，从 FIELD_ALIASES 找别名补齐。

    user_map 中已存在的键（alias）和值（已经被映射到的标准名）不会被覆盖。
    返回新增的 {alias: standard} 映射；调用方自己决定如何与 user_map 合并。
    """
    user_keys = set((user_map or {}).keys())
    user_values = set((user_map or {}).values())
    extra: dict[str, str] = {}
    for std in standard_names:
        if std in headers or std in user_values:
            continue
        for alias in FIELD_ALIASES.get(std, []):
            if alias in headers and alias not in user_keys:
                extra[alias] = std
                break
    return extra
