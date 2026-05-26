#!/usr/bin/env python3
"""Extract an MVP weighted road graph from cached GamerGuides map tiles.

This is a pragmatic computer-vision bootstrapper for FH6 Live Map.
It scans local tile_cache PNG files, detects road overlay colors, snaps them
to a grid, and writes data/road_graph.json that the web app can use for
A* route building.

v0.9.6 adds balanced asphalt routing and stricter white-component cleanup:
    white roads          -> cheapest / preferred
    orange roads         -> medium
    orange dashed trails -> expensive / last resort

Install optional dependencies on the machine that builds the graph:
    py -m pip install pillow numpy opencv-python

The runtime navigator itself does not need OpenCV; it only reads the resulting
JSON graph.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Iterable

TILE_SIZE = 256
MAP_ID = 481
DEFAULT_LAYER_ID = 760
DEFAULT_ZOOM = 18
MAX_ZOOM = 18

ROAD_CLASS_PRIORITY = {
    "white": 0,
    "orange": 1,
    "orange_dashed": 2,
    "unknown": 3,
}


def parse_tile_name(path: Path) -> tuple[int, int] | None:
    stem = path.stem
    if "-" not in stem:
        return None
    a, b = stem.split("-", 1)
    try:
        return int(a), int(b)
    except ValueError:
        return None


def iter_tiles(tile_cache: Path, map_id: int, layer_id: int, zoom: int) -> Iterable[tuple[int, int, Path]]:
    root = tile_cache / str(map_id) / str(layer_id) / str(zoom)
    if not root.exists():
        return []
    items: list[tuple[int, int, Path]] = []
    for path in root.glob("*.png"):
        xy = parse_tile_name(path)
        if xy is None:
            continue
        x, y = xy
        items.append((x, y, path))
    items.sort(key=lambda item: (item[1], item[0]))
    return items


def _clean_mask(mask, args: argparse.Namespace, class_name: str):
    """Remove tiny blobs and compact non-road false positives.

    This intentionally stays conservative. A few missed decorative segments are better
    than a graph that happily routes through roofs, fields and UI symbols.
    """
    import numpy as np

    if not args.use_morphology:
        return mask

    try:
        import cv2

        raw = (mask.astype("uint8") * 255)
        kernel = np.ones((args.kernel, args.kernel), dtype="uint8")
        raw = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, kernel)
        raw = cv2.morphologyEx(raw, cv2.MORPH_OPEN, kernel)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(raw, 8)
        keep = np.zeros_like(raw, dtype="uint8")
        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            width = int(stats[label, cv2.CC_STAT_WIDTH])
            height = int(stats[label, cv2.CC_STAT_HEIGHT])
            span = max(width, height)
            short = max(1, min(width, height))
            elongation = span / short
            fill_ratio = area / float(max(1, width * height))

            if area < args.min_component_area:
                continue
            if span < args.component_min_span:
                continue

            # White buildings/roofs/city blocks are the worst false positives. A true
            # road component is usually long, stroke-like, or low-fill inside its
            # bounding box. Compact bright chunks should not become asphalt.
            min_elongation = args.component_min_elongation
            large_area = args.component_large_area
            max_fill_ratio = args.component_max_fill_ratio
            if class_name == "white":
                min_elongation = max(min_elongation, args.white_component_min_elongation)
                large_area = max(large_area, args.white_component_large_area)
                max_fill_ratio = min(max_fill_ratio, args.white_component_max_fill_ratio)

            if area < large_area and elongation < min_elongation:
                continue
            if fill_ratio > max_fill_ratio and elongation < max(min_elongation * 1.35, 3.2):
                continue
            keep[labels == label] = 255
        return keep > 0
    except Exception:
        # OpenCV is helpful but not mandatory. If it is missing, continue with the raw mask.
        return mask


def detect_road_masks(path: Path, args: argparse.Namespace):
    try:
        from PIL import Image
        import numpy as np
    except Exception as exc:  # pragma: no cover - user environment guard
        raise SystemExit(
            "Missing dependencies. Install them with: py -m pip install pillow numpy opencv-python"
        ) from exc

    img = Image.open(path).convert("RGBA")
    arr = np.asarray(img)
    rgb = arr[..., :3].astype("int16")
    alpha = arr[..., 3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = maxc - minc

    # GamerGuides overlay style:
    # - white/gray low-saturation roads;
    # - salmon/orange race/road overlays and dotted trail overlays;
    # - magenta/pink main overlays that cover some asphalt corridors on the source map.
    # Yellow farm plots and building roofs are the main false positives, so defaults are intentionally strict.
    light_roads = (
        (alpha >= args.alpha_min)
        & (maxc >= args.light_value_min)
        & (sat <= args.light_sat_max)
        & (minc >= args.light_minc_min)
    )
    orange_roads = (
        (alpha >= args.alpha_min)
        & (r >= args.orange_r_min)
        & (g >= args.orange_g_min)
        & (g <= args.orange_g_max)
        & (b <= args.orange_b_max)
        & ((r - b) >= args.orange_rb_delta_min)
        & ((r - g) >= args.orange_rg_delta_min)
    )
    magenta_roads = (
        (alpha >= args.alpha_min)
        & (r >= args.magenta_r_min)
        & (b >= args.magenta_b_min)
        & (g <= args.magenta_g_max)
        & ((r - g) >= args.magenta_rg_delta_min)
        & ((b - g) >= args.magenta_bg_delta_min)
    )

    light_roads = _clean_mask(light_roads | magenta_roads, args, "white")
    orange_roads = _clean_mask(orange_roads, args, "orange")
    mask = light_roads | orange_roads

    if args.preview_dir:
        try:
            from PIL import Image
            import numpy as np

            preview_root = Path(args.preview_dir)
            preview_root.mkdir(parents=True, exist_ok=True)
            overlay = np.asarray(img.convert("RGB")).copy()
            # white/magenta asphalt corridors: green; orange detected roads: amber.
            overlay[light_roads] = (60, 255, 80)
            overlay[orange_roads] = (255, 170, 40)
            Image.fromarray(overlay).save(preview_root / path.name)
        except Exception as exc:
            print(f"WARN: failed to write preview for {path.name}: {exc}")

    return {
        "combined": mask,
        "white": light_roads,
        "orange": orange_roads,
    }


def classify_cell(white_ratio: float, orange_ratio: float, args: argparse.Namespace) -> str:
    if white_ratio >= args.white_min_ratio and white_ratio >= orange_ratio * 0.55:
        return "white"
    if orange_ratio >= args.orange_solid_ratio:
        return "orange"
    if orange_ratio >= args.min_road_ratio:
        return "orange_dashed"
    return "unknown"


def combine_edge_class(a: str, b: str) -> str:
    # If an edge joins two kinds, price it as the less preferred kind. This prevents
    # a few white cells around an intersection from making a trail look like a highway.
    pa = ROAD_CLASS_PRIORITY.get(a, ROAD_CLASS_PRIORITY["unknown"])
    pb = ROAD_CLASS_PRIORITY.get(b, ROAD_CLASS_PRIORITY["unknown"])
    return a if pa >= pb else b


def multiplier_for_class(road_class: str, args: argparse.Namespace) -> float:
    if road_class == "white":
        return args.white_cost_factor
    if road_class == "orange":
        return args.orange_cost_factor
    if road_class == "orange_dashed":
        return args.orange_dashed_cost_factor
    return args.unknown_cost_factor


def build_graph(args: argparse.Namespace) -> dict:
    import numpy as np

    tile_cache = Path(args.tile_cache).resolve()
    tiles = list(iter_tiles(tile_cache, args.map_id, args.layer, args.zoom))
    if not tiles:
        raise SystemExit(
            f"No cached tiles found in {tile_cache / str(args.map_id) / str(args.layer) / str(args.zoom)}\n"
            "First open/cache the map tiles, or run the tile-cache downloader."
        )

    scale = 2 ** (args.zoom - MAX_ZOOM)
    nodes: dict[str, dict] = {}
    class_counts: dict[str, int] = {"white": 0, "orange": 0, "orange_dashed": 0, "unknown": 0}
    tile_count = len(tiles)
    print(f"Scanning {tile_count} cached tiles from {tile_cache} (map={args.map_id}, layer={args.layer}, zoom={args.zoom})")

    for idx, (tile_x, tile_y, path) in enumerate(tiles, start=1):
        try:
            masks = detect_road_masks(path, args)
        except Exception as exc:
            print(f"WARN: failed to process {path}: {exc}")
            continue

        combined = masks["combined"]
        white = masks["white"]
        orange = masks["orange"]
        h, w = combined.shape[:2]
        stride = args.stride
        for local_y in range(0, h, stride):
            for local_x in range(0, w, stride):
                ys = slice(local_y, min(local_y + stride, h))
                xs = slice(local_x, min(local_x + stride, w))
                cell = combined[ys, xs]
                if cell.size == 0:
                    continue
                combined_ratio = float(np.count_nonzero(cell)) / float(cell.size)
                if combined_ratio < args.min_road_ratio:
                    continue

                white_ratio = float(np.count_nonzero(white[ys, xs])) / float(cell.size)
                orange_ratio = float(np.count_nonzero(orange[ys, xs])) / float(cell.size)
                road_class = classify_cell(white_ratio, orange_ratio, args)
                if road_class == "unknown" and not args.keep_unknown_cells:
                    continue

                global_px_x = tile_x * TILE_SIZE + local_x + stride / 2
                global_px_y = tile_y * TILE_SIZE + local_y + stride / 2
                grid_x = int(round(global_px_x / stride))
                grid_y = int(round(global_px_y / stride))
                node_id = f"{grid_x}:{grid_y}"
                if node_id in nodes:
                    # Keep the more preferred class if duplicate cells overlap between tiles.
                    old_class = str(nodes[node_id].get("road_class", "unknown"))
                    if ROAD_CLASS_PRIORITY.get(road_class, 9) < ROAD_CLASS_PRIORITY.get(old_class, 9):
                        nodes[node_id]["road_class"] = road_class
                    continue
                nodes[node_id] = {
                    "id": node_id,
                    "map_x": round((grid_x * stride) / scale, 3),
                    "map_y": round((grid_y * stride) / scale, 3),
                    "road_class": road_class,
                    "road_ratio": round(combined_ratio, 4),
                    "white_ratio": round(white_ratio, 4),
                    "orange_ratio": round(orange_ratio, 4),
                }
                class_counts[road_class] = class_counts.get(road_class, 0) + 1

        if idx == 1 or idx % 100 == 0 or idx == tile_count:
            print(f"  {idx:>5}/{tile_count} tiles · nodes={len(nodes)}")

    if not nodes:
        raise SystemExit("No road-like pixels were detected. Try lowering thresholds or using another zoom/layer.")

    node_keys = set(nodes.keys())
    edges: list[dict] = []
    edge_class_counts: dict[str, int] = {"white": 0, "orange": 0, "orange_dashed": 0, "unknown": 0}
    neighbor_offsets = [(1, 0), (0, 1)]
    if args.connect_diagonal:
        # Optional only. Diagonal grid links can create ugly corner-cutting on noisy CV masks.
        neighbor_offsets += [(1, 1), (1, -1)]

    for node_id, node in nodes.items():
        gx_s, gy_s = node_id.split(":", 1)
        gx, gy = int(gx_s), int(gy_s)
        for dx, dy in neighbor_offsets:
            other_id = f"{gx + dx}:{gy + dy}"
            if other_id not in node_keys:
                continue
            other = nodes[other_id]
            length = math.hypot(float(node["map_x"]) - float(other["map_x"]), float(node["map_y"]) - float(other["map_y"]))
            edge_class = combine_edge_class(str(node.get("road_class", "unknown")), str(other.get("road_class", "unknown")))
            cost = length * multiplier_for_class(edge_class, args)
            edges.append({
                "from": node_id,
                "to": other_id,
                "length": round(length, 3),
                "cost": round(cost, 3),
                "road_class": edge_class,
            })
            edge_class_counts[edge_class] = edge_class_counts.get(edge_class, 0) + 1

    graph = {
        "version": "0.9.7-road-cv-magenta-aware-runtime-repair",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "map_id": args.map_id,
        "layer_id": args.layer,
        "zoom": args.zoom,
        "scale": scale,
        "tile_size": TILE_SIZE,
        "stride_px": args.stride,
        "notes": "Weighted CV graph. Balanced priority: prefer asphalt/white roads, but avoid absurd detours.",
        "route_priority": {
            "white": args.white_cost_factor,
            "orange": args.orange_cost_factor,
            "orange_dashed": args.orange_dashed_cost_factor,
            "unknown": args.unknown_cost_factor,
        },
        "detection": {
            "alpha_min": args.alpha_min,
            "light_value_min": args.light_value_min,
            "light_sat_max": args.light_sat_max,
            "light_minc_min": args.light_minc_min,
            "orange_r_min": args.orange_r_min,
            "orange_g_min": args.orange_g_min,
            "orange_g_max": args.orange_g_max,
            "orange_b_max": args.orange_b_max,
            "orange_rb_delta_min": args.orange_rb_delta_min,
            "orange_rg_delta_min": args.orange_rg_delta_min,
            "magenta_r_min": args.magenta_r_min,
            "magenta_b_min": args.magenta_b_min,
            "magenta_g_max": args.magenta_g_max,
            "magenta_rg_delta_min": args.magenta_rg_delta_min,
            "magenta_bg_delta_min": args.magenta_bg_delta_min,
            "min_road_ratio": args.min_road_ratio,
            "white_min_ratio": args.white_min_ratio,
            "orange_solid_ratio": args.orange_solid_ratio,
            "use_morphology": args.use_morphology,
            "kernel": args.kernel,
            "min_component_area": args.min_component_area,
            "component_min_span": args.component_min_span,
            "component_min_elongation": args.component_min_elongation,
            "component_large_area": args.component_large_area,
            "component_max_fill_ratio": args.component_max_fill_ratio,
            "white_component_min_elongation": args.white_component_min_elongation,
            "white_component_large_area": args.white_component_large_area,
            "white_component_max_fill_ratio": args.white_component_max_fill_ratio,
            "connect_diagonal": args.connect_diagonal,
        },
        "node_class_counts": class_counts,
        "edge_class_counts": edge_class_counts,
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    return graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FH6 road_graph.json from cached map tiles.")
    parser.add_argument("--tile-cache", default="tile_cache", help="Path to tile_cache directory near the app/exe.")
    parser.add_argument("--output", default="data/road_graph.json", help="Output graph JSON path.")
    parser.add_argument("--map-id", type=int, default=MAP_ID)
    parser.add_argument("--layer", type=int, default=DEFAULT_LAYER_ID, help="Layer id: 760 Summer, 757 Autumn, 758 Winter, 759 Spring, 756 All Seasons.")
    parser.add_argument("--zoom", type=int, default=DEFAULT_ZOOM)
    parser.add_argument("--stride", type=int, default=14, help="Grid step in tile pixels. Smaller = more accurate, heavier graph.")
    parser.add_argument("--min-road-ratio", type=float, default=0.16, help="Minimum road-pixel ratio in a grid cell.")
    parser.add_argument("--white-min-ratio", type=float, default=0.13, help="Minimum white-road ratio for a cell to be classified as preferred white road.")
    parser.add_argument("--orange-solid-ratio", type=float, default=0.28, help="Orange cells below this ratio are treated as dashed/trail and penalized.")
    parser.add_argument("--keep-unknown-cells", action="store_true", default=False, help="Keep detected cells that cannot be classified. Off by default.")
    parser.add_argument("--connect-diagonal", action="store_true", default=False, help="Connect diagonal neighbor nodes too. Off by default to avoid diagonal shortcuts.")
    parser.add_argument("--no-connect-diagonal", dest="connect_diagonal", action="store_false")
    parser.add_argument("--alpha-min", type=int, default=35)
    parser.add_argument("--light-value-min", type=int, default=188)
    parser.add_argument("--light-sat-max", type=int, default=48)
    parser.add_argument("--light-minc-min", type=int, default=145)
    parser.add_argument("--orange-r-min", type=int, default=185)
    parser.add_argument("--orange-g-min", type=int, default=75)
    parser.add_argument("--orange-g-max", type=int, default=175)
    parser.add_argument("--orange-b-max", type=int, default=115)
    parser.add_argument("--orange-rb-delta-min", type=int, default=85)
    parser.add_argument("--orange-rg-delta-min", type=int, default=8)
    parser.add_argument("--magenta-r-min", type=int, default=150)
    parser.add_argument("--magenta-b-min", type=int, default=105)
    parser.add_argument("--magenta-g-max", type=int, default=120)
    parser.add_argument("--magenta-rg-delta-min", type=int, default=45)
    parser.add_argument("--magenta-bg-delta-min", type=int, default=35)
    parser.add_argument("--use-morphology", action="store_true", default=True)
    parser.add_argument("--no-morphology", dest="use_morphology", action="store_false")
    parser.add_argument("--kernel", type=int, default=3)
    parser.add_argument("--min-component-area", type=int, default=55)
    parser.add_argument("--component-min-span", type=int, default=26)
    parser.add_argument("--component-min-elongation", type=float, default=1.8)
    parser.add_argument("--component-large-area", type=int, default=1200)
    parser.add_argument("--component-max-fill-ratio", type=float, default=0.52, help="Reject compact filled blobs above this fill ratio unless very elongated.")
    parser.add_argument("--white-component-min-elongation", type=float, default=2.35)
    parser.add_argument("--white-component-large-area", type=int, default=4200)
    parser.add_argument("--white-component-max-fill-ratio", type=float, default=0.36, help="Stricter fill-ratio filter for white building/roof false positives.")
    parser.add_argument("--white-cost-factor", type=float, default=1.00)
    parser.add_argument("--orange-cost-factor", type=float, default=1.12)
    parser.add_argument("--orange-dashed-cost-factor", type=float, default=2.35)
    parser.add_argument("--unknown-cost-factor", type=float, default=8.00)
    parser.add_argument("--preview-dir", default="", help="Optional folder for preview PNGs with detected road pixels painted green/amber.")
    args = parser.parse_args()

    graph = build_graph(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nDone.")
    print(f"  nodes: {len(graph['nodes'])}")
    print(f"  edges: {len(graph['edges'])}")
    print(f"  node classes: {graph.get('node_class_counts')}")
    print(f"  edge classes: {graph.get('edge_class_counts')}")
    print(f"  output: {output.resolve()}")
    print("\nRestart FH6 Live Map after building the graph so /api/route can load it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
