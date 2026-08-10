"""工作簿 styles.xml 与 Normal 命名样式的兼容性回归测试。"""

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

from pivot_tool.config import load_preset  # noqa: E402
from pivot_tool.ooxml_guard import NS, validate_pivot_xlsx  # noqa: E402
from pivot_tool.packager import create_xlsx_with_pivot  # noqa: E402


STYLES_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"
)


def _replace_zip_text(path: Path, part: str, old: str, new: str) -> None:
    """替换单个 OOXML 部件，保留其余 zip 内容用于故障注入。"""
    with zipfile.ZipFile(path, "r") as source:
        contents = {name: source.read(name) for name in source.namelist()}
    text = contents[part].decode("utf-8")
    replaced = text.replace(old, new, 1)
    if replaced == text:
        raise AssertionError(f"未找到待替换内容: {old}")
    contents[part] = replaced.encode("utf-8")

    rewritten = path.with_name(f".{path.name}.rewrite")
    with zipfile.ZipFile(rewritten, "w", zipfile.ZIP_DEFLATED) as target:
        for name, content in contents.items():
            target.writestr(name, content)
    os.replace(rewritten, path)


class OoxmlStylesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.csv_path = self.root / "input.csv"
        self.output = self.root / "output.xlsx"
        self.csv_path.write_text(
            "event_day,exp_id,eshow,click,charge,tcharge,conv\n"
            "20260801,dz,100,10,12.5,15,2\n"
            "20260801,exp,120,14,16.5,18,3\n",
            encoding="utf-8",
        )
        create_xlsx_with_pivot(
            str(self.csv_path),
            str(self.output),
            load_preset("commercial_ab_test"),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generated_workbook_has_normal_named_style(self) -> None:
        self.assertEqual([], validate_pivot_xlsx(self.output))
        with zipfile.ZipFile(self.output, "r") as zf:
            styles = ET.fromstring(zf.read("xl/styles.xml"))

        normal = styles.find(f"{NS}cellStyles/{NS}cellStyle")
        self.assertIsNotNone(normal)
        assert normal is not None
        self.assertEqual("Normal", normal.get("name"))
        self.assertEqual("0", normal.get("xfId"))
        self.assertEqual("0", normal.get("builtinId"))

    def test_guard_rejects_missing_normal_style(self) -> None:
        _replace_zip_text(
            self.output,
            "xl/styles.xml",
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n',
            "",
        )

        detail = "\n".join(validate_pivot_xlsx(self.output))
        self.assertIn("缺少 cellStyles", detail)
        self.assertIn("Normal 命名样式数量为 0", detail)

    def test_guard_rejects_out_of_range_style_references(self) -> None:
        cases = (
            (
                "fontId",
                'fontId="0" fillId="0" borderId="0" xfId="0"',
                'fontId="2" fillId="0" borderId="0" xfId="0"',
                "cellXfs/xf[0] fontId=2 越界",
            ),
            (
                "fillId",
                'fillId="0" borderId="0" xfId="0"',
                'fillId="2" borderId="0" xfId="0"',
                "cellXfs/xf[0] fillId=2 越界",
            ),
            (
                "borderId",
                'borderId="0" xfId="0"',
                'borderId="1" xfId="0"',
                "cellXfs/xf[0] borderId=1 越界",
            ),
            (
                "xfId",
                'borderId="0" xfId="0"/></cellXfs>',
                'borderId="0" xfId="1"/></cellXfs>',
                "cellXfs/xf[0] xfId=1 越界",
            ),
        )
        valid_workbook = self.output.read_bytes()

        for name, old, new, expected in cases:
            with self.subTest(name=name):
                self.output.write_bytes(valid_workbook)
                _replace_zip_text(self.output, "xl/styles.xml", old, new)
                detail = "\n".join(validate_pivot_xlsx(self.output))
                self.assertIn(expected, detail)

    def test_guard_rejects_style_collection_count_mismatch(self) -> None:
        _replace_zip_text(
            self.output,
            "xl/styles.xml",
            '<fonts count="1">',
            '<fonts count="2">',
        )

        detail = "\n".join(validate_pivot_xlsx(self.output))
        self.assertIn("fonts count=2，实际 font 数量=1", detail)

    def test_guard_rejects_style_children_out_of_order(self) -> None:
        cell_xfs = (
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" '
            'borderId="0" xfId="0"/></cellXfs>\n'
        )
        cell_styles = (
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" '
            'builtinId="0"/></cellStyles>\n'
        )
        _replace_zip_text(
            self.output,
            "xl/styles.xml",
            cell_xfs + cell_styles,
            cell_styles + cell_xfs,
        )

        detail = "\n".join(validate_pivot_xlsx(self.output))
        self.assertIn("xl/styles.xml 子元素顺序非法: cellXfs", detail)

    def test_guard_rejects_missing_styles_relationship(self) -> None:
        _replace_zip_text(
            self.output,
            "xl/_rels/workbook.xml.rels",
            "/relationships/styles\" Target=\"styles.xml\"",
            "/relationships/theme\" Target=\"styles.xml\"",
        )

        detail = "\n".join(validate_pivot_xlsx(self.output))
        self.assertIn("styles 关系数量为 0，期望 1", detail)

    def test_guard_rejects_missing_styles_content_type(self) -> None:
        _replace_zip_text(
            self.output,
            "[Content_Types].xml",
            STYLES_CONTENT_TYPE,
            "application/xml",
        )

        detail = "\n".join(validate_pivot_xlsx(self.output))
        self.assertIn("styles Content Type 声明数量为 0", detail)


if __name__ == "__main__":
    unittest.main()
