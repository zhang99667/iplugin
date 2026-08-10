"""多业务透视表合并与 OOXML 闸门的回归测试。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from pivot_tool.merge_pivots import create_multi_business_pivot, main  # noqa: E402
from pivot_tool.ooxml_guard import (  # noqa: E402
    NS,
    PivotOoxmlError,
    validate_pivot_xlsx,
)


REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _write_config(path: Path, label: str) -> None:
    """写入足以覆盖合并行为的最小原生透视表配置。"""
    data = {
        "name": f"merge-{label}",
        "description": "",
        "data_sheet_name": f"{label}明细",
        "pivot_sheet_name": f"{label}透视",
        "pivot_table_name": f"{label}透视表",
        "columns": [
            {
                "name": "event_day",
                "type": "int",
                "shared_items_type": "enumerated",
            },
            {
                "name": "exp_id",
                "type": "str",
                "shared_items_type": "enumerated",
            },
            {"name": "eshow", "type": "int", "shared_items_type": "range"},
            {"name": "click", "type": "int", "shared_items_type": "range"},
            {"name": "charge", "type": "float", "shared_items_type": "range"},
        ],
        "calculated_fields": [
            {"name": "ectr", "formula": "click /eshow"},
        ],
        "pivot_layout": {
            "row_fields": ["exp_id"],
            "col_fields": ["__data__"],
            "data_fields": [
                {"name": "点击", "source_field": "click"},
                {"name": "消费", "source_field": "charge"},
                {"name": "点击率", "source_field": "ectr", "num_fmt_id": 10},
            ],
            "row_item_order": {"exp_id": ["dz", "exp"]},
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    """写入简单 CSV；测试数据不含需要额外转义的字符。"""
    lines = [",".join(headers), *( ",".join(row) for row in rows)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _replace_zip_text(path: Path, part: str, old: str, new: str) -> None:
    """重写指定 OOXML 部件，用于构造确定性的损坏样本。"""
    with zipfile.ZipFile(path, "r") as source:
        contents = {name: source.read(name) for name in source.namelist()}

    text = contents[part].decode("utf-8")
    replaced = text.replace(old, new, 1)
    if replaced == text:
        raise AssertionError(f"{part} 中未找到待替换内容: {old}")
    contents[part] = replaced.encode("utf-8")

    rewritten = path.with_name(f".{path.name}.rewrite")
    with zipfile.ZipFile(rewritten, "w", zipfile.ZIP_DEFLATED) as target:
        for name, content in contents.items():
            target.writestr(name, content)
    os.replace(rewritten, path)


class MergePivotsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _input(self, label: str, rows: list[list[str]]) -> tuple[Path, Path]:
        csv_path = self.root / f"{label}.csv"
        config_path = self.root / f"{label}.json"
        _write_csv(
            csv_path,
            ["event_day", "exp_id", "eshow", "click", "charge"],
            rows,
        )
        _write_config(config_path, label)
        return csv_path, config_path

    def test_merge_applies_aliases_avoids_calculated_conflicts_and_hides_data(self) -> None:
        csv_path = self.root / "aliases.csv"
        config_path = self.root / "aliases.json"
        output = self.root / "aliases.xlsx"
        _write_csv(
            csv_path,
            ["event_day", "exp_id", "eshow", "clk", "asp_charge", "ectr"],
            [["20260801", "dz", "100", "10", "12.5", "0.1"]],
        )
        _write_config(config_path, "别名")

        create_multi_business_pivot(
            [(str(csv_path), str(config_path))],
            str(output),
            hide_data_sheets=True,
        )

        self.assertEqual([], validate_pivot_xlsx(output))
        with zipfile.ZipFile(output, "r") as zf:
            workbook = ET.fromstring(zf.read("xl/workbook.xml"))
            cache = ET.fromstring(
                zf.read("xl/pivotCache/pivotCacheDefinition1.xml")
            )

        sheets = workbook.find(f"{NS}sheets")
        self.assertIsNotNone(sheets)
        assert sheets is not None
        sheet_states = {
            sheet.get("name"): sheet.get("state")
            for sheet in sheets.findall(f"{NS}sheet")
        }
        self.assertIsNone(sheet_states["别名透视"])
        self.assertEqual("hidden", sheet_states["别名明细"])

        cache_fields = cache.find(f"{NS}cacheFields")
        self.assertIsNotNone(cache_fields)
        assert cache_fields is not None
        field_names = [field.get("name") for field in cache_fields]
        self.assertIn("click", field_names)
        self.assertIn("charge", field_names)
        self.assertIn("ectr_source", field_names)
        self.assertEqual(1, field_names.count("ectr"))
        self.assertNotIn("clk", field_names)
        self.assertNotIn("asp_charge", field_names)

    def test_guard_validates_every_pivot_in_multi_workbook(self) -> None:
        first = self._input("业务一", [["20260801", "dz", "100", "10", "12.5"]])
        second = self._input("业务二", [["20260801", "exp", "120", "15", "18"]])
        output = self.root / "multi.xlsx"
        create_multi_business_pivot(
            [(str(first[0]), str(first[1])), (str(second[0]), str(second[1]))],
            str(output),
        )
        self.assertEqual([], validate_pivot_xlsx(output))

        _replace_zip_text(
            output,
            "xl/pivotCache/pivotCacheDefinition2.xml",
            'refreshOnLoad="1"',
            'refreshOnLoad="0"',
        )
        errors = validate_pivot_xlsx(output)
        detail = "\n".join(errors)
        self.assertIn("pivotCacheDefinition2.xml", detail)
        self.assertIn('refreshOnLoad="1"', detail)

    def test_guard_rejects_pivot_cache_id_relationship_mismatch(self) -> None:
        first = self._input("缓存一", [["20260801", "dz", "100", "10", "12.5"]])
        second = self._input("缓存二", [["20260801", "exp", "120", "15", "18"]])
        output = self.root / "cache-mismatch.xlsx"
        create_multi_business_pivot(
            [(str(first[0]), str(first[1])), (str(second[0]), str(second[1]))],
            str(output),
        )

        _replace_zip_text(
            output,
            "xl/pivotTables/pivotTable2.xml",
            'cacheId="1"',
            'cacheId="0"',
        )
        errors = validate_pivot_xlsx(output)
        detail = "\n".join(errors)
        self.assertIn("pivotTable2.xml", detail)
        self.assertIn("cacheId=0", detail)
        self.assertIn("关系", detail)

    def test_all_empty_inputs_create_valid_placeholder_workbook(self) -> None:
        first = self._input("空业务一", [])
        second = self._input("空业务二", [])
        output = self.root / "empty.xlsx"

        create_multi_business_pivot(
            [(str(first[0]), str(first[1])), (str(second[0]), str(second[1]))],
            str(output),
        )

        self.assertEqual([], validate_pivot_xlsx(output))
        with zipfile.ZipFile(output, "r") as zf:
            names = set(zf.namelist())
            workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        self.assertFalse(any(name.startswith("xl/pivotTables/") for name in names))
        pivot_caches = workbook.find(f"{NS}pivotCaches")
        self.assertIsNotNone(pivot_caches)
        assert pivot_caches is not None
        self.assertEqual([], list(pivot_caches))

    def test_validation_failure_preserves_existing_output(self) -> None:
        source = self._input("事务", [["20260801", "dz", "100", "10", "12.5"]])
        output = self.root / "existing.xlsx"
        output.write_bytes(b"existing-output")

        with mock.patch(
            "pivot_tool.merge_pivots.assert_valid_pivot_xlsx",
            side_effect=PivotOoxmlError("测试校验失败"),
        ):
            with self.assertRaises(PivotOoxmlError):
                create_multi_business_pivot(
                    [(str(source[0]), str(source[1]))],
                    str(output),
                )

        self.assertEqual(b"existing-output", output.read_bytes())
        self.assertEqual([], list(self.root.glob(f".{output.name}.*.tmp.xlsx")))

    def test_cli_forwards_hide_data_sheets(self) -> None:
        with mock.patch("pivot_tool.merge_pivots.create_multi_business_pivot") as create:
            result = main(
                [
                    "one.csv",
                    "one.json",
                    "--hide-data-sheets",
                    "-o",
                    "output.xlsx",
                ]
            )

        self.assertEqual(0, result)
        create.assert_called_once_with(
            [("one.csv", "one.json")],
            "output.xlsx",
            hide_data_sheets=True,
        )


if __name__ == "__main__":
    unittest.main()
