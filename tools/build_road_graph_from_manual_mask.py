#!/usr/bin/env python3
"""Rebuild data/road_graph.json from the final hand-corrected FH6 road mask.

This script reproduces the compressed manual-mask graph included in this build.
Run from the project root:

    py tools\build_road_graph_from_manual_mask.py

Optional builder-side dependencies:
    py -m pip install pillow numpy opencv-python scikit-image

The live map runtime does not need these packages; it only reads data/road_graph.json.
"""
from __future__ import annotations
import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize

SX = 6.58487266
SY = 6.60554791
OX = 4594.21749925
OY = 3225.79270983
STRIDE_FOR_STITCH = round((SX + SY) / 2.0, 3)
ROAD_CLASS_PRIORITY = {"white": 0, "orange": 1, "orange_dashed": 2, "unknown": 3}
COST = {"white": 1.00, "orange": 1.08, "orange_dashed": 2.60, "unknown": 9.50}
NEIGHBORS_8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def edge_key(a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    return (a, b) if a <= b else (b, a)


def classify_pixels(base_rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(base_rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    r, g, b = base_rgb[..., 0], base_rgb[..., 1], base_rgb[..., 2]
    orange = (
        (h >= 2) & (h <= 28) & (s >= 35) & (v >= 70) &
        (r.astype("int16") - b.astype("int16") >= 35) &
        (r.astype("int16") >= g.astype("int16") - 12)
    )
    return cv2.dilate(orange.astype("uint8"), np.ones((5, 5), np.uint8), iterations=1).astype(bool)


def class_at(pt: tuple[int, int], orange_hint: np.ndarray) -> str:
    x, y = pt
    h, w = orange_hint.shape
    rr = 2
    local = orange_hint[max(0, y - rr):min(h, y + rr + 1), max(0, x - rr):min(w, x + rr + 1)]
    if local.size and float(np.count_nonzero(local)) / float(local.size) >= 0.20:
        return "orange"
    return "white"


def edge_class_for_path(path: list[tuple[int, int]], orange_hint: np.ndarray) -> str:
    if not path:
        return "white"
    step = max(1, len(path) // 16)
    samples = [class_at(pt, orange_hint) for pt in path[::step]]
    if path[-1] not in path[::step]:
        samples.append(class_at(path[-1], orange_hint))
    return "orange" if samples.count("orange") / max(1, len(samples)) >= 0.20 else "white"


def segment_length(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot((b[0] - a[0]) * SX, (b[1] - a[1]) * SY)


def path_accumulated_lengths(path: list[tuple[int, int]]) -> list[float]:
    acc = [0.0]
    total = 0.0
    for a, b in zip(path[:-1], path[1:]):
        total += segment_length(a, b)
        acc.append(total)
    return acc


def build_skeleton_paths(skeleton: np.ndarray) -> tuple[list[list[tuple[int, int]]], int, int]:
    ys, xs = np.where(skeleton)
    points = [(int(x), int(y)) for x, y in zip(xs, ys)]
    point_set = set(points)
    neighbors: dict[tuple[int, int], list[tuple[int, int]]] = {
        p: [(p[0] + dx, p[1] + dy) for dx, dy in NEIGHBORS_8 if (p[0] + dx, p[1] + dy) in point_set]
        for p in points
    }
    degree = {p: len(neighbors[p]) for p in points}
    keys = {p for p, deg in degree.items() if deg != 2}
    visited_edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    paths: list[list[tuple[int, int]]] = []

    for start in sorted(keys, key=lambda p: (p[1], p[0])):
        for nb in neighbors[start]:
            ek = edge_key(start, nb)
            if ek in visited_edges:
                continue
            path = [start]
            prev, cur = start, nb
            visited_edges.add(ek)
            while True:
                path.append(cur)
                if cur in keys:
                    break
                next_items = [q for q in neighbors[cur] if q != prev]
                if not next_items:
                    break
                nxt = next_items[0]
                ek = edge_key(cur, nxt)
                if ek in visited_edges:
                    break
                visited_edges.add(ek)
                prev, cur = cur, nxt
            if len(path) >= 2:
                paths.append(path)

    # Closed loops where every point has degree 2.
    for p in points:
        for nb in neighbors[p]:
            ek = edge_key(p, nb)
            if ek in visited_edges:
                continue
            path = [p]
            prev, cur = p, nb
            visited_edges.add(ek)
            while True:
                path.append(cur)
                next_items = [q for q in neighbors[cur] if q != prev]
                if not next_items:
                    break
                nxt = next_items[0]
                ek = edge_key(cur, nxt)
                if ek in visited_edges:
                    break
                visited_edges.add(ek)
                prev, cur = cur, nxt
                if cur == p:
                    break
            if len(path) >= 2:
                paths.append(path)

    return paths, len(points), len(keys)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FH6 route graph from final manual road mask.")
    parser.add_argument("--mask", default="data/fh6_corrected_road_mask_final.png")
    parser.add_argument("--edits", default="data/fh6_road_edits_final.json")
    parser.add_argument("--source-map", default="data/fh6_full_map_source.jpeg")
    parser.add_argument("--output", default="data/road_graph.json")
    parser.add_argument("--clean-mask-output", default="data/fh6_corrected_road_mask_final_clean_for_graph.png")
    parser.add_argument("--skeleton-output", default="data/fh6_manual_road_skeleton_final.png")
    parser.add_argument("--min-component-area", type=int, default=80)
    parser.add_argument("--sample-step", type=int, default=6, help="Keep one node every N skeleton pixels along simple corridors.")
    parser.add_argument("--runtime-stitch-radius-cells", type=int, default=3)
    parser.add_argument("--runtime-component-bridge-radius-px", type=float, default=140.0)
    args = parser.parse_args()

    raw_mask = np.asarray(Image.open(args.mask).convert("L")) > 127
    count, labels, stats, _ = cv2.connectedComponentsWithStats(raw_mask.astype("uint8"), 8)
    mask = np.zeros_like(raw_mask, dtype=bool)
    removed_components = 0
    removed_px = 0
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= args.min_component_area:
            mask[labels == label] = True
        else:
            removed_components += 1
            removed_px += area
    Image.fromarray((mask.astype("uint8") * 255)).save(args.clean_mask_output)

    skeleton = skeletonize(mask)
    Image.fromarray((skeleton.astype("uint8") * 255)).save(args.skeleton_output)
    paths, skeleton_points, key_points = build_skeleton_paths(skeleton)

    source_map = Path(args.source_map)
    if source_map.exists():
        orange_hint = classify_pixels(np.asarray(Image.open(source_map).convert("RGB")))
    else:
        orange_hint = np.zeros_like(mask, dtype=bool)

    node_id_by_pt: dict[tuple[int, int], int] = {}
    nodes: list[dict] = []
    node_class: list[str] = []
    class_counts: Counter[str] = Counter()
    edges: list[dict] = []
    edge_counts: Counter[str] = Counter()
    seen_edges: set[tuple[int, int]] = set()

    def get_node(pt: tuple[int, int]) -> int:
        if pt in node_id_by_pt:
            return node_id_by_pt[pt]
        idx = len(nodes)
        node_id_by_pt[pt] = idx
        cls = class_at(pt, orange_hint)
        node_class.append(cls)
        class_counts[cls] += 1
        x, y = pt
        nodes.append({
            "id": f"{x}:{y}",
            "map_x": round(x * SX + OX, 3),
            "map_y": round(y * SY + OY, 3),
            "road_class": cls,
            "source_x": int(x),
            "source_y": int(y),
        })
        return idx

    def add_edge(a: int, b: int, length: float, cls: str) -> None:
        if a == b or length <= 0:
            return
        key = (a, b) if a < b else (b, a)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edge_counts[cls] += 1
        edges.append({
            "from": nodes[a]["id"],
            "to": nodes[b]["id"],
            "length": round(length, 3),
            "cost": round(length * COST.get(cls, COST["unknown"]), 3),
            "road_class": cls,
        })

    sample_step = max(1, int(args.sample_step))
    for path in paths:
        if len(path) < 2:
            continue
        acc = path_accumulated_lengths(path)
        sample_idx = [0]
        for i in range(sample_step, len(path) - 1, sample_step):
            sample_idx.append(i)
        if sample_idx[-1] != len(path) - 1:
            sample_idx.append(len(path) - 1)
        for ia, ib in zip(sample_idx[:-1], sample_idx[1:]):
            a = get_node(path[ia])
            b = get_node(path[ib])
            cls = edge_class_for_path(path[ia:ib + 1], orange_hint)
            add_edge(a, b, acc[ib] - acc[ia], cls)

    parent = list(range(len(nodes)))
    size = [1] * len(nodes)

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]

    for edge in edges:
        a = node_id_by_pt[tuple(map(int, edge["from"].split(":")))]
        b = node_id_by_pt[tuple(map(int, edge["to"].split(":")))]
        union(a, b)
    component_sizes = sorted(Counter(find(i) for i in range(len(nodes))).values(), reverse=True)

    edit_summary = {}
    edits_path = Path(args.edits)
    if edits_path.exists():
        edits = json.loads(edits_path.read_text(encoding="utf-8"))
        strokes = edits.get("strokes") or []
        edit_summary = {
            "kind": edits.get("kind"),
            "imageSize": edits.get("imageSize"),
            "brushUnit": edits.get("brushUnit"),
            "stroke_count": len(strokes),
            "stroke_type_counts": dict(Counter(str(s.get("type")) for s in strokes)),
        }

    graph = {
        "version": "0.9.8-manual-road-mask-final-2026-05-25-compressed",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "map_id": 481,
        "layer_id": 760,
        "zoom": 18,
        "scale": 1,
        "tile_size": 256,
        "stride_px": STRIDE_FOR_STITCH,
        "notes": f"Compressed road graph rebuilt from final hand-corrected FH6 road mask, sampled every {sample_step} skeleton pixels.",
        "route_priority": COST,
        "manual_source": {
            "mask_file": str(Path(args.mask)).replace("\\", "/"),
            "edits_file": str(edits_path).replace("\\", "/"),
            "clean_mask_file": str(Path(args.clean_mask_output)).replace("\\", "/"),
            "mask_size": {"width": int(mask.shape[1]), "height": int(mask.shape[0])},
            "min_component_area_px": args.min_component_area,
            "removed_small_components": removed_components,
            "removed_small_component_pixels": removed_px,
            "skeleton_points_before_compression": skeleton_points,
            "key_points_before_compression": key_points,
            "sample_step_skeleton_px": sample_step,
            "image_to_map_affine": {"sx": SX, "sy": SY, "ox": OX, "oy": OY},
            "edit_summary": edit_summary,
        },
        "runtime_stitch_radius_cells": args.runtime_stitch_radius_cells,
        "runtime_component_bridge_radius_px": args.runtime_component_bridge_radius_px,
        "node_class_counts": dict(class_counts),
        "edge_class_counts": dict(edge_counts),
        "source_component_count": len(component_sizes),
        "source_largest_components": component_sizes[:12],
        "nodes": nodes,
        "edges": edges,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Done: nodes={len(nodes)} edges={len(edges)} "
        f"skeleton_points={skeleton_points} sample_step={sample_step} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
