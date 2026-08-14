"""透视字段枚举 items 的完整性回归测试。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from pivot_tool.config import (  # noqa: E402
    ColumnDef,
    DataFieldDef,
    PivotConfig,
    PivotLayoutDef,
)
from pivot_tool.csv_reader import FieldMaps  # noqa: E402
from pivot_tool.ooxml_guard import NS, validate_pivot_xlsx  # noqa: E402
from pivot_tool.packager import create_xlsx_with_pivot  # noqa: E402
from pivot_tool.pivot_table import (  # noqa: E402
    _ordered_enum_values,
    build_pivot_table_xml,
)


def _config() -> PivotConfig:
    """构造包含 3 个枚举值的最小透视配置。"""
    return PivotConfig(
        name="pivot-items-test",
        description="",
        columns=[
            ColumnDef("segment", "str", shared_items_type="enumerated"),
            ColumnDef("metric", "int", shared_items_type="range"),
        ],
        calculated_fields=[],
        pivot_layout=PivotLayoutDef(
            row_fields=["segment"],
            col_fields=["__data__"],
            data_fields=[DataFieldDef("指标", "metric")],
            row_item_order={"segment": ["b"]},
        ),
    )


def _field_maps() -> FieldMaps:
    return FieldMaps(
        headers=["segment", "metric"],
        rows=[["a", "1"], ["b", "2"], ["c", "3"]],
        enumerated_items={0: ["a", "b", "c"]},
        item_index_maps={0: {"a": 0, "b": 1, "c": 2}},
        stats={1: (1, 3)},
    )


def _rewrite_zip_part(path: Path, part: str, transform) -> None:
    """重写一个 OOXML 部件，用于注入可控损坏。"""
    with zipfile.ZipFile(path, "r") as source:
        contents = {name: source.read(name) for name in source.namelist()}
    contents[part] = transform(contents[part].decode("utf-8")).encode("utf-8")

    rewritten = path.with_name(f".{path.name}.rewrite")
    with zipfile.ZipFile(rewritten, "w", zipfile.ZIP_DEFLATED) as target:
        for name, content in contents.items():
            target.writestr(name, content)
    os.replace(rewritten, path)


class PivotItemsTest(unittest.TestCase):
    def test_configured_order_matches_string_case_and_numeric_text(self) -> None:
        """排序配置允许大小写差异，也允许用 JSON 字符串表达数字。"""
        self.assertEqual(
            ["EXP", "dz"],
            _ordered_enum_values(["dz", "EXP"], ["exp"]),
        )
        self.assertEqual(
            [20260806, 20260805],
            _ordered_enum_values([20260805, 20260806], ["20260806"]),
        )

    def test_partial_row_item_order_keeps_unlisted_values(self) -> None:
        root = ET.fromstring(build_pivot_table_xml(_config(), _field_maps()))
        pivot_field = root.find(f"{NS}pivotFields/{NS}pivotField")
        self.assertIsNotNone(pivot_field)
        assert pivot_field is not None
        items = pivot_field.find(f"{NS}items")
        self.assertIsNotNone(items)
        assert items is not None

        # 配置只指定 b；a/c 仍需按原枚举顺序补在后面。
        self.assertEqual(
            ["1", "0", "2"],
            [item.get("x") for item in items.findall(f"{NS}item") if item.get("x") is not None],
        )
        self.assertEqual("4", items.get("count"))
        self.assertEqual(4, len(items.findall(f"{NS}item")))
        self.assertEqual(
            1,
            len([item for item in items.findall(f"{NS}item") if item.get("t") == "default"]),
        )

        row_items = root.find(f"{NS}rowItems")
        self.assertIsNotNone(row_items)
        assert row_items is not None
        self.assertEqual("4", row_items.get("count"))
        self.assertEqual(4, len(row_items.findall(f"{NS}i")))

    def test_guard_rejects_items_count_not_matching_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_path = root / "input.csv"
            output = root / "output.xlsx"
            csv_path.write_text(
                "segment,metric\n"
                "a,1\n"
                "b,2\n"
                "c,3\n",
                encoding="utf-8",
            )
            create_xlsx_with_pivot(str(csv_path), str(output), _config())

            def remove_one_item(xml: str) -> str:
                removed = xml.replace('<item x="2"/>', "", 1)
                self.assertNotEqual(xml, removed)
                return removed

            _rewrite_zip_part(output, "xl/pivotTables/pivotTable1.xml", remove_one_item)

            detail = "\n".join(validate_pivot_xlsx(output))
            self.assertIn("items count=4，实际 item 数量=3", detail)


if __name__ == "__main__":
    unittest.main()
