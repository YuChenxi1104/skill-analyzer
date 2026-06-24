from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_script_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "render_process_flow.py"
    )
    spec = importlib.util.spec_from_file_location(
        "render_process_flow_script",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_process_flow_data() -> dict:
    return {
        "title": "demo-skill 流程图",
        "subtitle": "从输入走到交付的轻量流程模块。",
        "meta_left": "主线看 SKILL.md，支线看 references / assets / README",
        "meta_right": "只保留模块、线条、SVG",
        "phases": [
            {
                "id": "input",
                "title": "用户输入",
                "subtitle": "先交代主题和素材",
                "steps": [
                    {
                        "id": "01",
                        "order": 1,
                        "track": "main",
                        "title": "提供主题与场景",
                        "purpose": "明确这个 skill 主要解决什么任务和使用场景。",
                        "source_kind": "skill",
                        "source_dir": "SKILL.md",
                        "source_line": "第236-251行",
                        "source_anchor": "Step 1 · 7问澄清清单",
                        "next": ["02"],
                    },
                    {
                        "id": "02",
                        "order": 2,
                        "track": "branch",
                        "title": "补原始内容或大纲",
                        "purpose": "补齐执行这个 skill 需要参考的现成材料。",
                        "source_kind": "readme",
                        "source_dir": "README.md",
                        "source_line": "第1-20行",
                        "source_anchor": "常见使用场景",
                        "next": ["03"],
                    },
                ],
            },
            {
                "id": "agent",
                "title": "Agent 接单",
                "subtitle": "先判断要不要继续追问",
                "steps": [
                    {
                        "id": "03",
                        "order": 3,
                        "track": "main",
                        "title": "判断信息是否足够",
                        "purpose": "确认是否可以继续规划，还是需要先补问用户。",
                        "source_kind": "skill",
                        "source_dir": "SKILL.md",
                        "source_line": "第236-251行",
                        "source_anchor": "Step 1 · 动手前必做",
                        "next": [],
                    }
                ],
            },
        ],
    }


class RenderProcessFlowTests(unittest.TestCase):
    def test_render_process_flow_html_contains_layers_and_structured_sources(self) -> None:
        module = load_script_module()

        with tempfile.TemporaryDirectory(prefix="skill-analyzer-process-flow-") as temp_dir:
            root = Path(temp_dir)
            data_path = root / "process-flow-data.json"
            output_path = root / "demo-skill-process-flow.html"

            data_path.write_text(
                json.dumps(sample_process_flow_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            module.render_process_flow(data_path, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("阶段层", html)
            self.assertIn("动作层", html)
            self.assertIn("目录", html)
            self.assertIn("行号", html)
            self.assertIn("主线看 SKILL.md", html)
            self.assertIn('"track":"main"', html)
            self.assertIn('"track":"branch"', html)

    def test_build_layout_model_stacks_same_phase_cards_without_overlap(self) -> None:
        module = load_script_module()
        data = sample_process_flow_data()
        data["phases"][1]["steps"].append(
            {
                "id": "04",
                "order": 4,
                "track": "main",
                "title": "补充规则",
                "purpose": "把接下来的执行要求补完整。",
                "source_kind": "skill",
                "source_dir": "SKILL.md",
                "source_line": "第260-280行",
                "source_anchor": "Step 2",
                "next": [],
            }
        )

        model = module.build_layout_model(module.normalize_data(data))
        agent_cards = [card for card in model["cards"] if card["phase_id"] == "agent"]

        self.assertEqual(len(agent_cards), 2)
        y_positions = {card["y"] for card in agent_cards}
        self.assertEqual(len(y_positions), 2)

    def test_build_layout_model_uses_side_lane_for_same_phase_serial_links(self) -> None:
        module = load_script_module()
        model = module.build_layout_model(module.normalize_data(sample_process_flow_data()))

        same_phase_link = next(link for link in model["links"] if link["from"]["id"] == "01")

        self.assertEqual(same_phase_link["kind"], "same-phase")
        self.assertEqual(same_phase_link["lane"], "right")
        self.assertIn("C", same_phase_link["path"])

    def test_build_layout_model_marks_skill_sourced_cards_for_learning(self) -> None:
        module = load_script_module()
        model = module.build_layout_model(module.normalize_data(sample_process_flow_data()))

        first_card = model["cards"][0]
        second_card = model["cards"][1]

        self.assertEqual(first_card["learning_tag"], "主说明重点")
        self.assertEqual(second_card["learning_tag"], "背景补充")

    def test_build_layout_model_preserves_purpose_and_source_line(self) -> None:
        module = load_script_module()
        model = module.build_layout_model(module.normalize_data(sample_process_flow_data()))
        first_card = model["cards"][0]

        self.assertEqual(first_card["purpose"], "明确这个 skill 主要解决什么任务和使用场景。")
        self.assertEqual(first_card["source_line"], "第236-251行")

    def test_estimate_card_height_leaves_room_for_meta_rows(self) -> None:
        module = load_script_module()
        height = module.estimate_card_height(
            360,
            "判断需沉淀哪些资源",
            "判断这个 skill 需要建立哪些 scripts、references、assets，分别承载什么内容。",
            "SKILL.md",
        )

        self.assertGreaterEqual(height, 184)

    def test_render_process_flow_html_uses_line_label_purpose_and_learning_tag(self) -> None:
        module = load_script_module()
        html = module.render_process_flow_html(module.normalize_data(sample_process_flow_data()))

        self.assertIn("行号", html)
        self.assertIn("第236-251行", html)
        self.assertIn("目的", html)
        self.assertIn("主说明重点", html)

    def test_render_process_flow_html_marks_skill_sourced_cards(self) -> None:
        module = load_script_module()
        html = module.render_process_flow_html(module.normalize_data(sample_process_flow_data()))

        self.assertIn('"isSkillSource":true', html)
        self.assertIn('"isSkillSource":false', html)

    def test_validate_requires_unique_step_ids(self) -> None:
        module = load_script_module()
        data = sample_process_flow_data()
        data["phases"][1]["steps"][0]["id"] = "01"

        with self.assertRaises(ValueError):
            module.normalize_data(data)

    def test_validate_requires_supported_track(self) -> None:
        module = load_script_module()
        data = sample_process_flow_data()
        data["phases"][0]["steps"][0]["track"] = "diagonal"

        with self.assertRaises(ValueError):
            module.normalize_data(data)


if __name__ == "__main__":
    unittest.main()
