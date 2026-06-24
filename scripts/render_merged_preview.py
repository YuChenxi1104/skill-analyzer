from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any
import re

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render_process_flow import build_layout_model as build_process_flow_layout_model
from render_process_flow import load_json as load_process_flow_json
from render_process_flow import normalize_data as normalize_process_flow_data
from render_process_flow import render_process_flow_html
from structure_layout_constants import (
    CHILD_NOTE_GAP_Y,
    CHILD_NOTE_MAX_W,
    CHILD_NOTE_MIN_W,
    GROUP_NOTE_EXTRA_W,
    GROUP_NOTE_GAP_Y,
    GROUP_NOTE_MIN_W,
    MIN_CHILD_GAP_X,
    MODEL_SIDE_PADDING,
    NOTE_MAX_LINES,
)


def require_fields(data: dict[str, Any], fields: list[str], scope: str) -> None:
    for field in fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {scope}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_basic_info(data: dict[str, Any]) -> None:
    require_fields(
        data,
        ["name", "source", "url", "stars", "forks", "checked_date", "one_liner"],
        "basic_info",
    )
    if "fit_for" in data and not isinstance(data["fit_for"], list):
        raise ValueError("basic_info.fit_for must be a list when provided")
    if "not_for" in data and not isinstance(data["not_for"], list):
        raise ValueError("basic_info.not_for must be a list when provided")


def validate_cards(cards: Any, scope: str, min_count: int, max_count: int) -> None:
    if not isinstance(cards, list):
        raise ValueError(f"{scope} must be a list")
    if not (min_count <= len(cards) <= max_count):
        raise ValueError(f"{scope} must contain {min_count}-{max_count} cards")
    for index, card in enumerate(cards):
        require_fields(card, ["icon", "title", "description"], f"{scope}[{index}]")


def validate_deliveries(items: Any) -> None:
    if not isinstance(items, list) or len(items) != 3:
        raise ValueError("experience.deliveries must contain exactly 3 items")
    for index, item in enumerate(items):
        require_fields(item, ["title", "description"], f"experience.deliveries[{index}]")


def validate_experience(data: dict[str, Any]) -> None:
    require_fields(
        data,
        [
            "prepare_kicker",
            "required_intro",
            "required_cards",
            "optional_intro",
            "optional_cards",
            "prompt_title",
            "prompt_text",
            "done_kicker",
            "deliveries",
        ],
        "experience",
    )
    validate_cards(data["required_cards"], "experience.required_cards", 2, 2)
    validate_cards(data["optional_cards"], "experience.optional_cards", 1, 4)
    validate_deliveries(data["deliveries"])


def validate_advanced(data: dict[str, Any]) -> None:
    require_fields(
        data,
        [
            "structure_title",
            "structure_description",
            "process_title",
            "process_description",
        ],
        "advanced",
    )


def validate_beginner_data(data: dict[str, Any]) -> None:
    require_fields(
        data,
        [
            "skill_name",
            "page_title",
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "basic_info",
            "experience",
            "advanced",
        ],
        "root",
    )
    validate_basic_info(data["basic_info"])
    validate_experience(data["experience"])
    validate_advanced(data["advanced"])


def process_data_path_for(structure_data_path: Path, skill_name: str) -> Path:
    return structure_data_path.parent / f"{skill_name}-process-flow-data.json"


def load_process_html(structure_data_path: Path, beginner_data: dict[str, Any]) -> tuple[str, int]:
    skill_name = beginner_data.get("skill_name", "skill")
    process_data_path = process_data_path_for(structure_data_path, skill_name)
    if not process_data_path.exists():
        raise ValueError(
            f"Missing required process flow data file: {process_data_path.name}"
        )
    process_data = normalize_process_flow_data(load_process_flow_json(process_data_path))
    model = build_process_flow_layout_model(process_data)
    return render_process_flow_html(process_data), int(model["height"])


def html_attr_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def process_html_to_srcdoc(process_html: str) -> str:
    compact = re.sub(r">\s+<", "><", process_html).strip()
    return html_attr_escape(compact)


