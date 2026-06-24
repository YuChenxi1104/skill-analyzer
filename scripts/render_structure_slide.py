import json
import sys
from pathlib import Path

from structure_layout_constants import (
    CHILD_NOTE_GAP_Y,
    CHILD_NOTE_MAX_W,
    CHILD_NOTE_MIN_W,
    GROUP_NOTE_EXTRA_W,
    GROUP_NOTE_GAP_Y,
    GROUP_NOTE_MIN_W,
    LABEL_LIMIT,
    LINE_HEIGHT,
    MIN_CHILD_GAP_X,
    MODEL_SIDE_PADDING,
    NOTE_HEIGHT_BASE,
    NOTE_LIMIT,
    NOTE_MAX_LINES,
    TYPE_LIMIT,
)


def count_display_units(text: str) -> int:
    units = 0.0
    for ch in text:
        if ch.isascii() and not ("\u4e00" <= ch <= "\u9fff"):
            units += 0.5
        else:
            units += 1
    return int(units) if units.is_integer() else int(units) + 1


def warn(message: str) -> None:
    print(f"[structure-slide warning] {message}", file=sys.stderr)


def estimate_note_height() -> int:
    return NOTE_HEIGHT_BASE + NOTE_MAX_LINES * LINE_HEIGHT


def child_note_width(node_width: int) -> int:
    return min(max(node_width + 28, CHILD_NOTE_MIN_W), CHILD_NOTE_MAX_W)


def group_note_width(node_width: int) -> int:
    return max(node_width + GROUP_NOTE_EXTRA_W, GROUP_NOTE_MIN_W)


def child_span_width(node: dict) -> int:
    return max(node["w"], child_note_width(node["w"]))


def child_block_height(node: dict) -> int:
    return node["h"] + CHILD_NOTE_GAP_Y + estimate_note_height()


def layout_group_children(data: dict) -> None:
    model = data["model"]
    required_width = model["width"]

    for group in model["groups"]:
        children = group.get("children", [])
        if not children:
            continue

        spans = [child_span_width(child) for child in children]
        total_width = sum(spans) + MIN_CHILD_GAP_X * max(len(children) - 1, 0)
        available_width = max(total_width, group["w"])

        left = group["x"] - available_width / 2
        center_y = min(child["y"] for child in children)

        cursor = left
        for child, span in zip(children, spans):
            child["x"] = round(cursor + span / 2)
            child["y"] = center_y
            cursor += span + MIN_CHILD_GAP_X

        group_left_edge = min(
            group["x"] - group_note_width(group["w"]) / 2,
            min(child["x"] - child_span_width(child) / 2 for child in children),
        )
        if group_left_edge < MODEL_SIDE_PADDING:
            shift = MODEL_SIDE_PADDING - group_left_edge
            group["x"] += shift
            for child in children:
                child["x"] += shift

        group_right_edge = max(
            group["x"] + group_note_width(group["w"]) / 2,
            max(child["x"] + child_span_width(child) / 2 for child in children),
        )
        required_width = max(required_width, int(group_right_edge + MODEL_SIDE_PADDING))

    if required_width > model["width"]:
        model["width"] = required_width
        data["viewBox"] = f"0 0 {model['width']} {model['height']}"


def rects_overlap(a: dict, b: dict) -> bool:
    return not (
        a["x2"] <= b["x1"]
        or b["x2"] <= a["x1"]
        or a["y2"] <= b["y1"]
        or b["y2"] <= a["y1"]
    )


def node_rect(node: dict, label: str) -> dict:
    return {
        "label": label,
        "kind": "node",
        "x1": node["x"] - node["w"] / 2,
        "x2": node["x"] + node["w"] / 2,
        "y1": node["y"] - node["h"] / 2,
        "y2": node["y"] + node["h"] / 2,
    }


def child_note_rect(node: dict, label: str) -> dict:
    width = child_note_width(node["w"])
    height = estimate_note_height()
    y1 = node["y"] + node["h"] / 2 + CHILD_NOTE_GAP_Y
    return {
        "label": label,
        "kind": "child_note",
        "x1": node["x"] - width / 2,
        "x2": node["x"] + width / 2,
        "y1": y1,
        "y2": y1 + height,
    }


