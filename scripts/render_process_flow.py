from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEMPLATE_PATH = PROJECT_ROOT / "assets" / "templates" / "process-flow-template.html"

PHASE_W = 220
PHASE_H = 78
CARD_MIN_W = 320
CARD_MAX_W = 500
CARD_MIN_H = 168
START_X = 120
PHASE_GAP = 96
PHASE_Y = 86
CARD_START_Y = 238
CARD_GAP_Y = 40
VIEW_W = 2280
VIEW_H = 1260


def display_units(text: str) -> float:
    units = 0.0
    for ch in text:
        if ch.isspace():
            units += 0.35
        elif ch.isascii():
            units += 0.55
        else:
            units += 1.0
    return units


def estimate_card_width(
    title: str,
    purpose: str,
    source_dir: str,
    source_line: str,
    learning_tag: str = "",
) -> int:
    width = max(
        196 + int(display_units(title) * 11.8),
        186 + int(display_units(purpose) * 7.8),
        176 + int(display_units(source_dir) * 7.5),
        168 + int(display_units(source_line) * 7.2),
        162 + int(display_units(learning_tag) * 8.0),
        CARD_MIN_W,
    )
    return min(width, CARD_MAX_W)


def estimate_line_count(text: str, width: int, factor: float) -> int:
    if not text:
        return 0
    chars_per_line = max(8, int((width - 82) / factor))
    return max(1, (int(display_units(text)) + chars_per_line - 1) // chars_per_line)


def estimate_card_height(width: int, title: str, purpose: str, source_dir: str) -> int:
    title_lines = estimate_line_count(title, width, 11.6)
    purpose_lines = estimate_line_count(f"目的：{purpose}" if purpose else "", width, 8.8)
    source_dir_lines = estimate_line_count(source_dir, width, 8.8)
    height = 54 + title_lines * 20 + 8 + purpose_lines * 14 + 12 + 44
    if source_dir_lines > 1:
        height += (source_dir_lines - 1) * 12
    height += 18
    return max(height, CARD_MIN_H)


def build_learning_tag(source_kind: str, source_dir: str) -> str:
    if source_kind == "skill" or source_dir == "SKILL.md":
        return "主说明重点"
    mapping = {
        "reference": "补充约束",
        "script": "执行脚本",
        "readme": "背景补充",
    }
    return mapping.get(source_kind, "补充信息")


def curve_path(from_x: float, from_y: float, to_x: float, to_y: float) -> str:
    ctrl_offset = max(42.0, abs(to_x - from_x) * 0.32)
    return (
        f"M {from_x:.1f} {from_y:.1f} "
        f"C {from_x + ctrl_offset:.1f} {from_y:.1f}, "
        f"{to_x - ctrl_offset:.1f} {to_y:.1f}, "
        f"{to_x:.1f} {to_y:.1f}"
    )


def same_phase_path(from_card: dict[str, Any], to_card: dict[str, Any]) -> str:
    start_x = from_card["x"] + from_card["w"] - 30
    start_y = from_card["y"] + from_card["h"]
    end_x = to_card["x"] + to_card["w"] - 30
    end_y = to_card["y"]
    lane_x = max(from_card["x"] + from_card["w"], to_card["x"] + to_card["w"]) + 18
    return (
        f"M {start_x:.1f} {start_y:.1f} "
        f"C {lane_x:.1f} {start_y + 22:.1f}, "
        f"{lane_x:.1f} {end_y - 22:.1f}, "
        f"{end_x:.1f} {end_y:.1f}"
    )


def require_fields(data: dict[str, Any], fields: list[str], scope: str) -> None:
    for field in fields:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {scope}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_step(step: dict[str, Any], phase_id: str) -> dict[str, Any]:
    require_fields(
        step,
        [
            "id",
            "order",
            "track",
            "title",
            "source_kind",
            "source_dir",
            "source_anchor",
            "next",
        ],
        f"step in phase {phase_id}",
    )
    if step["track"] not in {"main", "branch"}:
        raise ValueError(f"Unsupported track '{step['track']}' in phase {phase_id}")
    if not isinstance(step["next"], list):
        raise ValueError(f"step.next must be a list in phase {phase_id}")
    return {
        "id": str(step["id"]),
        "order": int(step["order"]),
        "track": str(step["track"]),
        "title": str(step["title"]).strip(),
        "purpose": str(step.get("purpose", "")).strip(),
        "source_kind": str(step["source_kind"]).strip(),
        "source_dir": str(step["source_dir"]).strip(),
        "source_line": str(step.get("source_line", step["source_anchor"])).strip(),
        "source_anchor": str(step["source_anchor"]).strip(),
        "next": [str(item) for item in step["next"]],
    }


def normalize_phase(phase: dict[str, Any]) -> dict[str, Any]:
    require_fields(phase, ["id", "title", "subtitle", "steps"], "phase")
    steps = phase["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"Phase {phase['id']} must contain non-empty steps")
    normalized_steps = [normalize_step(step, str(phase["id"])) for step in steps]
    return {
        "id": str(phase["id"]),
        "title": str(phase["title"]).strip(),
        "subtitle": str(phase["subtitle"]).strip(),
        "final": bool(phase.get("final", False)),
        "steps": normalized_steps,
    }


def normalize_data(data: dict[str, Any]) -> dict[str, Any]:
    require_fields(data, ["title", "phases"], "root")
    phases = data["phases"]
    if not isinstance(phases, list) or not phases:
        raise ValueError("phases must be a non-empty list")

    normalized_phases = [normalize_phase(phase) for phase in phases]
    step_ids: set[str] = set()
    for phase in normalized_phases:
        for step in phase["steps"]:
            if step["id"] in step_ids:
                raise ValueError(f"Duplicate step id '{step['id']}'")
            step_ids.add(step["id"])

    for phase in normalized_phases:
        for step in phase["steps"]:
            for next_id in step["next"]:
                if next_id not in step_ids:
                    raise ValueError(f"Unknown next step id '{next_id}'")

    return {
        "title": str(data["title"]).strip(),
        "subtitle": str(data.get("subtitle", "")).strip(),
        "meta_left": str(
            data.get(
                "meta_left",
                "主线看 SKILL.md，支线看 references / assets / README",
            )
        ).strip(),
        "meta_right": str(data.get("meta_right", "只保留模块、线条、SVG")).strip(),
        "phases": normalized_phases,
    }


def build_layout_model(data: dict[str, Any]) -> dict[str, Any]:
    phase_nodes: list[dict[str, Any]] = []
    card_nodes: list[dict[str, Any]] = []
    cards_by_id: dict[str, dict[str, Any]] = {}
    phase_links: list[dict[str, Any]] = []
    cursor_x = START_X

    for phase in data["phases"]:
        phase_steps = sorted(phase["steps"], key=lambda item: item["order"])
        phase_card_specs = []
        column_width = PHASE_W
        for step in phase_steps:
            learning_tag = build_learning_tag(step["source_kind"], step["source_dir"])
            card_width = estimate_card_width(
                step["title"],
                step["purpose"],
                step["source_dir"],
                step["source_line"],
                learning_tag,
            )
            card_height = estimate_card_height(
                card_width,
                step["title"],
                step["purpose"],
                step["source_dir"],
            )
            phase_card_specs.append((step, learning_tag, card_width, card_height))
            column_width = max(column_width, card_width)

        phase_x = cursor_x + (column_width - PHASE_W) / 2
        phase_node = {
            "id": phase["id"],
            "title": phase["title"],
            "subtitle": phase["subtitle"],
            "x": phase_x,
            "y": PHASE_Y,
            "w": PHASE_W,
            "h": PHASE_H,
            "final": phase["final"],
        }
        phase_nodes.append(phase_node)
        cursor_x += column_width + PHASE_GAP

        phase_center_x = phase_x + PHASE_W / 2
        current_y = CARD_START_Y
        for step, learning_tag, card_width, card_height in phase_card_specs:
            card = {
                "id": step["id"],
                "title": step["title"],
                "purpose": step["purpose"],
                "track": step["track"],
                "x": phase_center_x - card_width / 2,
                "y": current_y,
                "w": card_width,
                "h": card_height,
                "source_dir": step["source_dir"],
                "source_line": step["source_line"],
                "source_anchor": step["source_anchor"],
                "source_kind": step["source_kind"],
                "learning_tag": learning_tag,
                "isSkillSource": step["source_kind"] == "skill"
                or step["source_dir"] == "SKILL.md",
                "next": step["next"],
                "phase_id": phase["id"],
                "final": phase["final"],
            }
            card_nodes.append(card)
            cards_by_id[card["id"]] = card
            current_y += card_height + CARD_GAP_Y

    for index, phase in enumerate(phase_nodes[:-1]):
        next_phase = phase_nodes[index + 1]
        phase_links.append(
            {
                "fromX": phase["x"] + PHASE_W,
                "fromY": PHASE_Y + PHASE_H / 2,
                "toX": next_phase["x"],
                "toY": PHASE_Y + PHASE_H / 2,
                "path": curve_path(
                    phase["x"] + PHASE_W,
                    PHASE_Y + PHASE_H / 2,
                    next_phase["x"],
                    PHASE_Y + PHASE_H / 2,
                ),
            }
        )

    links: list[dict[str, Any]] = []
    for card in sorted(card_nodes, key=lambda item: int(item["id"])):
        for next_id in card["next"]:
            target = cards_by_id[next_id]
            if card["phase_id"] == target["phase_id"]:
                links.append(
                    {
                        "from": card,
                        "to": target,
                        "kind": "same-phase",
                        "lane": "right",
                        "path": same_phase_path(card, target),
                    }
                )
            else:
                links.append(
                    {
                        "from": card,
                        "to": target,
                        "kind": "cross-phase",
                        "lane": "center",
                        "path": curve_path(
                            card["x"] + card["w"],
                            card["y"] + card["h"] / 2,
                            target["x"],
                            target["y"] + target["h"] / 2,
                        ),
                    }
                )

    max_card_right = max(card["x"] + card["w"] for card in card_nodes) if card_nodes else VIEW_W
    max_card_bottom = max(card["y"] + card["h"] for card in card_nodes) if card_nodes else VIEW_H

    return {
        "width": max(VIEW_W, int(max_card_right + 140)),
        "height": max(VIEW_H, int(max_card_bottom + 140)),
        "phases": phase_nodes,
        "phaseLinks": phase_links,
        "cards": card_nodes,
        "links": links,
    }


def render_process_flow_html(data: dict[str, Any]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    model = build_layout_model(data)
    return (
        template.replace("__TITLE__", html.escape(data["title"]))
        .replace("__META_LEFT__", html.escape(data["meta_left"]))
        .replace("__META_RIGHT__", html.escape(data["meta_right"]))
        .replace("__VIEW_W__", str(model["width"]))
        .replace("__VIEW_H__", str(model["height"]))
        .replace(
            "__MODEL_JSON__",
            json.dumps(model, ensure_ascii=False, separators=(",", ":")),
        )
    )


def render_process_flow(data_path: Path, output_path: Path) -> None:
    raw = load_json(data_path)
    normalized = normalize_data(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_process_flow_html(normalized), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a skill process flow HTML from structured JSON data."
    )
    parser.add_argument("data", help="Path to process flow JSON data file.")
    parser.add_argument("output", help="Path to output HTML file.")
    return parser


def main(argv: list[str]) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv[1:])
    render_process_flow(Path(args.data).resolve(), Path(args.output).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