def js_object(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def render_cards(cards: list[dict[str, str]], required: bool) -> str:
    rendered = []
    extra_class = " required" if required else ""
    for card in cards:
        rendered.append(
            f"""
                  <article class="input-card">
                    <div class="input-head">
                      <div class="input-icon{extra_class}" aria-hidden="true">{html.escape(card['icon'])}</div>
                      <h3>{html.escape(card['title'])}</h3>
                    </div>
                    <p>{html.escape(card['description'])}</p>
                  </article>"""
        )
    return "".join(rendered)


def render_deliveries(items: list[dict[str, str]]) -> str:
    rendered = []
    for item in items:
        rendered.append(
            f"""
                  <article class="delivery-card">
                    <h3>{html.escape(item['title'])}</h3>
                    <p class="delivery-line">{html.escape(item['description'])}</p>
                  </article>"""
        )
    return "".join(rendered)


def render_judgement_list(items: list[str], empty_text: str) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return f'<p class="judgement-empty">{html.escape(empty_text)}</p>'

    rendered = []
    for value in values:
        rendered.append(f"<li>{html.escape(value)}</li>")
    return '<ul class="judgement-list">' + "".join(rendered) + "</ul>"


def build_html(
    beginner: dict[str, Any],
    structure: dict[str, Any],
    process_html: str,
    process_height: int,
) -> str:
    basic = beginner["basic_info"]
    exp = beginner["experience"]
    adv = beginner["advanced"]
    fit_for = basic.get("fit_for", [])
    not_for = basic.get("not_for", [])
    structure_model_json = js_object(structure["model"])
    focus_json = js_object(structure["focus"])
    process_srcdoc = process_html_to_srcdoc(process_html)
    process_frame_height = max(1180, process_height + 28)
    process_block = f"""
              <iframe
                class="process-inline-frame"
                style="height: {process_frame_height}px"
                srcdoc="{process_srcdoc}"
                title="{html.escape(beginner['skill_name'])} 流程图"
                loading="lazy"
              ></iframe>
    """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(beginner['page_title'])}</title>
  <style>
    :root {{
      --paper: #fffdfa;
      --ink: #2f312d;
      --muted: #6f736d;
      --line: #dad3c8;
      --line-strong: #c7c0b4;
      --frame: #e7dfd2;
      --accent: #4a6fa5;
      --accent-soft: #e8eef7;
      --accent-deep: #355889;
      --green: #5b8a63;
      --green-soft: #e8f2e9;
      --card: rgba(255, 253, 249, 0.95);
      --shadow: 0 18px 48px rgba(47, 49, 45, 0.08);
      --sans: "Segoe UI", "PingFang SC", "Microsoft YaHei UI", sans-serif;
      --serif: "Georgia", "Times New Roman", "Noto Serif SC", serif;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      min-height: 100%;
      background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.55), transparent 24%),
        linear-gradient(180deg, #f8f4ee 0%, #f1ece3 100%);
      color: var(--ink);
      font-family: var(--sans);
      line-height: 1.65;
    }}
    body {{ padding: 28px 18px 40px; }}
    .shell {{ max-width: 1180px; margin: 0 auto; }}
    .hero {{
      border: 1px solid var(--frame);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(255, 253, 249, 0.96), rgba(255, 250, 244, 0.92));
      box-shadow: var(--shadow);
      padding: 28px 28px 24px;
      margin-bottom: 20px;
    }}
    .eyebrow {{
      margin: 0 0 8px;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    h1 {{
      margin: 0;
      font-family: var(--serif);
      font-size: clamp(30px, 4vw, 50px);
      line-height: 1.08;
      font-weight: 700;
    }}
    .hero-subtitle {{
      margin: 10px 0 0;
      max-width: 760px;
      font-size: 15px;
      color: var(--muted);
    }}
    .tabs {{
      display: flex;
      gap: 10px;
      margin-top: 20px;
      flex-wrap: wrap;
    }}
    .tab-btn {{
      appearance: none;
      border: 1px solid var(--line-strong);
      background: rgba(255, 255, 255, 0.75);
      color: var(--muted);
      border-radius: 999px;
      padding: 10px 16px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: 0.18s ease;
    }}
    .tab-btn:hover {{
      transform: translateY(-1px);
      border-color: var(--accent);
      color: var(--accent-deep);
    }}
    .tab-btn.is-active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      box-shadow: 0 10px 22px rgba(74, 111, 165, 0.18);
    }}
    .panel {{ display: none; }}
    .panel.is-active {{ display: block; }}
    .card {{
      border: 1px solid var(--frame);
      border-radius: 24px;
      background: var(--card);
      box-shadow: var(--shadow);
      padding: 24px;
      margin-bottom: 18px;
    }}
    .section-head {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }}
    .section-no {{
      width: 38px;
      height: 38px;
      border-radius: 11px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--accent);
      color: #fff;
      font-size: 15px;
      font-weight: 700;
      flex: 0 0 auto;
    }}
    .section-title {{
      margin: 0;
      font-family: var(--serif);
      font-size: clamp(20px, 2.1vw, 30px);
      line-height: 1.2;
    }}
    .info-table {{ width: 100%; border-collapse: collapse; }}
    .info-table tr {{ border-bottom: 1px solid var(--line); }}
    .info-table tr:last-child {{ border-bottom: 0; }}
    .info-table td {{
      padding: 14px 10px;
      vertical-align: top;
      font-size: 14px;
    }}
    .info-table .label {{
      width: 132px;
      color: var(--muted);
      font-weight: 700;
      white-space: nowrap;
    }}
    .info-table a {{ color: var(--accent); text-decoration: none; }}
    .metrics {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .metric-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.82);
      font-size: 13px;
      color: var(--ink);
    }}
    .metric-chip svg {{
      width: 14px;
      height: 14px;
      display: block;
      flex: 0 0 auto;
    }}
    .metric-date {{ font-size: 12px; color: var(--muted); }}
    .one-liner-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.74);
      padding: 18px 20px;
      margin-top: 18px;
    }}
    .one-liner-label {{
      margin: 0 0 10px;
      font-size: 13px;
      font-weight: 800;
      color: var(--accent-deep);
    }}
    .one-liner-card p:last-child {{
      margin: 0;
      font-size: clamp(22px, 3vw, 30px);
      line-height: 1.45;
      font-weight: 700;
    }}
    .judgement-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 14px;
      margin-top: 18px;
    }}
    .judgement-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.76);
      padding: 16px 18px;
    }}
    .judgement-card h3 {{
      margin: 0 0 10px;
      font-size: 18px;
      line-height: 1.35;
    }}
    .judgement-card.fit h3 {{
      color: var(--accent-deep);
    }}
    .judgement-card.fit {{ display: none; }}
    .judgement-card.risk h3 {{
      color: #8b4f3d;
    }}
    .judgement-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
      font-size: 14px;
    }}
    .judgement-list li + li {{
      margin-top: 8px;
    }}
    .judgement-empty {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .flow-block {{
      position: relative;
      padding-left: 54px;
    }}
    .flow-block::before {{
      content: "";
      position: absolute;
      left: 17px;
      top: 6px;
      bottom: 6px;
      width: 2px;
      background: var(--line);
    }}
    .flow-node {{
      position: relative;
      margin-bottom: 24px;
    }}
    .flow-node:last-child {{ margin-bottom: 0; }}
    .flow-block.prepare-removed .flow-node:first-child .group-note {{ display: none; }}
    .flow-block.prepare-removed .flow-node:first-child .input-row {{ display: none; }}
    .flow-dot {{
      position: absolute;
      left: -44px;
      top: 6px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--paper);
      border: 2px solid var(--accent);
      z-index: 1;
    }}
    .phase-kicker {{
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin: 0 0 8px;
    }}
    .phase-kicker.prepare {{ color: #8a7550; }}
    .phase-kicker.done {{ color: var(--green); }}
    .phase-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      background: #faf7f1;
    }}
    .phase-card.done {{
      background: var(--green-soft);
      border-color: #cfe0d0;
    }}
    .group-note {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.82);
      font-size: 13px;
      font-weight: 700;
      color: var(--ink);
    }}
    .input-row {{
      display: grid;
      gap: 12px;
    }}
    .input-row.required {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .input-row.optional {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .input-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.78);
      padding: 16px;
    }}
    .input-head {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .input-icon {{
      width: 34px;
      height: 34px;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      background: #f7f2ea;
      border: 1px solid var(--line);
      flex: 0 0 auto;
    }}
    .input-icon.required {{
      background: #faf0ed;
      border-color: #dec1bc;
    }}
    .input-card h3 {{
      margin: 0;
      font-size: 18px;
      line-height: 1.35;
    }}
    .input-card p {{
      margin: 0;
      font-size: 14px;
      color: var(--muted);
    }}
    .prompt-box {{
      margin-top: 18px;
      border-radius: 16px;
      border: 1px solid #c8d4e8;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(232, 238, 247, 0.72));
      padding: 16px;
    }}
    .prompt-title {{
      margin: 0 0 10px;
      color: var(--accent-deep);
      font-size: 14px;
      font-weight: 800;
    }}
    .prompt-surface {{ position: relative; }}
    .copy-btn {{
      appearance: none;
      border: 1px solid #bfd0e8;
      background: #fff;
      color: var(--accent-deep);
      border-radius: 12px;
      width: 40px;
      height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: 0.18s ease;
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 1;
    }}
    .copy-btn:hover {{ background: var(--accent-soft); }}
    .copy-btn.is-copied {{
      border-color: #95bc9b;
      color: #295235;
      background: #edf7ee;
    }}
    .copy-btn svg {{
      width: 18px;
      height: 18px;
      display: block;
    }}
    .prompt-code {{
      margin: 0;
      white-space: pre-wrap;
      font-size: 13px;
      line-height: 1.7;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(74, 111, 165, 0.18);
      border-radius: 12px;
      padding: 18px 58px 18px 14px;
    }}
    .delivery-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .delivery-card {{
      border: 1px solid #cfe0d0;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.72);
      padding: 16px;
    }}
    .delivery-card h3 {{
      margin: 0 0 12px;
      font-size: 18px;
      line-height: 1.35;
      color: #295235;
    }}
    .delivery-line {{
      margin: 0;
      font-size: 15px;
      line-height: 1.7;
      color: #45604a;
      font-weight: 700;
    }}
    .frame-card {{
      border: 1px solid var(--frame);
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.78);
      padding: 18px;
      margin-bottom: 18px;
    }}
    .sub-head {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .sub-no {{
      width: 42px;
      height: 42px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: #f2f5fb;
      color: var(--accent-deep);
      font-size: 14px;
      font-weight: 800;
      flex: 0 0 auto;
    }}
    .frame-card h3 {{
      margin: 0 0 8px;
      font-size: 22px;
      font-family: var(--serif);
    }}
    .frame-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .delivery-note {{
      margin-top: 10px;
      font-size: 12px;
      color: var(--muted);
    }}
    .diagram-shell {{
      position: relative;
      overflow: hidden;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: #fff;
      box-shadow: 0 10px 28px rgba(47, 49, 45, 0.06);
    }}
    .interactive-structure {{
      position: relative;
      background: #fffefd;
    }}
    .structure-toolbar {{
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 2;
    }}
    .structure-tool {{
      appearance: none;
      width: 40px;
      height: 40px;
      border-radius: 12px;
      border: 1px solid #d7d1c6;
      background: rgba(255, 253, 250, 0.96);
      color: var(--accent-deep);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 18px rgba(47, 49, 45, 0.08);
    }}
    .structure-tool svg {{
      width: 18px;
      height: 18px;
      stroke: currentColor;
    }}
    .structure-canvas {{
      position: relative;
      height: min(74vh, 860px);
      min-height: 500px;
      overflow: hidden;
      cursor: grab;
      background: #fffefd;
    }}
    .structure-canvas.dragging {{ cursor: grabbing; }}
    .structure-svg-shell {{
      position: absolute;
      top: 0;
      left: 0;
      transform-origin: top left;
      user-select: none;
      -webkit-user-select: none;
    }}
    .structure-svg {{
      display: block;
      background: #fffefd;
    }}
    .structure-hint {{
      position: absolute;
      left: 16px;
      bottom: 14px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--frame);
      background: rgba(255, 253, 250, 0.95);
      color: var(--muted);
      font-size: 12px;
      pointer-events: none;
    }}
    .process-inline-frame {{
      width: 100%;
      height: 1180px;
      border: 0;
      display: block;
      background: #fffdfa;
      border-radius: 18px;
    }}
    @media (max-width: 960px) {{
      .delivery-grid,
      .judgement-grid,
      .input-row.required,
      .input-row.optional {{
        grid-template-columns: 1fr;
      }}
      .structure-canvas {{
        height: 62vh;
        min-height: 420px;
      }}
    }}
    @media (max-width: 720px) {{
      body {{ padding: 14px 10px 24px; }}
      .hero, .card {{ padding: 18px 16px; border-radius: 18px; }}
      .section-head {{ align-items: flex-start; }}
      .info-table td {{
        display: block;
        width: 100%;
        padding: 10px 0;
      }}
      .info-table .label {{ padding-bottom: 4px; }}
      .flow-block {{ padding-left: 42px; }}
      .flow-dot {{ left: -33px; }}
      .one-liner-card p:last-child {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <p class="eyebrow">{html.escape(beginner['hero_eyebrow'])}</p>
      <h1>{html.escape(beginner['hero_title'])}</h1>
      <p class="hero-subtitle">{html.escape(beginner['hero_subtitle'])}</p>
      <div class="tabs" role="tablist" aria-label="模块切换">
        <button class="tab-btn is-active" type="button" role="tab" aria-selected="true" aria-controls="panel-beginner" id="tab-beginner" data-target="panel-beginner">初级模块</button>
        <button class="tab-btn" type="button" role="tab" aria-selected="false" aria-controls="panel-advanced" id="tab-advanced" data-target="panel-advanced">中级模块</button>
      </div>
    </header>

    <main>
      <section class="panel is-active" id="panel-beginner" role="tabpanel" aria-labelledby="tab-beginner">
        <article class="card">
          <div class="section-head">
            <span class="section-no">1.1</span>
            <h2 class="section-title">基本信息</h2>
          </div>
          <table class="info-table">
            <tr>
              <td class="label">名称</td>
              <td>{html.escape(basic['name'])}</td>
            </tr>
            <tr>
              <td class="label">来源</td>
              <td>{html.escape(basic['source'])}</td>
            </tr>
            <tr>
              <td class="label">地址</td>
              <td><a href="{html.escape(basic['url'], quote=True)}" target="_blank" rel="noreferrer">{html.escape(basic['url'])}</a></td>
            </tr>
            <tr>
              <td class="label">热度</td>
              <td>
                <div class="metrics">
                  <span class="metric-chip">
                    <svg viewBox="0 0 24 24" fill="#b98a2c" aria-hidden="true">
                      <path d="M12 2.6l2.9 5.88 6.49.94-4.69 4.57 1.11 6.46L12 17.41 6.19 20.45l1.11-6.46L2.61 9.42l6.49-.94L12 2.6z"></path>
                    </svg>
                    {html.escape(basic['stars'])}
                  </span>
                  <span class="metric-chip">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#4a6fa5" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <circle cx="6" cy="6" r="2.5"></circle>
                      <circle cx="18" cy="6" r="2.5"></circle>
                      <circle cx="18" cy="18" r="2.5"></circle>
                      <path d="M8.5 7.4l7 3.3"></path>
                      <path d="M8.5 6h7"></path>
                      <path d="M17.2 8.3v7.2"></path>
                    </svg>
                    {html.escape(basic['forks'])}
                  </span>
                  <span class="metric-date">查询日期：{html.escape(basic['checked_date'])}</span>
                </div>
              </td>
            </tr>
          </table>
          <div class="one-liner-card">
            <p class="one-liner-label">一句话说清楚</p>
            <p>{html.escape(basic['one_liner'])}</p>
          </div>
          <div class="judgement-grid">
            <article class="judgement-card fit">
              <h3>适合你</h3>
              {render_judgement_list(fit_for, "这次产物里还没有补这一栏。")}
            </article>
            <article class="judgement-card risk">
              <h3>不适合你</h3>
              {render_judgement_list(not_for, "这次产物里还没有补这一栏。")}
            </article>
          </div>
        </article>

        <article class="card">
          <div class="section-head">
            <span class="section-no">1.2</span>
            <h2 class="section-title">体验流程</h2>
          </div>
          <div class="flow-block prepare-removed">
            <div class="flow-node">
              <span class="flow-dot"></span>
              <p class="phase-kicker prepare">{html.escape(exp['prepare_kicker'])}</p>
              <div class="phase-card">
                <div class="group-note">{html.escape(exp['required_intro'])}</div>
                <div class="input-row required">
{render_cards(exp['required_cards'], required=True)}
                </div>
                <div class="group-note">{html.escape(exp['optional_intro'])}</div>
                <div class="input-row optional">
{render_cards(exp['optional_cards'], required=False)}
                </div>
                <div class="prompt-box">
                  <p class="prompt-title">{html.escape(exp['prompt_title'])}</p>
                  <div class="prompt-surface">
                    <button class="copy-btn" type="button" id="copyPrompt" aria-label="复制提示词" title="复制提示词">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <rect x="9" y="9" width="10" height="10" rx="2"></rect>
                        <path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1"></path>
                      </svg>
                    </button>
                    <p class="prompt-code" id="promptText">{html.escape(exp['prompt_text'])}</p>
                  </div>
                </div>
              </div>
            </div>
            <div class="flow-node">
              <span class="flow-dot"></span>
              <p class="phase-kicker done">{html.escape(exp['done_kicker'])}</p>
              <div class="phase-card done">
                <div class="delivery-grid">
{render_deliveries(exp['deliveries'])}
                </div>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section class="panel" id="panel-advanced" role="tabpanel" aria-labelledby="tab-advanced">
        <article class="card">
          <div class="section-head">
            <span class="section-no">2</span>
            <h2 class="section-title">中级模块：结构图 + 流程图</h2>
          </div>
          <div class="frame-card">
            <div class="sub-head">
              <span class="sub-no">2.1</span>
              <div>
                <h3>{html.escape(adv['structure_title'])}</h3>
                <p>{html.escape(adv['structure_description'])}</p>
              </div>
            </div>
            <div class="diagram-shell">
              <div class="interactive-structure" id="interactiveStructure">
                <div class="structure-toolbar">
                  <button class="structure-tool" type="button" id="resetStructureView" aria-label="重置结构图视角" title="重置结构图视角">
                    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M3 12a9 9 0 1 0 3-6.7"></path>
                      <path d="M3 3v6h6"></path>
                    </svg>
                  </button>
                </div>
                <div class="structure-canvas" id="structureCanvas">
                  <div class="structure-svg-shell" id="structureSvgShell">
                    <svg class="structure-svg" id="structureInteractiveSvg" viewBox="{html.escape(structure['viewBox'])}" width="{structure['model']['width']}" height="{structure['model']['height']}" aria-label="{html.escape(structure['title'])}"></svg>
                  </div>
                </div>
                <div class="structure-hint">拖动平移 · 滚轮缩放 · 双击重置</div>
              </div>
            </div>
          </div>
          <div class="frame-card">
            <div class="sub-head">
              <span class="sub-no">2.2</span>
              <div>
                <h3>{html.escape(adv['process_title'])}</h3>
                <p>{html.escape(adv['process_description'])}</p>
              </div>
            </div>
            <div class="diagram-shell">
{process_block}
            </div>
            <p class="delivery-note">默认最终交付：`&lt;skill-name&gt;-merged-preview.html`。流程图默认内嵌在这一页里；独立流程页只在需要单独调试或讲解时再补。</p>
          </div>
        </article>
      </section>
    </main>
  </div>

  <script>
    (function () {{
      var buttons = document.querySelectorAll(".tab-btn");
      var panels = document.querySelectorAll(".panel");
      var copyButton = document.getElementById("copyPrompt");
      var promptText = document.getElementById("promptText");

      function activate(targetId) {{
        buttons.forEach(function (button) {{
          var active = button.getAttribute("data-target") === targetId;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-selected", active ? "true" : "false");
        }});

        panels.forEach(function (panel) {{
          panel.classList.toggle("is-active", panel.id === targetId);
        }});
      }}

      buttons.forEach(function (button) {{
        button.addEventListener("click", function () {{
          activate(button.getAttribute("data-target"));
          window.scrollTo({{ top: 0, behavior: "smooth" }});
        }});
      }});

      function flashCopyState(success) {{
        if (success) {{
          copyButton.classList.add("is-copied");
        }}
        window.setTimeout(function () {{
          copyButton.classList.remove("is-copied");
        }}, 1800);
      }}

      function fallbackCopy(text) {{
        var textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "readonly");
        textarea.style.position = "absolute";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();

        var copied = false;
        try {{
          copied = document.execCommand("copy");
        }} catch (error) {{
          copied = false;
        }}

        document.body.removeChild(textarea);
        return copied;
      }}

      if (copyButton && promptText) {{
        copyButton.addEventListener("click", function () {{
          var text = promptText.innerText;
          if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(text).then(function () {{
              flashCopyState(true);
            }}).catch(function () {{
              flashCopyState(fallbackCopy(text));
            }});
            return;
          }}
          flashCopyState(fallbackCopy(text));
        }});
      }}

      var SVG_NS = "http://www.w3.org/2000/svg";
      var structureCanvas = document.getElementById("structureCanvas");
      var structureSvgShell = document.getElementById("structureSvgShell");
      var structureInteractiveSvg = document.getElementById("structureInteractiveSvg");
      var resetStructureView = document.getElementById("resetStructureView");
      if (!structureCanvas || !structureSvgShell || !structureInteractiveSvg) {{
        return;
      }}

      const structureModel = {structure_model_json};
      const focus = {focus_json};

      var CHILD_NOTE_GAP_Y = {CHILD_NOTE_GAP_Y};
      var CHILD_NOTE_MIN_W = {CHILD_NOTE_MIN_W};
      var CHILD_NOTE_MAX_W = {CHILD_NOTE_MAX_W};
      var CHILD_NOTE_MAX_LINES = {NOTE_MAX_LINES};
      var GROUP_NOTE_GAP_Y = {GROUP_NOTE_GAP_Y};
      var GROUP_NOTE_MIN_W = {GROUP_NOTE_MIN_W};
      var GROUP_NOTE_EXTRA_W = {GROUP_NOTE_EXTRA_W};
      var GROUP_NOTE_MAX_LINES = {NOTE_MAX_LINES};
      var MIN_CHILD_GAP_X = {MIN_CHILD_GAP_X};
      var MODEL_SIDE_PADDING = {MODEL_SIDE_PADDING};

      function svgEl(name, attrs) {{
        var node = document.createElementNS(SVG_NS, name);
        Object.keys(attrs || {{}}).forEach(function (key) {{
          node.setAttribute(key, attrs[key]);
        }});
        return node;
      }}

      function charWidthEstimate(char) {{
        if (/\\s/.test(char)) return 3.8;
        if (/[A-Za-z0-9/_\\-.]/.test(char)) return 6.6;
        if (/[\\u2E80-\\u9FFF\\uF900-\\uFAFF]/.test(char)) return 11.2;
        return 8.2;
      }}

      function textWidthEstimate(text) {{
        return Array.from(text).reduce(function (sum, char) {{
          return sum + charWidthEstimate(char);
        }}, 0);
      }}

      function tokenizeText(text) {{
        return text.match(/[A-Za-z0-9/_\\-.]+|./g) || [];
      }}

      function getWrappedLines(text, maxWidth) {{
        var tokens = tokenizeText(text);
        var lines = [];
        var line = "";
        for (var i = 0; i < tokens.length; i += 1) {{
          var token = tokens[i];
          var testLine = line + token;
          if (textWidthEstimate(testLine) > maxWidth && line) {{
            lines.push(line);
            line = token;
          }} else {{
            line = testLine;
          }}
        }}
        if (line) lines.push(line);
        return lines;
      }}

      function fitLines(text, maxWidth, maxLines) {{
        var lines = getWrappedLines(text, maxWidth);
        if (!maxLines || lines.length <= maxLines) return lines;
        var trimmed = lines.slice(0, maxLines);
        var last = trimmed[maxLines - 1];
        while (last.length > 1 && textWidthEstimate(last + "...") > maxWidth) {{
          last = last.slice(0, -1);
        }}
        trimmed[maxLines - 1] = last + "...";
        return trimmed;
      }}

      function childSpanWidth(node) {{
        return Math.max(node.w, Math.min(Math.max(node.w + 28, CHILD_NOTE_MIN_W), CHILD_NOTE_MAX_W));
      }}

      function layoutGroupChildren(model) {{
        model.groups.forEach(function (group) {{
          var children = group.children || [];
          if (!children.length) return;

          var spans = children.map(childSpanWidth);
          var totalWidth = spans.reduce(function (sum, span) {{ return sum + span; }}, 0) + MIN_CHILD_GAP_X * Math.max(children.length - 1, 0);
          var availableWidth = Math.max(totalWidth, group.w);
          var left = group.x - availableWidth / 2;
          var centerY = Math.min.apply(null, children.map(function (child) {{ return child.y; }}));
          var cursor = left;

          children.forEach(function (child, index) {{
            var span = spans[index];
            child.x = Math.round(cursor + span / 2);
            child.y = centerY;
            cursor += span + MIN_CHILD_GAP_X;
          }});

          var groupLeftEdge = Math.min(
            group.x - Math.max(group.w + GROUP_NOTE_EXTRA_W, GROUP_NOTE_MIN_W) / 2,
            Math.min.apply(null, children.map(function (child) {{ return child.x - childSpanWidth(child) / 2; }}))
          );
          if (groupLeftEdge < MODEL_SIDE_PADDING) {{
            var shift = MODEL_SIDE_PADDING - groupLeftEdge;
            group.x += shift;
            children.forEach(function (child) {{
              child.x += shift;
            }});
          }}
        }});
      }}

      function wrapText(parent, text, x, y, maxWidth, lineHeight, attrs, maxLines) {{
        var node = svgEl("text", attrs || {{}});
        var lines = fitLines(text, maxWidth, maxLines);
        lines.forEach(function (line, index) {{
          var span = svgEl("tspan", {{ x: x, y: y + index * lineHeight }});
          span.textContent = line;
          node.appendChild(span);
        }});
        parent.appendChild(node);
      }}

      function addLineText(parent, text, x, y, attrs) {{
        var node = svgEl("text", Object.assign({{ x: x, y: y }}, attrs || {{}}));
        node.textContent = text;
        parent.appendChild(node);
      }}

      function curvePath(fromX, fromY, toX, toY) {{
        var midY = (fromY + toY) / 2;
        return ["M", fromX, fromY, "C", fromX, midY, toX, midY, toX, toY].join(" ");
      }}

      function drawNode(parent, node, options) {{
        var x = node.x - node.w / 2;
        var y = node.y - node.h / 2;
        var group = svgEl("g");
        var compact = !!options.compact;
        var noteText = (node.note || "").trim();

        group.appendChild(svgEl("rect", {{
          x: x,
          y: y,
          width: node.w,
          height: node.h,
          rx: compact ? 6 : 10,
          ry: compact ? 6 : 10,
          fill: "#fffefd",
          stroke: "#dbd5ca",
          "stroke-width": compact ? 1.1 : 1.3
        }}));

        addLineText(group, node.label, node.x, y + (compact ? 28 : 26), {{
          "text-anchor": "middle",
          "font-size": compact ? "18" : "20",
          "font-weight": "600",
          fill: "#2f312d",
          "font-family": "Segoe UI, Microsoft YaHei UI, sans-serif"
        }});

        addLineText(group, node.type, node.x, y + 52, {{
          "text-anchor": "middle",
          "font-size": compact ? "13.5" : "15",
          fill: "#7a7e77",
          "font-family": "Segoe UI, Microsoft YaHei UI, sans-serif"
        }});

        if (options.showNote && noteText) {{
          var chipY = y + node.h + CHILD_NOTE_GAP_Y;
          var chipW = Math.min(Math.max(node.w + 28, CHILD_NOTE_MIN_W), CHILD_NOTE_MAX_W);
          var chipX = node.x - chipW / 2;
          var lines = fitLines(noteText, chipW - 28, CHILD_NOTE_MAX_LINES);
          var chipH = 20 + lines.length * 15;
          group.appendChild(svgEl("rect", {{
            x: chipX,
            y: chipY,
            width: chipW,
            height: chipH,
            rx: 14,
            ry: 14,
            fill: "#fffdfa",
            stroke: "#e4ddd2",
            "stroke-width": "1"
          }}));
          wrapText(group, noteText, node.x, chipY + 18, chipW - 28, 15, {{
            "text-anchor": "middle",
            "font-size": "11.5",
            fill: "#777b75",
            "font-family": "Segoe UI, Microsoft YaHei UI, sans-serif"
          }}, CHILD_NOTE_MAX_LINES);
        }}

        if (options.showGroupNote && noteText) {{
          var noteY = y + node.h + GROUP_NOTE_GAP_Y;
          var noteW = Math.max(node.w + GROUP_NOTE_EXTRA_W, GROUP_NOTE_MIN_W);
          var noteX = node.x - noteW / 2;
          var groupLines = fitLines(noteText, noteW - 36, GROUP_NOTE_MAX_LINES);
          var noteH = 20 + groupLines.length * 15;
          group.appendChild(svgEl("rect", {{
            x: noteX,
            y: noteY,
            width: noteW,
            height: noteH,
            rx: 14,
            ry: 14,
            fill: "#fffdfa",
            stroke: "#e4ddd2",
            "stroke-width": "1"
          }}));
          wrapText(group, noteText, node.x, noteY + 18, noteW - 36, 15, {{
            "text-anchor": "middle",
            "font-size": "12",
            fill: "#777b75",
            "font-family": "Segoe UI, Microsoft YaHei UI, sans-serif"
          }}, GROUP_NOTE_MAX_LINES);
        }}

        parent.appendChild(group);
      }}

      function renderTree(svg) {{
        while (svg.firstChild) {{
          svg.removeChild(svg.firstChild);
        }}

        svg.setAttribute("viewBox", "0 0 " + structureModel.width + " " + structureModel.height);
        svg.setAttribute("width", structureModel.width);
        svg.setAttribute("height", structureModel.height);
        svg.appendChild(svgEl("rect", {{
          x: 0,
          y: 0,
          width: structureModel.width,
          height: structureModel.height,
          fill: "#fffefd"
        }}));

        drawNode(svg, structureModel.root, {{ compact: true, showNote: false, showGroupNote: false }});

        structureModel.groups.forEach(function (group) {{
          svg.appendChild(svgEl("path", {{
            d: curvePath(structureModel.root.x, structureModel.root.y + structureModel.root.h / 2, group.x, group.y - group.h / 2),
            fill: "none",
            stroke: "#d5d0c6",
            "stroke-width": "1.5"
          }}));

          drawNode(svg, group, {{ compact: false, showNote: false, showGroupNote: true }});

          group.children.forEach(function (child) {{
            svg.appendChild(svgEl("path", {{
              d: curvePath(group.x, group.y + group.h / 2, child.x, child.y - child.h / 2),
              fill: "none",
              stroke: "#d5d0c6",
              "stroke-width": "1.4"
            }}));
            drawNode(svg, child, {{ compact: true, showNote: true, showGroupNote: false }});
          }});
        }});
      }}

      layoutGroupChildren(structureModel);
      renderTree(structureInteractiveSvg);

      var scale = 1;
      var translateX = 0;
      var translateY = 0;
      var dragging = false;
      var startX = 0;
      var startY = 0;
      var originX = 0;
      var originY = 0;
      var minScale = 0.38;
      var maxScale = 2.8;

      function applyTransform() {{
        structureSvgShell.style.transform = "translate(" + translateX + "px, " + translateY + "px) scale(" + scale + ")";
      }}

      function setInitialView() {{
        var rect = structureCanvas.getBoundingClientRect();
        var fitScaleX = (rect.width * 0.92) / focus.width;
        var fitScaleY = (rect.height * 0.9) / focus.height;
        scale = Math.max(minScale, Math.min(maxScale, Math.min(fitScaleX, fitScaleY)));
        translateX = 24 - focus.x * scale;
        translateY = 18 - focus.y * scale;
        applyTransform();
      }}

      function zoomAt(pointX, pointY, nextScale) {{
        var clamped = Math.max(minScale, Math.min(maxScale, nextScale));
        var worldX = (pointX - translateX) / scale;
        var worldY = (pointY - translateY) / scale;
        scale = clamped;
        translateX = pointX - worldX * scale;
        translateY = pointY - worldY * scale;
        applyTransform();
      }}

      structureCanvas.addEventListener("wheel", function (event) {{
        event.preventDefault();
        var rect = structureCanvas.getBoundingClientRect();
        zoomAt(event.clientX - rect.left, event.clientY - rect.top, scale * (event.deltaY < 0 ? 1.08 : 0.92));
      }}, {{ passive: false }});

      structureCanvas.addEventListener("mousedown", function (event) {{
        dragging = true;
        structureCanvas.classList.add("dragging");
        startX = event.clientX;
        startY = event.clientY;
        originX = translateX;
        originY = translateY;
      }});

      window.addEventListener("mousemove", function (event) {{
        if (!dragging) return;
        translateX = originX + (event.clientX - startX);
        translateY = originY + (event.clientY - startY);
        applyTransform();
      }});

      window.addEventListener("mouseup", function () {{
        dragging = false;
        structureCanvas.classList.remove("dragging");
      }});

      structureCanvas.addEventListener("dblclick", setInitialView);
      if (resetStructureView) {{
        resetStructureView.addEventListener("click", setInitialView);
      }}
      window.addEventListener("resize", setInitialView);
      setInitialView();
    }})();
  </script>
</body>
</html>
"""


def render_merged_preview(
    structure_data_path: Path,
    beginner_data_path: Path,
    output_path: Path,
) -> None:
    structure_data = load_json(structure_data_path)
    beginner_data = load_json(beginner_data_path)
    process_html, process_height = load_process_html(structure_data_path, beginner_data)
    validate_beginner_data(beginner_data)
    require_fields(structure_data, ["title", "viewBox", "focus", "model"], "structure_data")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_html(beginner_data, structure_data, process_html, process_height),
        encoding="utf-8",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a merged skill breakdown preview from structured JSON data."
    )
    parser.add_argument("structure_data", help="Path to structure-data.json")
    parser.add_argument("beginner_data", help="Path to beginner-data.json")
    parser.add_argument("output", help="Path to output merged preview HTML")
    return parser


def main(argv: list[str]) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv[1:])
    render_merged_preview(
        Path(args.structure_data).resolve(),
        Path(args.beginner_data).resolve(),
        Path(args.output).resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
