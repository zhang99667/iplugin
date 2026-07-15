"""PivotTable 页面筛选区与主体 location 的回归测试。"""

from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
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
from pivot_tool.ooxml_guard import NS, _validate_layout  # noqa: E402
from pivot_tool.pivot_table import build_pivot_table_xml  # noqa: E402


def _build_xml(filter_count: int) -> str:
    """构造固定三指标布局，只改变页面筛选字段数量。"""
    available_filters = ["event_day", "cust_id"]
    config = PivotConfig(
        name="page-layout-test",
        description="",
        columns=[
            ColumnDef("event_day", "int"),
            ColumnDef("cust_id", "str"),
            ColumnDef("exp", "str"),
            ColumnDef("shows", "int"),
        ],
        calculated_fields=[],
        pivot_layout=PivotLayoutDef(
            row_fields=["exp"],
            col_fields=["__data__"],
            data_fields=[
                DataFieldDef("指标一", "shows"),
                DataFieldDef("指标二", "shows"),
                DataFieldDef("指标三", "shows"),
            ],
            filter_fields=available_filters[:filter_count],
            row_item_order={"exp": ["dz", "0"]},
        ),
    )
    field_maps = FieldMaps(
        headers=["event_day", "cust_id", "exp", "shows"],
        rows=[],
        enumerated_items={
            0: [20260712, 20260713],
            1: ["1", "2"],
            2: ["dz", "0"],
        },
    )
    return build_pivot_table_xml(config, field_maps)


class PivotPageLayoutTest(unittest.TestCase):
    def test_builder_places_body_below_page_fields(self) -> None:
        cases = [
            (0, "A1:D5", "2", None, None),
            (1, "A3:D6", "1", "1", "1"),
            (2, "A4:D7", "1", "2", "1"),
        ]

        for filter_count, ref, first_data_row, row_pages, col_pages in cases:
            with self.subTest(filter_count=filter_count):
                root = ET.fromstring(_build_xml(filter_count))
                location = root.find(f"{NS}location")
                self.assertIsNotNone(location)
                assert location is not None
                self.assertEqual(ref, location.get("ref"))
                self.assertEqual(first_data_row, location.get("firstDataRow"))
                self.assertEqual(row_pages, location.get("rowPageCount"))
                self.assertEqual(col_pages, location.get("colPageCount"))

                page_fields = root.find(f"{NS}pageFields")
                if filter_count:
                    self.assertIsNotNone(page_fields)
                    assert page_fields is not None
                    self.assertEqual(str(filter_count), page_fields.get("count"))
                    self.assertEqual(
                        ["-1"] * filter_count,
                        [field.get("hier") for field in page_fields],
                    )
                else:
                    self.assertIsNone(page_fields)

    def test_guard_accepts_generated_filter_layouts(self) -> None:
        for filter_count in range(3):
            with self.subTest(filter_count=filter_count):
                pivot_xml = _build_xml(filter_count)
                errors: list[str] = []
                _validate_layout(ET.fromstring(pivot_xml), pivot_xml, errors)
                self.assertEqual([], errors)

    def test_guard_accepts_extra_blank_row_below_page_fields(self) -> None:
        pivot_xml = _build_xml(2).replace('ref="A4:D7"', 'ref="A5:D8"')

        errors: list[str] = []
        _validate_layout(ET.fromstring(pivot_xml), pivot_xml, errors)
        self.assertEqual([], errors)

    def test_guard_rejects_page_fields_overlapping_body(self) -> None:
        valid_xml = _build_xml(2)
        broken_xml = valid_xml.replace(
            '<location ref="A4:D7" firstHeaderRow="0" firstDataRow="1" '
            'firstDataCol="1" rowPageCount="2" colPageCount="1"/>',
            '<location ref="A1:D5" firstHeaderRow="0" firstDataRow="2" '
            'firstDataCol="1"/>',
        )
        self.assertNotEqual(valid_xml, broken_xml)

        errors: list[str] = []
        _validate_layout(ET.fromstring(broken_xml), broken_xml, errors)
        detail = "\n".join(errors)
        self.assertIn("firstDataRow=2，期望 1", detail)
        self.assertIn("主体首行不得早于 4", detail)
        self.assertIn("rowPageCount=None，期望 2", detail)
        self.assertIn("colPageCount=None，期望 1", detail)


if __name__ == "__main__":
    unittest.main()
