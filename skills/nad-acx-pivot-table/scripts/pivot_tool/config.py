"""配置 dataclass 定义、JSON 加载与校验。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ColumnDef:
    name: str                           # 列名
    type: str                           # "str" | "int" | "float"
    nullable: bool = False              # 是否允许空值
    shared_items_type: str = "auto"     # "enumerated"|"range"|"mixed"|"auto"


@dataclass
class CalculatedFieldDef:
    name: str       # 计算字段名
    formula: str    # 公式 (如 "click /eshow")


@dataclass
class DataFieldDef:
    name: str                           # 显示名
    source_field: str                   # 来源字段（列名或计算字段名）
    aggregation: str = "sum"
    show_data_as: str = "normal"        # "normal"|"percentDiff"|...
    base_field: str | None = None       # percentDiff 的基准字段名
    base_item: int = 0
    num_fmt_id: int = 0


@dataclass
class PivotLayoutDef:
    row_fields: list[str]
    col_fields: list[str]
    data_fields: list[DataFieldDef]
    filter_fields: list[str] = field(default_factory=list)
    row_item_order: dict[str, list[str]] | None = None


@dataclass
class PivotConfig:
    name: str
    description: str
    columns: list[ColumnDef]
    calculated_fields: list[CalculatedFieldDef]
    pivot_layout: PivotLayoutDef
    data_sheet_name: str = "原始数据"
    pivot_sheet_name: str = "实验组数据透视"
    pivot_table_name: str = "数据透视表"
    pivot_style: str = "PivotStyleLight16"

    # ── 便利方法 ─────────────────────────────────────────────────

    def column_index(self, name: str) -> int:
        """按名称查找列索引，找不到时抛 ValueError。"""
        for i, c in enumerate(self.columns):
            if c.name == name:
                return i
        raise ValueError(f"Column not found: {name!r}")

    def column_by_name(self, name: str) -> ColumnDef:
        for c in self.columns:
            if c.name == name:
                return c
        raise ValueError(f"Column not found: {name!r}")

    def all_field_names(self) -> list[str]:
        """所有字段名（原始列 + 计算字段），顺序即为 cacheField 顺序。"""
        return [c.name for c in self.columns] + [cf.name for cf in self.calculated_fields]

    def field_index(self, name: str) -> int:
        """字段名 → cacheField 索引（含计算字段）。"""
        names = self.all_field_names()
        try:
            return names.index(name)
        except ValueError:
            raise ValueError(f"Field not found: {name!r}") from None

    @property
    def total_field_count(self) -> int:
        return len(self.columns) + len(self.calculated_fields)

    @property
    def str_col_indices(self) -> set[int]:
        return {i for i, c in enumerate(self.columns) if c.type == "str"}

    @property
    def int_col_indices(self) -> set[int]:
        return {i for i, c in enumerate(self.columns) if c.type == "int"}


# ── JSON → dataclass 转换 ────────────────────────────────────────


def _parse_data_field(d: dict) -> DataFieldDef:
    return DataFieldDef(
        name=d["name"],
        source_field=d["source_field"],
        aggregation=d.get("aggregation", "sum"),
        show_data_as=d.get("show_data_as", "normal"),
        base_field=d.get("base_field"),
        base_item=d.get("base_item", 0),
        num_fmt_id=d.get("num_fmt_id", 0),
    )


def _parse_layout(d: dict) -> PivotLayoutDef:
    return PivotLayoutDef(
        row_fields=d["row_fields"],
        col_fields=d["col_fields"],
        data_fields=[_parse_data_field(f) for f in d["data_fields"]],
        filter_fields=d.get("filter_fields", []),
        row_item_order=d.get("row_item_order"),
    )


def _parse_config(data: dict) -> PivotConfig:
    columns = [
        ColumnDef(
            name=c["name"],
            type=c["type"],
            nullable=c.get("nullable", False),
            shared_items_type=c.get("shared_items_type", "auto"),
        )
        for c in data["columns"]
    ]
    calc = [
        CalculatedFieldDef(name=cf["name"], formula=cf["formula"])
        for cf in data.get("calculated_fields", [])
    ]
    layout = _parse_layout(data["pivot_layout"])
    return PivotConfig(
        name=data["name"],
        description=data.get("description", ""),
        columns=columns,
        calculated_fields=calc,
        pivot_layout=layout,
        data_sheet_name=data.get("data_sheet_name", "原始数据"),
        pivot_sheet_name=data.get("pivot_sheet_name", "实验组数据透视"),
        pivot_table_name=data.get("pivot_table_name", "数据透视表"),
        pivot_style=data.get("pivot_style", "PivotStyleLight16"),
    )


def load_config(path: str | Path) -> PivotConfig:
    """从 JSON 文件加载配置。"""
    with open(path, "r", encoding="utf-8") as f:
        return _parse_config(json.load(f))


def load_preset(name: str) -> PivotConfig:
    """从内置预设加载配置。"""
    from pivot_tool.presets import get_preset_path

    path = get_preset_path(name)
    return load_config(path)


def validate_config(config: PivotConfig) -> list[str]:
    """校验配置，返回错误列表（空 = 合法）。"""
    errors: list[str] = []
    col_names = {c.name for c in config.columns}
    calc_names = {cf.name for cf in config.calculated_fields}
    all_names = col_names | calc_names

    for f in config.pivot_layout.row_fields:
        if f not in col_names:
            errors.append(f"row_fields 引用了不存在的列: {f!r}")
    for f in config.pivot_layout.col_fields:
        if f not in col_names and f != "__data__":
            errors.append(f"col_fields 引用了不存在的列: {f!r}")
    for df in config.pivot_layout.data_fields:
        if df.source_field not in all_names:
            errors.append(f"data_field {df.name!r} 引用了不存在的字段: {df.source_field!r}")
        if df.show_data_as != "normal" and df.base_field and df.base_field not in col_names:
            errors.append(f"data_field {df.name!r} 的 base_field 引用了不存在的列: {df.base_field!r}")
    for f in config.pivot_layout.filter_fields:
        if f not in col_names:
            errors.append(f"filter_fields 引用了不存在的列: {f!r}")

    valid_types = {"str", "int", "float"}
    for c in config.columns:
        if c.type not in valid_types:
            errors.append(f"列 {c.name!r} 的 type 无效: {c.type!r}，应为 {valid_types}")

    return errors
