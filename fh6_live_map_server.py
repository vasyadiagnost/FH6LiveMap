#!/usr/bin/env python3
from __future__ import annotations

import argparse
import heapq
import json
import math
import mimetypes
import socket
import struct
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

APP_NAME = "FH6 Live Map"
APP_VERSION = "0.9.26-meme-layer-fullscreen-fast-jump"

OFFICIAL_PACKET_SIZE = 324
A, B, C = 0.652837, 0.000763, 10387.027
D, E, F = -0.003754, -0.657135, 9846.097
MAP_ID = 481
DEFAULT_LAYER_ID = 760
MIN_ZOOM, MAX_ZOOM = 12, 18
TILE_SIZE = 256
MAP_WIDTH, MAP_HEIGHT = 20000, 20000

INDEX_HTML = """<!doctype html><html lang='ru'><head><meta charset='utf-8'><title>FH6 Live Map</title></head><body style='font-family:system-ui;background:#070b12;color:#e5e7eb;padding:24px'><h1>FH6 Live Map</h1><p>index_work.html не найден рядом с программой. Верните файл index_work.html в папку проекта / сборки.</p></body></html>"""
def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative_path
    return Path(__file__).resolve().parent / relative_path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


MEME_SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
MEME_EVENT_ORDER = ["mega_fail_crash", "collision", "jump_takeoff"]
MEME_EVENT_DEFAULTS: dict[str, dict[str, Any]] = {
    "mega_fail_crash": {
        "enabled": True,
        "folder": "samples/mega_fail_crash",
        "cooldown_sec": 8.0,
        "window_sec": 0.15,
        "min_previous_speed_kmh": 120.0,
        "max_current_speed_kmh": 15.0,
        "min_speed_drop_kmh": 100.0,
        "priority": 120,
    },
    "collision": {
        "enabled": True,
        "folder": "samples/collision",
        "cooldown_sec": 4.5,
        "window_sec": 0.5,
        "min_speed_drop_kmh": 40.0,
        "min_previous_speed_kmh": 60.0,
        "max_brake_pct": 5.0,
        "priority": 100,
    },
    "jump_takeoff": {
        "enabled": True,
        "folder": "samples/jump_takeoff",
        "cooldown_sec": 4.0,
        "detection_mode": "fast_freefall_confirmed",
        "min_speed_kmh": 75.0,
        "takeoff_lookback_sec": 2.8,
        "freefall_window_sec": 0.15,
        "min_freefall_duration_sec": 0.15,
        "min_freefall_samples": 2,
        "min_takeoff_vertical_speed_mps": 1.0,
        "min_vertical_speed_gain_mps": 1.1,
        "min_takeoff_rise_m": 0.75,
        "max_freefall_vertical_speed_mps": -0.25,
        "max_freefall_avg_accel_mps2": -0.45,
        "min_drop_from_recent_apex_m": 0.18,
        "max_apex_age_sec": 2.4,
        "min_fall_ratio": 0.018,
        "priority": 60,
    },
}
MEME_DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "volume": 0.85,
    "global_cooldown_sec": 2.5,
    "supported_extensions": sorted(MEME_SUPPORTED_EXTENSIONS),
    "events": MEME_EVENT_DEFAULTS,
}

MEME_CONFIG_SCHEMA_VERSION = 4
MEME_0923_STRICT_JUMP_DEFAULTS = {
    "cooldown_sec": 6.0,
    "window_sec": 0.28,
    "min_speed_kmh": 80.0,
    "min_vertical_delta": 1.0,
    "min_vertical_speed_mps": 5.0,
    "min_vertical_speed_gain_mps": 3.0,
    "min_rise_ratio": 0.12,
}