def group_note_rect(node: dict, label: str) -> dict:
    width = group_note_width(node["w"])
    height = estimate_note_height()
    y1 = node["y"] + node["h"] / 2 + GROUP_NOTE_GAP_Y
    return {
        "label": label,
        "kind": "group_note",
        "x1": node["x"] - width / 2,
        "x2": node["x"] + width / 2,
        "y1": y1,
        "y2": y1 + height,
    }


def validate_geometry(data: dict) -> None:
    model = data["model"]
    rects: list[dict] = []

    for group in model["groups"]:
        rects.append(node_rect(group, group["label"]))
        rects.append(group_note_rect(group, f"{group['label']} note"))
        for child in group["children"]:
            rects.append(node_rect(child, child["label"]))
            rects.append(child_note_rect(child, f"{child['label']} note"))

    for rect in rects:
        if rect["x1"] < 0 or rect["x2"] > model["width"]:
            warn(f"{rect['label']} [{rect['kind']}] exceeds horizontal canvas bounds")
        if rect["y1"] < 0 or rect["y2"] > model["height"]:
            warn(f"{rect['label']} [{rect['kind']}] exceeds vertical canvas bounds")

    for index, rect in enumerate(rects):
        for other in rects[index + 1 :]:
            if rects_overlap(rect, other):
                warn(
                    f"{rect['label']} [{rect['kind']}] overlaps {other['label']} [{other['kind']}]"
                )


def require_keys(data: dict, keys: list[str], scope: str) -> None:
    for key in keys:
        if key not in data:
            raise ValueError(f"Missing required key '{key}' in {scope}")


def validate_focus(data: dict) -> None:
    focus = data["focus"]
    require_keys(focus, ["x", "y", "width", "height"], "focus")


def validate_node(node: dict, scope: str) -> None:
    require_keys(node, ["label", "type", "note"], scope)

    label_len = count_display_units(str(node["label"]))
    type_len = count_display_units(str(node["type"]))
    note_len = count_display_units(str(node["note"]))

    if label_len > LABEL_LIMIT:
      warn(f"{scope}.label exceeds recommended limit {LABEL_LIMIT}: {node['label']}")
    if type_len > TYPE_LIMIT:
      warn(f"{scope}.type exceeds recommended limit {TYPE_LIMIT}: {node['type']}")
    if note_len > NOTE_LIMIT:
      warn(f"{scope}.note exceeds recommended limit {NOTE_LIMIT}: {node['note']}")


def validate_model(data: dict) -> None:
    model = data["model"]
    require_keys(model, ["width", "height", "root", "groups"], "model")
    validate_node(model["root"], "model.root")

    for group_index, group in enumerate(model["groups"]):
        scope = f"model.groups[{group_index}]"
        require_keys(group, ["x", "y", "w", "h", "label", "type", "note", "children"], scope)
        validate_node(group, scope)

        for child_index, child in enumerate(group["children"]):
            child_scope = f"{scope}.children[{child_index}]"
            require_keys(child, ["x", "y", "w", "h", "label", "type", "note"], child_scope)
            validate_node(child, child_scope)


def validate_data(data: dict) -> None:
    require_keys(data, ["title", "viewBox", "focus", "model"], "root")
    validate_focus(data)
    validate_model(data)
    layout_group_children(data)
    validate_geometry(data)


def render_structure_slide(template_path: Path, data_path: Path, output_path: Path) -> None:
    template = template_path.read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    validate_data(data)

    title = data["title"]
    view_box = data["viewBox"]
    focus_json = json.dumps(data["focus"], ensure_ascii=False, indent=2)
    model_json = json.dumps(data["model"], ensure_ascii=False, indent=2)
    width = str(data["model"]["width"])
    height = str(data["model"]["height"])

    rendered = (
        template.replace("__TITLE__", title)
        .replace("__VIEW_BOX__", view_box)
        .replace("__FOCUS_JSON__", focus_json)
        .replace("__MODEL_JSON__", model_json)
        .replace("__WIDTH__", width)
        .replace("__HEIGHT__", height)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: render_structure_slide.py <template.html> <data.json> <output.html>")
        return 1

    template_path = Path(argv[1]).resolve()
    data_path = Path(argv[2]).resolve()
    output_path = Path(argv[3]).resolve()
    render_structure_slide(template_path, data_path, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
