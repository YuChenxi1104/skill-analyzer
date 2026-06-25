from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_script_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "render_merged_preview.py"
    )
    spec = importlib.util.spec_from_file_location(
        "render_merged_preview_script",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_structure_data() -> dict:
    return {
        "title": "demo-skill 文件夹结构图",
        "viewBox": "0 0 1800 1200",
        "focus": {
            "x": 120,
            "y": 80,
            "width": 900,
            "height": 620,
        },
        "model": {
            "width": 1800,
            "height": 1200,
            "root": {
                "x": 900,
                "y": 86,
                "w": 220,
                "h": 38,
                "label": "demo-skill/",
                "type": "Skill 根目录",
                "note": "完整 skill 样本",
            },
            "groups": [
                {
                    "x": 420,
                    "y": 266,
                    "w": 220,
                    "h": 72,
                    "label": "SKILL.md",
                    "type": "主说明",
                    "note": "定义主流程",
                    "children": [
                        {
                            "x": 420,
                            "y": 520,
                            "w": 250,
                            "h": 70,
                            "label": "SKILL.md",
                            "type": "Markdown 文档",
                            "note": "核心规则",
                        }
                    ],
                }
            ],
        },
    }


def sample_beginner_data() -> dict:
    return {
        "skill_name": "demo-skill",
        "page_title": "demo-skill 模块页",
        "hero_eyebrow": "模块总览",
        "hero_title": "demo-skill",
        "hero_subtitle": "一页看懂这个 skill 适不适合你，以及它怎么组织和交付。",
        "basic_info": {
            "name": "demo-skill",
            "source": "GitHub / demo/example",
            "url": "https://github.com/demo/example",
            "stars": "1.2k 星标",
            "forks": "86 Fork",
            "checked_date": "2026-06-22",
            "one_liner": "适合把重复流程沉淀成可复用 Skill。",
            "not_for": [
                "想完全自定义来源",
                "想做成自己的咨询系统",
            ],
        },
        "experience": {
            "prepare_kicker": "准备阶段 / 你需要给什么",
            "required_intro": "先把这两件事直接告诉它",
            "required_cards": [
                {
                    "icon": "🗂",
                    "title": "你要做什么",
                    "description": "说明目标和典型请求。",
                },
                {
                    "icon": "⚙️",
                    "title": "有哪些限制",
                    "description": "说明命名、资源和工具约束。",
                },
            ],
            "optional_intro": "这些材料有的话一起给",
            "optional_cards": [
                {
                    "icon": "📚",
                    "title": "现成资料",
                    "description": "已有文档、脚本或模板。",
                }
            ],
            "prompt_title": "复制即用版提示词",
            "prompt_text": "帮我做一个关于【问题】的 skill。",
            "done_kicker": "结束阶段 / 你会拿到什么",
            "deliveries": [
                {
                    "title": "1. 核心交付",
                    "description": "一份可继续迭代的 skill 文件夹。",
                },
                {
                    "title": "2. 如何浏览",
                    "description": "先看 SKILL.md，再看补充资源。",
                },
                {
                    "title": "3. 如何修改与分享",
                    "description": "后续可继续补脚本和文档。",
                },
            ],
        },
        "advanced": {
            "structure_title": "结构图",
            "structure_description": "先看它由哪些核心文件组成。",
            "process_title": "流程图",
            "process_description": "看它怎么从输入走到交付。",
        },
    }


def sample_process_flow_data() -> dict:
    return {
        "title": "demo-skill 流程图",
        "subtitle": "从输入走到交付的默认流程图模块。",
        "meta_left": "主线看 SKILL.md，支线看 references / assets / README",
        "meta_right": "默认并入 merged-preview.html",
        "phases": [
            {
                "id": "input",
                "title": "用户输入",
                "subtitle": "先交代目标和素材",
                "steps": [
                    {
                        "id": "01",
                        "order": 1,
                        "track": "main",
                        "title": "提供主题与场景",
                        "source_kind": "skill",
                        "source_dir": "SKILL.md",
                        "source_anchor": "Step 1",
                        "next": ["02"],
                    }
                ],
            },
            {
                "id": "agent",
                "title": "Agent 接单",
                "subtitle": "判断是否继续追问",
                "steps": [
                    {
                        "id": "02",
                        "order": 2,
                        "track": "main",
                        "title": "判断信息是否足够",
                        "source_kind": "skill",
                        "source_dir": "SKILL.md",
                        "source_anchor": "Step 2",
                        "next": [],
                    }
                ],
            },
        ],
    }


class RenderMergedPreviewTests(unittest.TestCase):
    def test_render_merged_preview_embeds_process_flow_by_default(self) -> None:
        module = load_script_module()

        with tempfile.TemporaryDirectory(prefix="skill-analyzer-merged-preview-") as temp_dir:
            root = Path(temp_dir)
            structure_path = root / "structure-data.json"
            beginner_path = root / "beginner-data.json"
            process_path = root / "demo-skill-process-flow-data.json"
            output_path = root / "demo-skill-merged-preview.html"

            structure_path.write_text(
                json.dumps(sample_structure_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            beginner_path.write_text(
                json.dumps(sample_beginner_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            process_path.write_text(
                json.dumps(sample_process_flow_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            module.render_merged_preview(structure_path, beginner_path, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("demo-skill", html)
            self.assertIn("const structureModel =", html)
            self.assertIn("结构图", html)
            self.assertIn("流程图", html)
            self.assertIn('class="judgement-card risk"', html)
            self.assertNotIn('class="judgement-card fit"', html)
            self.assertNotIn(".judgement-card.fit { display: none; }", html)
            self.assertIn("想完全自定义来源", html)
            self.assertIn("想做成自己的咨询系统", html)
            self.assertIn('class="flow-block prepare-removed"', html)
            self.assertIn(
                ".flow-block.prepare-removed .flow-node:first-child .group-note { display: none; }",
                html,
            )
            self.assertIn(
                ".flow-block.prepare-removed .flow-node:first-child .input-row { display: none; }",
                html,
            )
            self.assertIn("复制即用版提示词", html)
            self.assertIn('id="copyPrompt"', html)
            self.assertIn('class="process-inline-frame"', html)

    def test_render_merged_preview_requires_process_flow_data(self) -> None:
        module = load_script_module()

        with tempfile.TemporaryDirectory(prefix="skill-analyzer-process-flow-") as temp_dir:
            root = Path(temp_dir)
            structure_path = root / "structure-data.json"
            beginner_path = root / "beginner-data.json"
            output_path = root / "demo-skill-merged-preview.html"

            structure_path.write_text(
                json.dumps(sample_structure_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            beginner_path.write_text(
                json.dumps(sample_beginner_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                module.render_merged_preview(structure_path, beginner_path, output_path)



if __name__ == "__main__":
    unittest.main()