def maybe_migrate_meme_config(data: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """Migrate old meme-layer configs without touching user sample folders.

    v0.9.26 keeps the confirmed freefall idea, but reduces the
    confirmation delay to about 0.15 seconds and removes the old keep-screen-awake UI in
    favor of a lightweight fullscreen button.
    User-facing toggles, folders and sample files are preserved.
    """
    changed = False
    events = data.get("events") if isinstance(data.get("events"), dict) else {}
    if not isinstance(events, dict):
        events = {}
        data["events"] = events
        changed = True

    # Ensure all event blocks exist. Preserve existing user folders/enabled flags.
    for event_name, defaults in MEME_EVENT_DEFAULTS.items():
        current = events.get(event_name)
        if not isinstance(current, dict):
            events[event_name] = dict(defaults)
            changed = True
            continue
        for key, value in defaults.items():
            if key not in current:
                current[key] = value
                changed = True

    jump_cfg = events.get("jump_takeoff")
    if isinstance(jump_cfg, dict):
        new_jump = MEME_EVENT_DEFAULTS["jump_takeoff"]
        old_schema = int(data.get("config_schema_version") or 0)
        new_required_keys = (
            "detection_mode",
            "takeoff_lookback_sec",
            "freefall_window_sec",
            "min_freefall_duration_sec",
            "min_freefall_samples",
            "min_takeoff_vertical_speed_mps",
            "min_takeoff_rise_m",
            "max_freefall_vertical_speed_mps",
            "max_freefall_avg_accel_mps2",
            "min_drop_from_recent_apex_m",
            "min_vertical_speed_gain_mps",
            "max_apex_age_sec",
            "min_fall_ratio",
        )
        if old_schema < MEME_CONFIG_SCHEMA_VERSION:
            # Keep folder/enabled, but move detection thresholds to the new model.
            for key in new_required_keys:
                if jump_cfg.get(key) != new_jump[key]:
                    jump_cfg[key] = new_jump[key]
                    changed = True
            if float(jump_cfg.get("cooldown_sec", 0) or 0) < float(new_jump["cooldown_sec"]):
                jump_cfg["cooldown_sec"] = new_jump["cooldown_sec"]
                changed = True

    if data.get("config_schema_version") != MEME_CONFIG_SCHEMA_VERSION:
        data["config_schema_version"] = MEME_CONFIG_SCHEMA_VERSION
        changed = True
    if changed:
        try:
            config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("[meme] config migrated to v0.9.26 fast freefall jump detector")
        except Exception as exc:
            print(f"[meme] config migration skipped: {exc}")
    return data



def meme_layer_dir() -> Path:
    """User-editable meme layer folder next to the script/EXE."""
    return app_dir() / "data" / "meme_layer"


def meme_samples_dir() -> Path:
    return meme_layer_dir() / "samples"


def load_index_html() -> str:
    """Prefer editable/bundled index_work.html, keep embedded INDEX_HTML as a safe fallback."""
    candidates = [app_dir() / "index_work.html", resource_path("index_work.html")]
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except Exception:
            pass
    return INDEX_HTML


def ensure_meme_layer_files() -> None:
    base = meme_layer_dir()
    samples = meme_samples_dir()
    base.mkdir(parents=True, exist_ok=True)
    samples.mkdir(parents=True, exist_ok=True)
    for event_name, cfg in MEME_EVENT_DEFAULTS.items():
        folder = samples / Path(str(cfg.get("folder", f"samples/{event_name}"))).name
        folder.mkdir(parents=True, exist_ok=True)
        note = folder / "PUT_YOUR_SAMPLES_HERE.txt"
        if not note.exists():
            note.write_text(
                "Drop your .mp3, .wav, .ogg, .m4a, .aac or .flac files into this folder.\n"
                "The phone web UI will load and play them from the PC over local Wi-Fi.\n",
                encoding="utf-8",
            )
    config_path = base / "config.json"
    if not config_path.exists():
        config_path.write_text(json.dumps(MEME_DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
    readme_path = base / "README_Meme_Layer.txt"
    if not readme_path.exists():
        readme_path.write_text(
            "FH6 Live Map Meme Layer\n"
            "=======================\n\n"
            "Put custom sound samples on the PC here:\n"
            "  data/meme_layer/samples/collision\n"
            "  data/meme_layer/samples/mega_fail_crash\n"
            "  data/meme_layer/samples/jump_takeoff\n\n"
            "Supported formats: .mp3, .wav, .ogg, .m4a, .aac, .flac\n"
            "Open the map on your phone, go to Settings, press 'Enable sound', and use Rescan after adding files.\n\n"
            "Events:\n"
            "  collision        - brake is not pressed, speed before hit was 60+ km/h, speed dropped by 40+ km/h in 0.5 s\n"
            "  mega_fail_crash  - speed was 120+ km/h and fell to 15 km/h or lower in about 0.15 s\n"
            "  jump_takeoff     - confirmed jump / fast freefall after ramp\n",
            encoding="utf-8",
        )


def load_meme_config() -> dict[str, Any]:
    ensure_meme_layer_files()
    config_path = meme_layer_dir() / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = maybe_migrate_meme_config(data, config_path)
            merged = json.loads(json.dumps(MEME_DEFAULT_CONFIG, ensure_ascii=False))
            merged.update({k: v for k, v in data.items() if k != "events"})
            merged_events = dict(MEME_EVENT_DEFAULTS)
            custom_events = data.get("events") if isinstance(data.get("events"), dict) else {}
            for event_name, defaults in MEME_EVENT_DEFAULTS.items():
                event_cfg = dict(defaults)
                custom_cfg = custom_events.get(event_name)
                if isinstance(custom_cfg, dict):
                    event_cfg.update(custom_cfg)
                merged_events[event_name] = event_cfg
            merged["events"] = merged_events
            return merged
    except Exception as exc:
        print(f"[meme] config read failed, using defaults: {exc}")
    return MEME_DEFAULT_CONFIG


def resolve_meme_event_folder(event_name: str, config: dict[str, Any] | None = None) -> Path | None:
    config = config or load_meme_config()
    events = config.get("events") if isinstance(config.get("events"), dict) else {}
    event_cfg = events.get(event_name)
    if not isinstance(event_cfg, dict):
        return None
    folder_rel = str(event_cfg.get("folder") or f"samples/{event_name}").replace("\\", "/").strip("/")
    root = meme_layer_dir().resolve()
    folder = (root / folder_rel).resolve()
    try:
        folder.relative_to(root)
    except ValueError:
        return None
    return folder


def list_meme_samples() -> dict[str, Any]:
    config = load_meme_config()
    events_out: dict[str, Any] = {}
    for event_name in MEME_EVENT_ORDER:
        event_cfg = dict(config.get("events", {}).get(event_name, {}))
        folder = resolve_meme_event_folder(event_name, config)
        files = []
        if folder is not None:
            folder.mkdir(parents=True, exist_ok=True)
            for file_path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                if not file_path.is_file() or file_path.suffix.lower() not in MEME_SUPPORTED_EXTENSIONS:
                    continue
                try:
                    stat = file_path.stat()
                except OSError:
                    continue
                files.append({
                    "name": file_path.name,
                    "size_bytes": stat.st_size,
                    "mtime": int(stat.st_mtime),
                    "url": f"/api/meme/sample/{quote(event_name, safe='')}/{quote(file_path.name, safe='')}",
                })
        events_out[event_name] = {
            "enabled": bool(event_cfg.get("enabled", True)),
            "folder": str(event_cfg.get("folder") or f"samples/{event_name}"),
            "folder_path": str(folder) if folder is not None else "",
            "count": len(files),
            "files": files,
            "config": event_cfg,
        }
    return {
        "ok": True,
        "base_path": str(meme_layer_dir()),
        "enabled": bool(config.get("enabled", True)),
        "volume": float(config.get("volume", 0.85) or 0.85),
        "global_cooldown_sec": float(config.get("global_cooldown_sec", 2.5) or 2.5),
        "supported_extensions": sorted(MEME_SUPPORTED_EXTENSIONS),
        "event_order": MEME_EVENT_ORDER,
        "events": events_out,
    }


def read_meme_sample(event_name: str, filename: str) -> tuple[bytes, str] | None:
    config = load_meme_config()
    folder = resolve_meme_event_folder(event_name, config)
    if folder is None:
        return None
    root = folder.resolve()
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix.lower() not in MEME_SUPPORTED_EXTENSIONS:
        return None
    mime_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return candidate.read_bytes(), mime_type


def build_fh6_fields():
    fields = []
    def add(name, fmt):
        fields.append((name, fmt))
    add("IsRaceOn", "i")
    add("TimestampMS", "I")
    for name in [
        "EngineMaxRpm","EngineIdleRpm","CurrentEngineRpm",
        "AccelerationX","AccelerationY","AccelerationZ",
        "VelocityX","VelocityY","VelocityZ",
        "AngularVelocityX","AngularVelocityY","AngularVelocityZ",
        "Yaw","Pitch","Roll",
        "NormalizedSuspensionTravelFrontLeft","NormalizedSuspensionTravelFrontRight",
        "NormalizedSuspensionTravelRearLeft","NormalizedSuspensionTravelRearRight",
        "TireSlipRatioFrontLeft","TireSlipRatioFrontRight","TireSlipRatioRearLeft","TireSlipRatioRearRight",
        "WheelRotationSpeedFrontLeft","WheelRotationSpeedFrontRight","WheelRotationSpeedRearLeft","WheelRotationSpeedRearRight",
    ]:
        add(name, "f")
    for name in [
        "WheelOnRumbleStripFrontLeft","WheelOnRumbleStripFrontRight","WheelOnRumbleStripRearLeft","WheelOnRumbleStripRearRight",
        "WheelInPuddleFrontLeft","WheelInPuddleFrontRight","WheelInPuddleRearLeft","WheelInPuddleRearRight",
    ]:
        add(name, "i")
    for name in [
        "SurfaceRumbleFrontLeft","SurfaceRumbleFrontRight","SurfaceRumbleRearLeft","SurfaceRumbleRearRight",
        "TireSlipAngleFrontLeft","TireSlipAngleFrontRight","TireSlipAngleRearLeft","TireSlipAngleRearRight",
        "TireCombinedSlipFrontLeft","TireCombinedSlipFrontRight","TireCombinedSlipRearLeft","TireCombinedSlipRearRight",
        "SuspensionTravelMetersFrontLeft","SuspensionTravelMetersFrontRight","SuspensionTravelMetersRearLeft","SuspensionTravelMetersRearRight",
    ]:
        add(name, "f")
    for name in ["CarOrdinal","CarClass","CarPerformanceIndex","DrivetrainType","NumCylinders"]:
        add(name, "i")
    add("CarGroup", "I")
    for name in [
        "SmashableVelDiff","SmashableMass","PositionX","PositionY","PositionZ",
        "Speed","Power","Torque","TireTempFrontLeft","TireTempFrontRight","TireTempRearLeft","TireTempRearRight",
        "Boost","Fuel","DistanceTraveled","BestLap","LastLap","CurrentLap","CurrentRaceTime",
    ]:
        add(name, "f")
    add("LapNumber", "H")
    add("RacePosition", "B")
    for name in ["Accel","Brake","Clutch","HandBrake","Gear"]:
        add(name, "B")
    for name in ["Steer","NormalizedDrivingLine","NormalizedAIBrakeDifference"]:
        add(name, "b")
    return fields


FH6_FIELDS = build_fh6_fields()
FH6_STRUCT_FORMAT = "<" + "".join(fmt for _, fmt in FH6_FIELDS)
FH6_STRUCT_SIZE = struct.calcsize(FH6_STRUCT_FORMAT)


@dataclass
class TelemetrySnapshot:
    receiving: bool = False
    packet_count: int = 0
    dropped_short: int = 0
    packet_size: int = 0
    last_packet_age: float | None = None
    timestamp_ms: int = 0
    position_x: float | None = None
    position_y: float | None = None
    position_z: float | None = None
    map_x: float | None = None
    map_y: float | None = None
    speed_mps: float = 0.0
    speed_kmh: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0
    yaw_rad: float = 0.0
    yaw_deg: float = 0.0
    heading_deg: float = 0.0
    gear: int = 0
    rpm: float = 0.0
    engine_max_rpm: float = 0.0
    distance_traveled_m: float = 0.0
    throttle_pct: float = 0.0
    brake_pct: float = 0.0
    steer: int = 0


class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_packet_time = None
        self.udp_error = None
        self.last_good_position = None
        self.snapshot = TelemetrySnapshot()

    def set_udp_error(self, message: str):
        with self.lock:
            self.udp_error = message

    def clear_udp_error(self):
        with self.lock:
            self.udp_error = None

    def update_from_packet(self, telemetry: dict[str, Any], packet_size: int):
        now = time.time()
        raw_pos_x = float(telemetry.get("PositionX", 0.0))
        raw_pos_y = float(telemetry.get("PositionY", 0.0))
        raw_pos_z = float(telemetry.get("PositionZ", 0.0))
        raw_map_x, raw_map_y = forza_to_map(raw_pos_x, raw_pos_z)

        speed_mps = float(telemetry.get("Speed", 0.0))
        gear = int(telemetry.get("Gear", 0))
        yaw_rad = float(telemetry.get("Yaw", 0.0))
        vx = float(telemetry.get("VelocityX", 0.0))
        vy = float(telemetry.get("VelocityY", 0.0))
        vz = float(telemetry.get("VelocityZ", 0.0))

        # FH6 can emit a bogus / menu-like coordinate when the game is paused or loses focus.
        # In that state telemetry usually reports speed=0 and Gear=0, which the UI shows as "-".
        # For immersion we keep the last accepted driving coordinate until real driving telemetry resumes.
        pause_coordinate_hold = bool(speed_mps <= 0.20 and gear == 0 and self.last_good_position is not None)

        if pause_coordinate_hold:
            pos_x, pos_y, pos_z, map_x, map_y, held_yaw, held_heading = self.last_good_position
            effective_yaw_rad = held_yaw
            effective_heading_deg = held_heading
        else:
            pos_x, pos_y, pos_z = raw_pos_x, raw_pos_y, raw_pos_z
            map_x, map_y = raw_map_x, raw_map_y
            effective_yaw_rad = yaw_rad
            effective_heading_deg = compute_screen_heading_deg(yaw_rad, vx, vz, speed_mps)
            self.last_good_position = (pos_x, pos_y, pos_z, map_x, map_y, effective_yaw_rad, effective_heading_deg)

        with self.lock:
            self.udp_error = None
            prev = self.snapshot
            self.last_packet_time = now
            self.snapshot = TelemetrySnapshot(
                receiving=True,
                packet_count=prev.packet_count + 1,
                dropped_short=prev.dropped_short,
                packet_size=packet_size,
                last_packet_age=0.0,
                timestamp_ms=int(telemetry.get("TimestampMS", 0)),
                position_x=pos_x, position_y=pos_y, position_z=pos_z,
                map_x=map_x, map_y=map_y,
                speed_mps=speed_mps, speed_kmh=speed_mps * 3.6,
                velocity_x=vx, velocity_y=vy, velocity_z=vz,
                yaw_rad=effective_yaw_rad, yaw_deg=math.degrees(effective_yaw_rad),
                heading_deg=effective_heading_deg,
                gear=gear,
                rpm=float(telemetry.get("CurrentEngineRpm", 0.0)),
                engine_max_rpm=float(telemetry.get("EngineMaxRpm", 0.0)),
                distance_traveled_m=float(telemetry.get("DistanceTraveled", 0.0)),
                throttle_pct=float(telemetry.get("Accel", 0.0)) / 255.0 * 100.0,
                brake_pct=float(telemetry.get("Brake", 0.0)) / 255.0 * 100.0,
                steer=int(telemetry.get("Steer", 0)),
            )

    def mark_short_packet(self, packet_size: int):
        with self.lock:
            self.snapshot.dropped_short += 1
            self.snapshot.packet_size = packet_size

    def get_snapshot(self):
        with self.lock:
            snap = self.snapshot
            age = None if self.last_packet_time is None else time.time() - self.last_packet_time
            out = asdict(snap)
            out["last_packet_age"] = age
            out["receiving"] = bool(age is not None and age < 1.5)
            out["udp_error"] = self.udp_error
            out["pause_coordinate_hold"] = bool(self.last_good_position is not None and snap.speed_mps <= 0.20 and snap.gear == 0)
            has_position = out.get("map_x") is not None and out.get("map_y") is not None
            out["holding_last_position"] = bool((not out["receiving"]) and has_position)
            out["status"] = "LIVE" if out["receiving"] else ("HOLDING" if has_position else "WAITING")
            out["app"] = {"name": APP_NAME, "version": APP_VERSION}
            out["map"] = {
                "width": MAP_WIDTH, "height": MAP_HEIGHT,
                "tile_size": TILE_SIZE, "min_zoom": MIN_ZOOM, "max_zoom": MAX_ZOOM,
                "default_layer_id": DEFAULT_LAYER_ID,
                "formula": {"a": A, "b": B, "c": C, "d": D, "e": E, "f": F},
            }
            return out


STATE = SharedState()


def forza_to_map(position_x: float, position_z: float):
    return A * position_x + B * position_z + C, D * position_x + E * position_z + F


def map_vector_to_screen_angle_deg(map_dx: float, map_dy: float):
    return math.degrees(math.atan2(map_dx, -map_dy))


def compute_screen_heading_deg(yaw_rad: float, velocity_x: float, velocity_z: float, speed_mps: float):
    if speed_mps > 1.5:
        vx_map = A * velocity_x + B * velocity_z
        vy_map = D * velocity_x + E * velocity_z
        return map_vector_to_screen_angle_deg(vx_map, vy_map)
    forward_x = math.sin(yaw_rad)
    forward_z = math.cos(yaw_rad)
    fx_map = A * forward_x + B * forward_z
    fy_map = D * forward_x + E * forward_z
    return map_vector_to_screen_angle_deg(fx_map, fy_map)


def parse_packet(data: bytes):
    values = struct.unpack(FH6_STRUCT_FORMAT, data[:FH6_STRUCT_SIZE])
    return dict(zip((name for name, _ in FH6_FIELDS), values))


def udp_listener(bind: str, port: int, stop_event: threading.Event):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((bind, port))
        sock.settimeout(0.2)
    except OSError as e:
        message = f"Could not bind UDP telemetry on {bind}:{port}: {e}. Close other FH6LiveMap/FH6TelemetryExtractor processes or change the UDP port."
        print("UDP ERROR:", message)
        STATE.set_udp_error(message)
        return

    STATE.clear_udp_error()
    print(f"UDP telemetry: listening on {bind}:{port}")
    print(f"FH6 packet parser: official={OFFICIAL_PACKET_SIZE} bytes | parsed={FH6_STRUCT_SIZE} bytes")
    try:
        while not stop_event.is_set():
            try:
                data, _addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            if len(data) < FH6_STRUCT_SIZE:
                STATE.mark_short_packet(len(data))
                continue
            try:
                STATE.update_from_packet(parse_packet(data), len(data))
            except Exception:
                print("Failed to parse FH6 packet:")
                traceback.print_exc()
    finally:
        sock.close()



MARKERS_CACHE: list[dict[str, Any]] | None = None
ROAD_GRAPH_CACHE: dict[str, Any] | None = None
ROAD_GRAPH_CACHE_KEY: tuple[str, float] | None = None

ROAD_CLASS_MULTIPLIERS = {
    # White roads are asphalt and remain preferred. v0.9.8 fixes the important
    # practical detail: not every synthetic graph link is equal. Short synthetic
    # links usually repair broken road pixels under labels / tile seams / magenta
    # overlays; long synthetic links are likely scenery shortcuts and stay costly.
    "white": 1.00,
    "orange": 1.08,
    "orange_dashed": 2.60,
    "synthetic_short": 2.40,
    "synthetic_medium": 7.00,
    "synthetic_bridge": 34.00,
    "unknown": 9.50,
}
ROAD_CLASS_LABELS = {
    "white": "white roads",
    "orange": "orange roads",
    "orange_dashed": "orange dashed / trails",
    "synthetic_bridge": "graph stitches",
    "unknown": "unknown",
}

ROUTING_COST_PROFILES = {
    # Default navigator mode: asphalt/white first, but practical.
    "asphalt_practical": {
        "white": 1.00,
        "orange": 1.08,
        "orange_dashed": 2.60,
        "synthetic_short": 2.40,
        "synthetic_medium": 7.00,
        "synthetic_bridge": 34.00,
        "unknown": 9.50,
        "heuristic_weight": 1.45,
    },
    # Backup: permits orange and tiny CV gap bridges to avoid absurd white-road hooks.
    "detour_escape": {
        "white": 1.00,
        "orange": 1.02,
        "orange_dashed": 1.85,
        "synthetic_short": 1.65,
        "synthetic_medium": 4.20,
        "synthetic_bridge": 22.00,
        "unknown": 11.00,
        "heuristic_weight": 2.10,
    },
    # Last resort: finds the shortest sane graph route while still avoiding long
    # synthetic cuts through fields. This is for fragmented urban areas.
    "shortest_sane": {
        "white": 1.00,
        "orange": 1.00,
        "orange_dashed": 1.25,
        "synthetic_short": 1.25,
        "synthetic_medium": 2.80,
        "synthetic_bridge": 18.00,
        "unknown": 14.00,
        "heuristic_weight": 3.00,
    },
}

DETOUR_RATIO_SOFT_LIMIT = 1.35
DETOUR_EXTRA_PENALTY = 8.00

# CV road graphs are intentionally conservative. That keeps false roads out, but it
# also tears real roads apart under labels, magenta map overlays, bridges and tile
# seams. Runtime repair adds expensive synthetic links only between nearby broken
# components. These links are not preferred roads; they are crack-fillers so A* can
# produce a usable route instead of dying with "disconnected components".
LOCAL_STITCH_RADIUS_CELLS = 4
COMPONENT_BRIDGE_RADIUS_PX = 320.0
COMPONENT_BRIDGE_MIN_CLASS_SIZE = 2


def _normalize_road_class(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"white", "light", "road", "street", "main", "primary"}:
        return "white"
    if text in {"orange", "salmon", "secondary"}:
        return "orange"
    if text in {"orange_dashed", "dashed", "trail", "dirt", "path"}:
        return "orange_dashed"
    if text in {"magenta", "pink", "purple", "highway"}:
        return "white"
    if text in {"synthetic", "synthetic_bridge", "bridge", "stitch", "stitch_bridge", "component_bridge", "gap_bridge", "runtime_bridge"}:
        return "synthetic_bridge"
    return "unknown"


def _road_class_multiplier(value: Any) -> float:
    return float(ROAD_CLASS_MULTIPLIERS.get(_normalize_road_class(value), ROAD_CLASS_MULTIPLIERS["unknown"]))


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)



def load_markers_data() -> list[dict[str, Any]]:
    global MARKERS_CACHE
    if MARKERS_CACHE is not None:
        return MARKERS_CACHE
    try:
        data = json.loads(resource_path("data/markers.json").read_text(encoding="utf-8"))
        MARKERS_CACHE = data if isinstance(data, list) else []
    except Exception:
        MARKERS_CACHE = []
    return MARKERS_CACHE


def find_marker(marker_id: str) -> dict[str, Any] | None:
    needle = str(marker_id)
    for marker in load_markers_data():
        if str(marker.get("markerId", "")) == needle or str(marker.get("id", "")) == needle:
            return marker
    return None



def road_graph_paths() -> list[Path]:
    # Generated graphs should live next to the script/exe, so the user can rebuild them
    # without repackaging. Bundled graph is only a fallback.
    paths = [app_dir() / "data" / "road_graph.json"]
    try:
        bundled = resource_path("data/road_graph.json")
        if bundled not in paths:
            paths.append(bundled)
    except Exception:
        pass
    return paths



class _Dsu:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.size = [1] * size

    def find(self, item: int) -> int:
        parent = self.parent
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(self, a: int, b: int) -> bool:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True


def _parse_grid_id(node_id: str, x: float, y: float, stride: float) -> tuple[int, int]:
    if ":" in node_id:
        left, right = node_id.split(":", 1)
        try:
            return int(left), int(right)
        except ValueError:
            pass
    safe_stride = stride if stride > 0 else 10.0
    return int(round(x / safe_stride)), int(round(y / safe_stride))


def _build_components(adjacency: list[list[tuple[int, float]]]) -> tuple[list[int], list[int]]:
    component = [-1] * len(adjacency)
    sizes: list[int] = []
    for start in range(len(adjacency)):
        if component[start] != -1:
            continue
        cid = len(sizes)
        stack = [start]
        component[start] = cid
        count = 0
        while stack:
            node = stack.pop()
            count += 1
            for neighbor, _cost in adjacency[node]:
                if component[neighbor] == -1:
                    component[neighbor] = cid
                    stack.append(neighbor)
        sizes.append(count)
    return component, sizes


def _build_spatial_index(coords: list[tuple[float, float]], cell_size: float = 320.0) -> dict[tuple[int, int], list[int]]:
    spatial: dict[tuple[int, int], list[int]] = {}
    for idx, (x, y) in enumerate(coords):
        key = (int(x // cell_size), int(y // cell_size))
        spatial.setdefault(key, []).append(idx)
    return spatial


def _simplify_polyline(points: list[tuple[float, float]], epsilon: float = 7.0, max_points: int = 2600) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points

    def point_line_distance(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        px, py = p
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        denom = dx * dx + dy * dy
        if denom <= 1e-9:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
        qx, qy = ax + t * dx, ay + t * dy
        return math.hypot(px - qx, py - qy)

    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        a = points[start]
        b = points[end]
        best_i = -1
        best_d = -1.0
        for i in range(start + 1, end):
            d = point_line_distance(points[i], a, b)
            if d > best_d:
                best_d = d
                best_i = i
        if best_i >= 0 and best_d > epsilon:
            keep.add(best_i)
            stack.append((start, best_i))
            stack.append((best_i, end))
    simplified = [points[i] for i in sorted(keep)]
    if len(simplified) <= max_points:
        return simplified
    step = max(1, math.ceil(len(simplified) / max_points))
    sampled = simplified[::step]
    if sampled[-1] != simplified[-1]:
        sampled.append(simplified[-1])
    return sampled


def load_road_graph(force: bool = False) -> dict[str, Any] | None:
    global ROAD_GRAPH_CACHE, ROAD_GRAPH_CACHE_KEY
    graph_file = next((p for p in road_graph_paths() if p.exists() and p.stat().st_size > 0), None)
    if graph_file is None:
        ROAD_GRAPH_CACHE = None
        ROAD_GRAPH_CACHE_KEY = None
        return None

    key = (str(graph_file.resolve()), graph_file.stat().st_mtime)
    if not force and ROAD_GRAPH_CACHE is not None and ROAD_GRAPH_CACHE_KEY == key:
        return ROAD_GRAPH_CACHE

    started = time.time()
    try:
        raw = json.loads(graph_file.read_text(encoding="utf-8"))
        raw_nodes = raw.get("nodes", [])
        raw_edges = raw.get("edges", [])
        stride = float(raw.get("stride_px") or raw.get("stride") or 10.0)

        node_ids: list[str] = []
        coords: list[tuple[float, float]] = []
        grid_keys: list[tuple[int, int]] = []
        node_classes: list[str] = []
        id_to_index: dict[str, int] = {}
        node_class_counts: dict[str, int] = {}

        for idx, node in enumerate(raw_nodes):
            road_class = "unknown"
            if isinstance(node, dict):
                node_id = str(node.get("id", idx))
                x = node.get("map_x", node.get("x"))
                y = node.get("map_y", node.get("y"))
                road_class = _normalize_road_class(node.get("road_class") or node.get("kind") or node.get("type"))
            elif isinstance(node, (list, tuple)) and len(node) >= 2:
                node_id = str(idx)
                x, y = node[0], node[1]
            else:
                continue
            if x is None or y is None:
                continue
            fx, fy = float(x), float(y)
            id_to_index[node_id] = len(node_ids)
            node_ids.append(node_id)
            coords.append((fx, fy))
            grid_keys.append(_parse_grid_id(node_id, fx, fy, stride))
            node_classes.append(road_class)
            node_class_counts[road_class] = node_class_counts.get(road_class, 0) + 1

        adjacency: list[list[tuple[int, float]]] = [[] for _ in node_ids]
        edge_class_lookup: dict[tuple[int, int], str] = {}
        edge_length_lookup: dict[tuple[int, int], float] = {}
        edge_class_counts: dict[str, int] = {}
        dsu = _Dsu(len(node_ids))
        raw_edge_count = 0

        def add_edge(a: int, b: int, length: float, weighted_cost: float, road_class: str) -> None:
            if a == b or length <= 0:
                return
            adjacency[a].append((b, weighted_cost))
            adjacency[b].append((a, weighted_cost))
            key2 = _edge_key(a, b)
            existing = edge_length_lookup.get(key2)
            if existing is None or weighted_cost < existing * _road_class_multiplier(edge_class_lookup.get(key2, "unknown")):
                edge_class_lookup[key2] = road_class
                edge_length_lookup[key2] = length
            edge_class_counts[road_class] = edge_class_counts.get(road_class, 0) + 1
            dsu.union(a, b)

        for edge in raw_edges:
            road_class = "unknown"
            length = None
            cost = None
            if isinstance(edge, dict):
                a_id = str(edge.get("from", edge.get("a", "")))
                b_id = str(edge.get("to", edge.get("b", "")))
                cost = edge.get("cost")
                length = edge.get("length")
                road_class = _normalize_road_class(edge.get("road_class") or edge.get("kind") or edge.get("type"))
            elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
                a_id, b_id = str(edge[0]), str(edge[1])
                cost = edge[2] if len(edge) >= 3 else None
            else:
                continue
            a = id_to_index.get(a_id)
            b = id_to_index.get(b_id)
            if a is None or b is None or a == b:
                continue
            ax, ay = coords[a]
            bx, by = coords[b]
            physical_len = float(length) if length is not None else math.hypot(ax - bx, ay - by)
            if road_class == "unknown" and 0 <= a < len(node_classes) and 0 <= b < len(node_classes):
                # Old graphs had no edge class. New graphs do, but this keeps future hand-edited graphs usable.
                ca, cb = node_classes[a], node_classes[b]
                # Prefer the less preferred class on mixed edges.
                order = {"white": 0, "orange": 1, "orange_dashed": 2, "synthetic_bridge": 3, "unknown": 4}
                road_class = ca if order.get(ca, 9) >= order.get(cb, 9) else cb
            if cost is not None and road_class == "unknown":
                weighted = float(cost)
            elif cost is not None and length is not None:
                # v0.9.4 graph builder already writes weighted cost. Preserve it.
                weighted = float(cost)
            else:
                weighted = physical_len * _road_class_multiplier(road_class)
            add_edge(a, b, physical_len, weighted, road_class)
            raw_edge_count += 1

        stitch_edges = 0
        component_bridge_edges = 0
        version_text = str(raw.get("version", "")).lower()
        is_cv_graph = "road-cv" in version_text or "cv" in version_text or bool(raw.get("detection"))

        # 1) Small local stitches: close 1-4 cell gaps caused by anti-aliasing,
        # labels or turning off diagonal grid links in the extractor.
        stitch_radius_cells = int(raw.get("runtime_stitch_radius_cells") or (LOCAL_STITCH_RADIUS_CELLS if is_cv_graph else 0))
        if stitch_radius_cells and node_ids:
            grid_to_index: dict[tuple[int, int], int] = {}
            for idx, key2 in enumerate(grid_keys):
                grid_to_index.setdefault(key2, idx)
            offsets: list[tuple[int, int]] = []
            r = max(1, stitch_radius_cells)
            for dx in range(0, r + 1):
                for dy in range(-r, r + 1):
                    if dx == 0 and dy <= 0:
                        continue
                    if dx * dx + dy * dy <= r * r:
                        offsets.append((dx, dy))
            max_bridge = max(stride * r + 0.01, 1.0)
            for idx, (gx, gy) in enumerate(grid_keys):
                for dx, dy in offsets:
                    other = grid_to_index.get((gx + dx, gy + dy))
                    if other is None or other == idx:
                        continue
                    if dsu.find(idx) == dsu.find(other):
                        continue
                    ax, ay = coords[idx]
                    bx, by = coords[other]
                    length = math.hypot(ax - bx, ay - by)
                    if 0.0 < length <= max_bridge:
                        bridge_cost = length * ROAD_CLASS_MULTIPLIERS["synthetic_bridge"]
                        add_edge(idx, other, length, bridge_cost, "synthetic_bridge")
                        stitch_edges += 1

        # 2) Component bridges: conservative CV often creates separate islands of the
        # same real road, especially where the map has magenta overlays or dense city
        # labels. We connect nearest neighbouring islands with expensive synthetic
        # links. Kruskal-style sorting keeps the shortest possible crack-fillers and
        # prevents a dense spiderweb of shortcuts.
        component_bridge_radius = float(raw.get("runtime_component_bridge_radius_px") or (COMPONENT_BRIDGE_RADIUS_PX if is_cv_graph else 0.0))
        if component_bridge_radius > 0 and node_ids:
            bridgeable_classes = {"white", "orange"}
            spatial_bridge: dict[tuple[int, int], list[int]] = {}
            cell = max(80.0, component_bridge_radius)
            for idx, (x, y) in enumerate(coords):
                if node_classes[idx] not in bridgeable_classes:
                    continue
                spatial_bridge.setdefault((int(x // cell), int(y // cell)), []).append(idx)

            nearest_between_components: dict[tuple[int, int], tuple[float, int, int]] = {}
            for idx, (x, y) in enumerate(coords):
                if node_classes[idx] not in bridgeable_classes:
                    continue
                root_a = dsu.find(idx)
                cx, cy = int(x // cell), int(y // cell)
                for gx in range(cx - 1, cx + 2):
                    for gy in range(cy - 1, cy + 2):
                        for other in spatial_bridge.get((gx, gy), []):
                            if other <= idx:
                                continue
                            root_b = dsu.find(other)
                            if root_a == root_b:
                                continue
                            ox, oy = coords[other]
                            length = math.hypot(ox - x, oy - y)
                            if not (0.0 < length <= component_bridge_radius):
                                continue
                            # Avoid letting tiny false-positive specks pull the graph together.
                            # DSU sizes after local stitches are a good enough proxy here.
                            if dsu.size[root_a] < COMPONENT_BRIDGE_MIN_CLASS_SIZE or dsu.size[root_b] < COMPONENT_BRIDGE_MIN_CLASS_SIZE:
                                continue
                            pair_key = (root_a, root_b) if root_a < root_b else (root_b, root_a)
                            class_penalty = 0.0 if node_classes[idx] == node_classes[other] else 35.0
                            score = length + class_penalty
                            old = nearest_between_components.get(pair_key)
                            if old is None or score < old[0]:
                                nearest_between_components[pair_key] = (score, idx, other)

            # Add shortest inter-component links first. Stop naturally when candidates
            # are exhausted; remaining components are genuinely isolated or too far away.
            for _score, idx, other in sorted(nearest_between_components.values(), key=lambda item: item[0]):
                if dsu.find(idx) == dsu.find(other):
                    continue
                ax, ay = coords[idx]
                bx, by = coords[other]
                length = math.hypot(ax - bx, ay - by)
                if not (0.0 < length <= component_bridge_radius):
                    continue
                bridge_cost = length * ROAD_CLASS_MULTIPLIERS["synthetic_bridge"]
                add_edge(idx, other, length, bridge_cost, "synthetic_bridge")
                component_bridge_edges += 1

        component, component_sizes = _build_components(adjacency)
        spatial_cell_size = 320.0
        spatial = _build_spatial_index(coords, spatial_cell_size)
        edge_count = sum(len(items) for items in adjacency) // 2
        meta = {k: v for k, v in raw.items() if k not in ("nodes", "edges")}
        meta.update({
            "raw_edge_count": raw_edge_count,
            "stitch_edges": stitch_edges,
            "component_bridge_edges": component_bridge_edges,
            "component_bridge_radius_px": component_bridge_radius if 'component_bridge_radius' in locals() else 0,
            "local_stitch_radius_cells": stitch_radius_cells if 'stitch_radius_cells' in locals() else 0,
            "component_count": len(component_sizes),
            "largest_components": sorted(component_sizes, reverse=True)[:8],
            "load_seconds": round(time.time() - started, 3),
            "node_class_counts_runtime": node_class_counts,
            "edge_class_counts_runtime": edge_class_counts,
            "route_cost_multipliers": ROAD_CLASS_MULTIPLIERS,
        })
        ROAD_GRAPH_CACHE = {
            "path": str(graph_file),
            "meta": meta,
            "node_ids": node_ids,
            "nodes": node_ids,
            "coords": coords,
            "node_classes": node_classes,
            "id_to_index": id_to_index,
            "adjacency": adjacency,
            "edge_class_lookup": edge_class_lookup,
            "edge_length_lookup": edge_length_lookup,
            "component": component,
            "component_sizes": component_sizes,
            "spatial": spatial,
            "spatial_cell_size": spatial_cell_size,
            "edges_count": edge_count,
        }
        ROAD_GRAPH_CACHE_KEY = key
        print(
            f"[routing] loaded road graph: nodes={len(node_ids)} edges={edge_count} "
            f"components={len(component_sizes)} stitched={stitch_edges} component_bridges={component_bridge_edges} path={graph_file}"
        )
        return ROAD_GRAPH_CACHE
    except Exception as exc:
        print(f"[routing] failed to load road graph {graph_file}: {exc}")
        traceback.print_exc()
        ROAD_GRAPH_CACHE = None
        ROAD_GRAPH_CACHE_KEY = None
        return None

def nearest_graph_nodes(graph: dict[str, Any], x: float, y: float, limit: int = 10, max_distance: float = 900.0) -> list[tuple[int, float]]:
    coords: list[tuple[float, float]] = graph["coords"]
    spatial: dict[tuple[int, int], list[int]] = graph.get("spatial", {})
    cell_size = float(graph.get("spatial_cell_size", 320.0))
    if not coords:
        return []
    cx, cy = int(x // cell_size), int(y // cell_size)
    max_ring = int(math.ceil(max_distance / cell_size)) + 1
    candidates: list[tuple[float, int]] = []
    seen: set[int] = set()
    for ring in range(max_ring + 1):
        for gx in range(cx - ring, cx + ring + 1):
            for gy in range(cy - ring, cy + ring + 1):
                if ring and abs(gx - cx) < ring and abs(gy - cy) < ring:
                    continue
                for idx in spatial.get((gx, gy), []):
                    if idx in seen:
                        continue
                    seen.add(idx)
                    nx, ny = coords[idx]
                    d = math.hypot(nx - x, ny - y)
                    if d <= max_distance:
                        candidates.append((d, idx))
        if len(candidates) >= limit * 4 and ring >= 1:
            break
    if not candidates:
        # Safe fallback for unusual coordinates or empty spatial buckets.
        for idx, (nx, ny) in enumerate(coords):
            d = math.hypot(nx - x, ny - y)
            if d <= max_distance:
                candidates.append((d, idx))
    candidates.sort(key=lambda item: item[0])
    return [(idx, dist) for dist, idx in candidates[:limit]]


def _synthetic_multiplier_for_length(length: float, profile: dict[str, float]) -> float:
    if length <= 70.0:
        return float(profile.get("synthetic_short", profile.get("synthetic_bridge", 34.0)))
    if length <= 180.0:
        return float(profile.get("synthetic_medium", profile.get("synthetic_bridge", 34.0)))
    return float(profile.get("synthetic_bridge", ROAD_CLASS_MULTIPLIERS["synthetic_bridge"]))


def _route_edge_cost(graph: dict[str, Any], a: int, b: int, profile: dict[str, float] | None = None) -> float:
    """Return runtime edge cost.

    Older graph files and even some v0.9.4 graphs may contain precomputed edge costs.
    For navigation we deliberately recompute the cost from physical length + current
    profile so changing routing behavior does not require rebuilding the graph.
    """
    key = _edge_key(a, b)
    length_lookup: dict[tuple[int, int], float] = graph.get("edge_length_lookup", {})
    class_lookup: dict[tuple[int, int], str] = graph.get("edge_class_lookup", {})
    coords: list[tuple[float, float]] = graph["coords"]
    ax, ay = coords[a]
    bx, by = coords[b]
    physical_len = float(length_lookup.get(key, math.hypot(ax - bx, ay - by)))
    road_class = _normalize_road_class(class_lookup.get(key, "unknown"))
    multipliers = profile or ROAD_CLASS_MULTIPLIERS
    if road_class == "synthetic_bridge":
        multiplier = _synthetic_multiplier_for_length(physical_len, multipliers)
    else:
        multiplier = float(multipliers.get(road_class, multipliers.get("unknown", ROAD_CLASS_MULTIPLIERS["unknown"])))
    return physical_len * multiplier


def _route_physical_length(graph: dict[str, Any], node_indices: list[int]) -> float:
    if len(node_indices) < 2:
        return 0.0
    coords: list[tuple[float, float]] = graph["coords"]
    length_lookup: dict[tuple[int, int], float] = graph.get("edge_length_lookup", {})
    total = 0.0
    for a, b in zip(node_indices, node_indices[1:]):
        ax, ay = coords[a]
        bx, by = coords[b]
        total += float(length_lookup.get(_edge_key(a, b), math.hypot(ax - bx, ay - by)))
    return total


def _detour_penalty(physical_total: float, direct_px: float) -> float:
    if direct_px <= 1.0:
        return 0.0
    soft_limit = max(direct_px * DETOUR_RATIO_SOFT_LIMIT, direct_px + 950.0)
    if physical_total <= soft_limit:
        return 0.0
    return (physical_total - soft_limit) * DETOUR_EXTRA_PENALTY


def shortest_graph_path(
    graph: dict[str, Any],
    start_idx: int,
    goal_idx: int,
    max_visited: int | None = None,
    profile: dict[str, float] | None = None,
) -> tuple[list[int], float, int] | None:
    if start_idx == goal_idx:
        return [start_idx], 0.0, 0
    component = graph.get("component") or []
    if component and component[start_idx] != component[goal_idx]:
        return None
    coords: list[tuple[float, float]] = graph["coords"]
    adjacency: list[list[tuple[int, float]]] = graph["adjacency"]
    gx, gy = coords[goal_idx]
    if max_visited is None:
        # Weighted A* profiles can re-open nodes; one visit per node is too tight on
        # the hand-corrected graph. Keep the old hard ceiling spirit, but give the
        # search enough headroom before declaring "no path".
        max_visited = min(max(420000, len(coords) * 4), 900000)

    def heuristic(node_idx: int) -> float:
        # The cheapest road multiplier is 1.0, so plain geometric distance remains
        # admissible for all current profiles.
        ax, ay = coords[node_idx]
        return math.hypot(ax - gx, ay - gy)

    heuristic_weight = float((profile or {}).get("heuristic_weight", 1.0))
    open_heap: list[tuple[float, float, int]] = [(heuristic(start_idx) * heuristic_weight, 0.0, start_idx)]
    came_from: dict[int, int | None] = {start_idx: None}
    best_cost: dict[int, float] = {start_idx: 0.0}
    visited = 0

    while open_heap and visited < max_visited:
        _priority, cost_so_far, current = heapq.heappop(open_heap)
        if cost_so_far != best_cost.get(current):
            continue
        visited += 1
        if current == goal_idx:
            path = [current]
            while came_from[path[-1]] is not None:
                path.append(came_from[path[-1]])
            path.reverse()
            return path, cost_so_far, visited
        for neighbor, _stored_edge_cost in adjacency[current]:
            edge_cost = _route_edge_cost(graph, current, neighbor, profile)
            new_cost = cost_so_far + edge_cost
            if new_cost < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = new_cost
                came_from[neighbor] = current
                heapq.heappush(open_heap, (new_cost + heuristic(neighbor) * heuristic_weight, new_cost, neighbor))
    return None

def make_route_response(target_x: float, target_y: float, title: str = "Destination") -> dict[str, Any]:
    snap = STATE.get_snapshot()
    start_x = snap.get("map_x")
    start_y = snap.get("map_y")
    if start_x is None or start_y is None:
        return {"ok": False, "mode": "waiting_for_telemetry", "error": "No current car position yet", "polyline": []}

    start_x = float(start_x)
    start_y = float(start_y)
    direct_px = math.hypot(target_x - start_x, target_y - start_y)
    direct = {
        "ok": True,
        "mode": "direct",
        "target_title": title,
        "distance_px": round(direct_px, 2),
        "distance_meters": round(direct_px / 0.655),
        "polyline": [
            {"map_x": round(start_x, 3), "map_y": round(start_y, 3)},
            {"map_x": round(target_x, 3), "map_y": round(target_y, 3)},
        ],
        "message": "Direct preview route. Build data/road_graph.json for road-graph routing.",
    }

    graph = load_road_graph()
    if not graph or not graph.get("coords"):
        return direct

    def graph_failed(mode: str, message: str, routing: dict[str, Any] | None = None) -> dict[str, Any]:
        # Do not silently draw a diagonal when a road graph exists but cannot produce a path.
        # A diagonal fallback looked like a real route and made debugging impossible.
        return {
            "ok": False,
            "mode": mode,
            "target_title": title,
            "distance_px": round(direct_px, 2),
            "distance_meters": round(direct_px / 0.655),
            "polyline": [],
            "message": message,
            "routing": routing or {},
        }

    start_candidates = nearest_graph_nodes(graph, start_x, start_y, limit=96, max_distance=1800.0)
    goal_candidates = nearest_graph_nodes(graph, target_x, target_y, limit=96, max_distance=1800.0)
    if not start_candidates or not goal_candidates:
        return graph_failed(
            "graph_snap_failed",
            "Road graph exists, but the car or target is too far from a detected road node.",
            {"start_candidates": len(start_candidates), "goal_candidates": len(goal_candidates)},
        )

    component = graph.get("component") or []
    candidate_pairs: list[tuple[float, int, int, float, float]] = []
    for start_idx, start_snap in start_candidates:
        for goal_idx, goal_snap in goal_candidates:
            if component and component[start_idx] != component[goal_idx]:
                continue
            comp_size = graph.get("component_sizes", [0])[component[start_idx]] if component else 0
            # Prefer candidates on substantial road components so tiny false-positive blobs near the car
            # do not win over the actual nearby road network.
            component_penalty = 600.0 / math.sqrt(max(1, comp_size))
            candidate_pairs.append((start_snap + goal_snap + component_penalty, start_idx, goal_idx, start_snap, goal_snap))
    candidate_pairs.sort(key=lambda item: item[0])

    if not candidate_pairs:
        start_components: dict[int, int] = {}
        goal_components: dict[int, int] = {}
        if component:
            for idx, _d in start_candidates:
                start_components[component[idx]] = start_components.get(component[idx], 0) + 1
            for idx, _d in goal_candidates:
                goal_components[component[idx]] = goal_components.get(component[idx], 0) + 1
        return graph_failed(
            "graph_disconnected",
            "Road graph exists, but nearby car/target road candidates are in disconnected components.",
            {
                "start_candidates": len(start_candidates),
                "goal_candidates": len(goal_candidates),
                "start_components": len(start_components),
                "goal_components": len(goal_components),
            },
        )

    best_result = None
    best_meta = None
    # Try snapped combinations and two profiles. The first keeps asphalt/white preferred;
    # the second prevents absurd detours when a short connector is orange/dashed.
    for _snap_sum, start_idx, goal_idx, start_snap, goal_snap in candidate_pairs[:4]:
        for profile_name, profile in ROUTING_COST_PROFILES.items():
            graph_path = shortest_graph_path(graph, start_idx, goal_idx, profile=profile)
            if not graph_path:
                continue
            node_indices, graph_cost, visited = graph_path
            physical_graph_px = _route_physical_length(graph, node_indices)
            physical_total = start_snap + physical_graph_px + goal_snap
            weighted_total = start_snap * 1.20 + graph_cost + goal_snap * 1.05
            detour_penalty = _detour_penalty(physical_total, direct_px)

            # Route sanity: prefer asphalt, but route length matters more than worshipping
            # white pixels. Also make long synthetic bridges very visible to the scorer.
            edge_class_lookup = graph.get("edge_class_lookup", {})
            length_lookup = graph.get("edge_length_lookup", {})
            synthetic_long_px = 0.0
            synthetic_total_px = 0.0
            non_asphalt_px = 0.0
            for aa, bb in zip(node_indices, node_indices[1:]):
                key2 = _edge_key(aa, bb)
                cls2 = _normalize_road_class(edge_class_lookup.get(key2, "unknown"))
                ax, ay = graph["coords"][aa]
                bx, by = graph["coords"][bb]
                length2 = float(length_lookup.get(key2, math.hypot(ax - bx, ay - by)))
                if cls2 == "synthetic_bridge":
                    synthetic_total_px += length2
                    if length2 > 180.0:
                        synthetic_long_px += length2
                elif cls2 != "white":
                    non_asphalt_px += length2
            sanity_penalty = non_asphalt_px * 0.08 + synthetic_total_px * 0.35 + synthetic_long_px * 2.75
            final_score = weighted_total + detour_penalty + sanity_penalty
            if best_result is None or final_score < best_result[1]:
                best_result = (node_indices, final_score, graph_cost, physical_graph_px, physical_total, profile_name, detour_penalty)
                best_meta = (start_idx, goal_idx, start_snap, goal_snap, visited)

    if best_result is None or best_meta is None:
        return graph_failed(
            "graph_no_path",
            "Road graph exists, but A* could not find a connected path between snapped road nodes.",
            {"candidate_pairs": len(candidate_pairs)},
        )

    node_indices, route_cost_px, graph_cost, precomputed_physical_graph_px, precomputed_physical_total, profile_name, detour_penalty = best_result
    start_idx, goal_idx, start_snap, goal_snap, visited = best_meta
    coords: list[tuple[float, float]] = graph["coords"]
    edge_class_lookup: dict[tuple[int, int], str] = graph.get("edge_class_lookup", {})

    road_profile: dict[str, int] = {}
    road_profile_length: dict[str, float] = {}
    length_lookup: dict[tuple[int, int], float] = graph.get("edge_length_lookup", {})
    physical_graph_px = 0.0
    for a, b in zip(node_indices, node_indices[1:]):
        ax, ay = coords[a]
        bx, by = coords[b]
        length = float(length_lookup.get(_edge_key(a, b), math.hypot(ax - bx, ay - by)))
        physical_graph_px += length
        cls = _normalize_road_class(edge_class_lookup.get(_edge_key(a, b), "unknown"))
        road_profile[cls] = road_profile.get(cls, 0) + 1
        road_profile_length[cls] = round(road_profile_length.get(cls, 0.0) + length, 2)

    # Keep the value used during scoring to avoid tiny differences from repeated summing.
    if precomputed_physical_graph_px > 0:
        physical_graph_px = precomputed_physical_graph_px
    physical_distance_px = start_snap + physical_graph_px + goal_snap

    full_points = [(start_x, start_y)]
    full_points.extend(coords[idx] for idx in node_indices)
    if math.hypot(full_points[-1][0] - target_x, full_points[-1][1] - target_y) > 1.0:
        full_points.append((target_x, target_y))
    simplified = _simplify_polyline(full_points, epsilon=7.0)
    polyline = [{"map_x": round(x, 3), "map_y": round(y, 3)} for x, y in simplified]

    preferred_bits = []
    for cls in ("white", "orange", "orange_dashed", "synthetic_bridge", "unknown"):
        count = road_profile.get(cls, 0)
        if count:
            preferred_bits.append(f"{cls}:{count}")
    profile_text = ", ".join(preferred_bits) if preferred_bits else "unknown"

    return {
        "ok": True,
        "mode": "graph",
        "target_title": title,
        "graph_path_nodes": len(node_indices),
        "polyline_points": len(polyline),
        "visited_nodes": visited,
        "distance_px": round(physical_distance_px, 2),
        "distance_meters": round(physical_distance_px / 0.655),
        "polyline": polyline,
        "message": "Road graph route built with practical asphalt priority, short-gap repair and runtime graph stitching.",
        "routing": {
            "start_node": graph["node_ids"][start_idx],
            "goal_node": graph["node_ids"][goal_idx],
            "start_snap_px": round(start_snap, 2),
            "goal_snap_px": round(goal_snap, 2),
            "graph_cost_px": round(graph_cost, 2),
            "route_cost_px": round(route_cost_px, 2),
            "physical_graph_px": round(physical_graph_px, 2),
            "candidate_pairs": len(candidate_pairs),
            "profile": profile_name,
            "detour_penalty": round(detour_penalty, 2),
            "direct_px": round(direct_px, 2),
            "detour_ratio": round(physical_distance_px / max(1.0, direct_px), 3),
            "road_profile": road_profile,
            "road_profile_length_px": road_profile_length,
            "road_profile_text": profile_text,
        },
    }


def search_markers(query: str, limit: int = 25) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return []
    terms = [t for t in q.split() if t]
    snap = STATE.get_snapshot()
    px, py = snap.get("map_x"), snap.get("map_y")
    results = []
    for marker in load_markers_data():
        hay = " ".join(str(marker.get(k, "")) for k in ("title", "category", "parent_category", "description", "desc")).lower()
        if not all(term in hay for term in terms):
            continue
        item = dict(marker)
        if px is not None and py is not None:
            item["distance_px"] = round(math.hypot(float(marker.get("map_x", 0)) - float(px), float(marker.get("map_y", 0)) - float(py)), 2)
        results.append(item)
    if px is not None and py is not None:
        results.sort(key=lambda item: item.get("distance_px", float("inf")))
    else:
        results.sort(key=lambda item: str(item.get("title", "")))
    return results[: max(1, min(limit, 100))]

class Handler(BaseHTTPRequestHandler):
    server_version = f"{APP_NAME}/{APP_VERSION}"

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/state"):
            return
        super().log_message(fmt, *args)

    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_bytes(self, data: bytes, content_type: str, status=200, cache=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=86400" if cache else "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_bytes(load_index_html().encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/state":
            self.send_json(STATE.get_snapshot())
            return
        if path == "/api/qr.svg":
            query = parse_qs(urlparse(self.path).query)
            text = query.get("text", [""])[0]
            self.send_bytes(make_qr_svg(text), "image/svg+xml; charset=utf-8")
            return
        if path == "/asset/fh6_full_map_source.jpeg":
            try:
                p = resource_path("data/fh6_full_map_source.jpeg")
                self.send_bytes(p.read_bytes(), "image/jpeg", cache=True)
            except Exception:
                self.send_error(HTTPStatus.NOT_FOUND, "Map fallback image not found")
            return
        if path == "/api/info":
            port = self.server.server_address[1]
            lan_ips = get_lan_ips()
            self.send_json({
                "http_port": port,
                "lan_ips": lan_ips,
                "phone_urls": [f"http://{ip}:{port}/" for ip in lan_ips],
                "local_url": f"http://127.0.0.1:{port}/",
            })
            return
        if path in ("/api/meme/samples", "/api/meme/rescan"):
            try:
                self.send_json(list_meme_samples())
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=500)
            return
        if path.startswith("/api/meme/sample/"):
            try:
                rest = path[len("/api/meme/sample/"):].split("/", 1)
                if len(rest) != 2:
                    self.send_error(HTTPStatus.BAD_REQUEST, "Bad meme sample path")
                    return
                event_name = unquote(rest[0])
                filename = unquote(rest[1])
                sample = read_meme_sample(event_name, filename)
                if sample is None:
                    self.send_error(HTTPStatus.NOT_FOUND, "Meme sample not found")
                    return
                data, mime_type = sample
                self.send_bytes(data, mime_type, cache=False)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=500)
            return
        if path.startswith("/api/media/"):
            action = path.rsplit("/", 1)[-1]
            ok, message = send_windows_media_key(action)
            self.send_json({"ok": ok, "action": action, "error": None if ok else message, "message": message})
            return
        if path == "/api/diagnostics":
            self.send_json(STATE.get_snapshot())
            return
        if path == "/api/search":
            query = parse_qs(urlparse(self.path).query)
            q = query.get("q", query.get("query", [""]))[0]
            try:
                limit = int(query.get("limit", [25])[0])
            except ValueError:
                limit = 25
            self.send_json(search_markers(q, limit=limit))
            return
        if path == "/api/route":
            query = parse_qs(urlparse(self.path).query)
            marker = None
            marker_id = query.get("marker_id", [""])[0]
            if marker_id:
                marker = find_marker(marker_id)
            try:
                if marker is not None:
                    target_x = float(marker.get("map_x"))
                    target_y = float(marker.get("map_y"))
                    target_title = str(marker.get("title", "Destination"))
                else:
                    target_x = float(query.get("target_x", query.get("x", [""]))[0])
                    target_y = float(query.get("target_y", query.get("y", [""]))[0])
                    target_title = query.get("target_title", query.get("title", ["Destination"]))[0]
                self.send_json(make_route_response(target_x, target_y, target_title))
            except Exception as e:
                self.send_json({"ok": False, "mode": "error", "error": str(e), "polyline": []}, status=400)
            return
        if path == "/api/graph/status":
            graph = load_road_graph()
            if graph:
                self.send_json({"ok": True, "nodes": len(graph.get("coords", [])), "edges": graph.get("edges_count", 0), "path": graph.get("path"), "meta": graph.get("meta", {})})
            else:
                self.send_json({"ok": False, "nodes": 0, "edges": 0, "message": "data/road_graph.json not found"})
            return
        if path == "/api/markers":
            try:
                self.send_json(load_markers_data())
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)
            return
        if path.startswith("/tile/"):
            parts = path.strip("/").split("/")
            if len(parts) != 5:
                self.send_error(HTTPStatus.BAD_REQUEST, "Bad tile path")
                return
            _, layer_id, z, x, y_png = parts
            self.serve_tile(layer_id, z, x, y_png.replace(".png", ""))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path.startswith("/api/media/"):
            action = path.rsplit("/", 1)[-1]
            ok, message = send_windows_media_key(action)
            self.send_json({"ok": ok, "action": action, "error": None if ok else message, "message": message})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


    def serve_tile(self, layer_id: str, z: str, x: str, y: str):
        if not (layer_id.isdigit() and z.isdigit() and x.lstrip("-").isdigit() and y.lstrip("-").isdigit()):
            self.send_error(HTTPStatus.BAD_REQUEST, "Bad tile parameters")
            return
        cache_dir = app_dir() / "tile_cache" / str(MAP_ID) / layer_id / z
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{x}-{y}.png"
        if cache_file.exists() and cache_file.stat().st_size > 0:
            self.send_bytes(cache_file.read_bytes(), "image/png", cache=True)
            return
        url = f"https://www.gamerguides.com/assets/maps/{MAP_ID}/{layer_id}/{z}/{x}-{y}.png"
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": f"{APP_NAME}/{APP_VERSION} local preview",
                "Accept": "image/png,image/*;q=0.8,*/*;q=0.5",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            cache_file.write_bytes(data)
            self.send_bytes(data, "image/png", cache=True)
        except Exception:
            transparent_png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c636000000200010005fe02fea5579a0000000049454e44ae426082")
            self.send_bytes(transparent_png, "image/png")



def send_windows_media_key(action: str) -> tuple[bool, str]:
    """Send system-wide media keys on Windows. A phone browser can trigger this endpoint over LAN."""
    if sys.platform != "win32":
        return False, "Media keys are currently implemented for Windows only."

    key_map = {
        "playpause": 0xB3,
        "next": 0xB0,
        "prev": 0xB1,
        "volup": 0xAF,
        "voldown": 0xAE,
    }
    vk = key_map.get(action)
    if vk is None:
        return False, f"Unknown media action: {action}"

    try:
        import ctypes
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.03)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return True, "sent"
    except Exception as e:
        return False, str(e)



def make_qr_svg(text: str) -> bytes:
    try:
        import qrcode
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(text, image_factory=factory, box_size=8, border=2)
        return img.to_string(encoding="unicode").encode("utf-8")
    except Exception:
        escaped = (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="260" height="260" viewBox="0 0 260 260">
<rect width="260" height="260" fill="white"/>
<text x="130" y="100" text-anchor="middle" font-family="Arial" font-size="14" fill="#111">QR generator unavailable</text>
<text x="130" y="130" text-anchor="middle" font-family="Arial" font-size="11" fill="#111">{escaped}</text>
<text x="130" y="160" text-anchor="middle" font-family="Arial" font-size="10" fill="#555">Install qrcode package in build environment</text>
</svg>"""
        return svg.encode("utf-8")


def get_lan_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
            ip = item[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip not in ips and not ip.startswith("127."):
            ips.insert(0, ip)
    except Exception:
        pass
    return ips



def telemetry_heartbeat(stop_event: threading.Event) -> None:
    last_count = -1
    while not stop_event.is_set():
        time.sleep(2.0)
        snap = STATE.get_snapshot()
        count = snap.get("packet_count", 0)
        age = snap.get("last_packet_age")
        err = snap.get("udp_error")
        if err:
            print(f"[telemetry] UDP ERROR: {err}")
        elif count != last_count:
            age_text = "none" if age is None else f"{age:.2f}s"
            print(f"[telemetry] packets={count} receiving={snap.get('receiving')} last_age={age_text} speed={snap.get('speed_kmh', 0):.1f} km/h")
            last_count = count


def main():
    parser = argparse.ArgumentParser(description="FH6 Live Map local web preview.")
    parser.add_argument("--udp-bind", default="127.0.0.1")
    parser.add_argument("--udp-port", type=int, default=5700)
    parser.add_argument("--http-bind", default="0.0.0.0")
    parser.add_argument("--http-port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if 5200 <= args.udp_port <= 5300:
        print("Warning: Forza docs recommend avoiding UDP ports 5200 through 5300.")

    ensure_meme_layer_files()

    stop_event = threading.Event()
    threading.Thread(target=udp_listener, args=(args.udp_bind, args.udp_port, stop_event), daemon=True).start()
    threading.Thread(target=telemetry_heartbeat, args=(stop_event,), daemon=True).start()

    server = ThreadingHTTPServer((args.http_bind, args.http_port), Handler)
    local_url = f"http://127.0.0.1:{args.http_port}/"

    print("")
    print(f"{APP_NAME} v{APP_VERSION}")
    print("=" * 72)
    print("Forza Horizon 6 setup:")
    print("  Settings > HUD and Gameplay")
    print("  Data Out: ON")
    print("  Data Out IP Address: 127.0.0.1  (same PC)")
    print(f"  Data Out IP Port: {args.udp_port}")
    print(f"  Local UDP listener bind: {args.udp_bind}:{args.udp_port}")
    print("")
    print("Web UI:")
    print(f"  This PC: {local_url}")
    for ip in get_lan_ips():
        print(f"  Phone/LAN: http://{ip}:{args.http_port}/")
    print("")
    print("If Windows Firewall asks, allow Private network access.")
    print("Tile cache is stored near the EXE/script in: tile_cache/")
    print(f"Meme samples folder: {meme_samples_dir()}")
    print("Press Ctrl+C here to stop.")
    print("=" * 72)

    if not args.no_browser:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
