"""验证 zagent CLI 主入口可以正常分发普通子命令。"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from z_agent import cli


class CliTest(unittest.TestCase):
    def test_doctor_command_runs_through_main_parser(self):
        """覆盖 main 中的 argparse 分发路径，避免普通子命令入口再次被打断。"""
        with patch("z_agent.cli.run_doctor", return_value="诊断完成"):
            # main 会直接写 stdout，这里捕获输出，避免测试日志被命令文本干扰。
            with patch("builtins.print") as print_mock:
                exit_code = cli.main(["doctor"])

        self.assertEqual(exit_code, 0)
        print_mock.assert_called_once_with("诊断完成")

    def test_restore_executes_by_default(self):
        """restore 命令本身就是执行恢复，不需要额外模式参数。"""
        workspace = {"windows": []}
        adapter = Mock()
        adapter.restore_workspace.return_value = ""
        with patch("z_agent.cli.load_state", return_value={"latest_workspace": workspace}):
            with patch("z_agent.cli.build_restore_plan", return_value={"items": []}):
                with patch("z_agent.cli.GhosttyAdapter", return_value=adapter):
                    exit_code = cli.main(["restore"])

        self.assertEqual(exit_code, 0)
        adapter.restore_workspace.assert_called_once_with(workspace)


if __name__ == "__main__":
    unittest.main()
