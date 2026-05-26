#!/usr/bin/env python3
from __future__ import annotations

import argparse
import heapq
import json
import math
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
from urllib.parse import parse_qs, urlparse

APP_NAME = "FH6 Live Map"
APP_VERSION = "0.9.15-compact-nearest-poi"

OFFICIAL_PACKET_SIZE = 324
A, B, C = 0.652837, 0.000763, 10387.027
D, E, F = -0.003754, -0.657135, 9846.097
MAP_ID = 481
DEFAULT_LAYER_ID = 760
MIN_ZOOM, MAX_ZOOM = 12, 18
TILE_SIZE = 256
MAP_WIDTH, MAP_HEIGHT = 20000, 20000

INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>FH6 Live Map · v0.9.15</title>\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<style>\n:root{--bg:#070b12;--panel:rgba(8,13,24,.84);--panel2:rgba(15,23,42,.92);--text:#e5e7eb;--muted:#9ca3af;--accent:#38bdf8;--good:#22c55e;--bad:#ef4444;--border:rgba(148,163,184,.24)}\n*{box-sizing:border-box}html,body{height:100%;margin:0;overflow:hidden;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif}\n#app{position:fixed;inset:0;overflow:hidden;background:radial-gradient(circle at center,#111827,#030712)}\n#mapViewport{position:absolute;inset:0;overflow:hidden;cursor:grab;touch-action:none}.dragging{cursor:grabbing!important}#mapWorld{position:absolute;inset:0;width:100%;height:100%;overflow:visible;transform:rotate(0deg);transform-origin:50% 50%;will-change:transform}#tileLayer,#routeLayer,#markerLayer{position:absolute;inset:0;width:100%;height:100%;overflow:visible;transform:none}#mapFallback{position:absolute;left:0;top:0;z-index:0;pointer-events:none;user-select:none;-webkit-user-drag:none;opacity:.92}#tileLayer{z-index:1}#routeLayer{pointer-events:none;z-index:82}#markerLayer{pointer-events:none;z-index:90}.marker,.poiPopup{pointer-events:auto}\n.tile{position:absolute;width:256px;height:256px;user-select:none;-webkit-user-drag:none;background:transparent}\n.marker{position:absolute;width:10px;height:10px;margin-left:-5px;margin-top:-5px;border-radius:50%;border:1px solid rgba(255,255,255,.85);box-shadow:0 0 0 2px rgba(0,0,0,.3),0 0 12px rgba(255,255,255,.18);cursor:pointer}\n.marker.speed{width:13px;height:13px;margin-left:-6.5px;margin-top:-6.5px}\n.marker.selected{width:24px;height:24px;margin-left:-12px;margin-top:-12px;border:3px solid #fff;z-index:120;box-shadow:0 0 0 5px rgba(56,189,248,.35),0 0 28px rgba(56,189,248,.95)}\n.poiPopup{position:absolute;z-index:240;min-width:240px;max-width:320px;background:rgba(8,13,24,.94);border:1px solid rgba(148,163,184,.34);border-radius:16px;padding:12px;box-shadow:0 16px 36px rgba(0,0,0,.42);backdrop-filter:blur(14px);pointer-events:auto}\n.poiPopupTitle{font-weight:850;font-size:15px;line-height:1.15;padding-right:30px}.poiPopupMeta{color:#9ca3af;font-size:12px;margin-top:4px}.poiPopupDesc{color:#d1d5db;font-size:12px;line-height:1.35;margin-top:10px}.poiPopupRow{display:flex;justify-content:space-between;gap:12px;border-top:1px solid rgba(148,163,184,.16);margin-top:8px;padding-top:8px;font-size:12px}.poiPopupActions{display:flex;gap:8px;margin-top:10px}.routeBtn{width:100%;min-height:36px;background:rgba(56,189,248,.18);border-color:rgba(56,189,248,.55)}.poiPopupClose{position:absolute;right:8px;top:7px;width:28px;height:28px;min-height:0;padding:0;border-radius:999px}\n.nearItem.clickable{cursor:pointer}.nearItem.clickable:hover{background:rgba(56,189,248,.12);border-radius:10px;padding-left:6px;padding-right:6px}\n.ipLine{color:#e5e7eb;font-weight:800}.ipLine small{color:#9ca3af;font-weight:650}.copyIpBtn{margin-left:8px;min-height:26px;padding:0 8px;border-radius:9px;font-size:11px}.qrWrap{margin-top:8px;display:flex;justify-content:flex-start}.qrWrap img{width:132px;height:132px;border-radius:12px;background:white;padding:8px}.pcLinkPanel.hideOnDevice{display:none!important}\n#app.navMode .topbar{display:none}#app.navMode .bottom{display:none}#app.navMode .marker{opacity:.42}\n.navTopInstruction{position:absolute;left:14px;top:14px;right:14px;z-index:310;display:none;background:#2563eb;color:#fff;border-radius:22px;padding:14px 16px;box-shadow:0 18px 40px rgba(0,0,0,.38);pointer-events:auto}\n#app.navMode .navTopInstruction{display:flex;align-items:center;gap:14px}.navArrow{font-size:38px;font-weight:900;line-height:1}.navText{font-size:18px;font-weight:850;line-height:1.15}.navSub{font-size:13px;opacity:.9;margin-top:3px}\n.navSpeedBubble{position:absolute;right:16px;top:104px;z-index:315;display:none;min-width:96px;height:58px;border-radius:18px;background:rgba(8,13,24,.86);color:#e5e7eb;border:1px solid rgba(148,163,184,.24);align-items:center;justify-content:center;font-weight:900;font-size:24px;box-shadow:0 12px 28px rgba(0,0,0,.34);backdrop-filter:blur(12px);padding:0 14px}\n#app.navMode .navSpeedBubble{display:flex}.navBottomBar{position:absolute;left:14px;right:14px;bottom:14px;z-index:315;display:none;background:rgba(255,255,255,.92);color:#111827;border-radius:20px;padding:10px 12px;box-shadow:0 18px 40px rgba(0,0,0,.38);pointer-events:auto;align-items:center;gap:12px}\n#app.navMode .navBottomBar{display:flex}.navExit{width:48px;height:48px;border-radius:14px;background:#e5e7eb;color:#111827;border:0;font-size:28px;min-height:0;padding:0}.navMetrics{display:flex;align-items:center;gap:18px;font-size:22px;font-weight:850;white-space:nowrap}\n.navTargetName{position:absolute;left:50%;bottom:92px;z-index:312;display:none;transform:translateX(-50%);background:rgba(255,255,255,.92);color:#111827;border-radius:16px;padding:9px 14px;font-weight:750;box-shadow:0 12px 28px rgba(0,0,0,.24);max-width:80vw;text-align:center}\n#app.navMode .navTargetName{display:block}.routeLine{position:absolute;height:10px;background:#63f000;border:2px solid rgba(16,185,129,.85);border-radius:999px;transform-origin:0 50%;box-shadow:0 0 0 4px rgba(99,240,0,.22),0 0 18px rgba(99,240,0,.65);z-index:82;display:none}\n#app.navMode .routeLine{display:block}.navDestination{position:absolute;width:26px;height:26px;margin-left:-13px;margin-top:-13px;border-radius:50%;background:#ef4444;border:4px solid #fff;box-shadow:0 0 0 5px rgba(239,68,68,.25),0 8px 18px rgba(0,0,0,.4);z-index:95;display:none}\n#app.navMode .navDestination{display:block}.navCompass{position:absolute;left:16px;top:104px;z-index:315;display:none;background:rgba(8,13,24,.84);color:#e5e7eb;border:1px solid rgba(148,163,184,.24);border-radius:16px;padding:8px 10px;font-size:12px;font-weight:800;box-shadow:0 10px 24px rgba(0,0,0,.28)}\n#app.navMode .navCompass{display:block}.musicWidget{position:absolute;right:16px;bottom:92px;z-index:316;display:none;background:rgba(8,13,24,.88);color:#e5e7eb;border:1px solid rgba(148,163,184,.24);border-radius:18px;padding:10px 12px;box-shadow:0 16px 36px rgba(0,0,0,.38);pointer-events:auto;min-width:210px}\n#app.navMode .musicWidget{display:block}.musicTitle{font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:.08em;font-weight:800;margin-bottom:8px}.musicButtons{display:flex;gap:8px}.musicButtons button{min-width:42px;min-height:38px;border-radius:12px;padding:0 10px}.musicStatus{font-size:11px;color:#9ca3af;margin-top:7px;min-height:14px}\n@media(max-width:900px),(pointer:coarse){.pcLinkPanel{display:none!important}}@media(max-width:760px){.navTopInstruction{border-radius:18px;padding:12px}.navText{font-size:16px}.navArrow{font-size:32px}.navSpeedBubble{min-width:88px;height:52px;font-size:22px;right:12px;top:92px}.navBottomBar{left:10px;right:10px;bottom:10px;border-radius:18px}.navMetrics{font-size:18px;gap:10px}.navExit{width:44px;height:44px}.navTargetName{bottom:84px}.musicWidget{right:10px;bottom:84px;min-width:190px;padding:9px}}\n\n.marker.selected{width:24px;height:24px;margin-left:-12px;margin-top:-12px;border:3px solid #fff;z-index:120;box-shadow:0 0 0 5px rgba(56,189,248,.35),0 0 28px rgba(56,189,248,.95)}\n.poiPopup{position:absolute;z-index:240;min-width:240px;max-width:320px;background:rgba(8,13,24,.94);border:1px solid rgba(148,163,184,.34);border-radius:16px;padding:12px;box-shadow:0 16px 36px rgba(0,0,0,.42);backdrop-filter:blur(14px);pointer-events:auto}\n.poiPopupTitle{font-weight:850;font-size:15px;line-height:1.15}.poiPopupMeta{color:#9ca3af;font-size:12px;margin-top:4px}.poiPopupRow{display:flex;justify-content:space-between;gap:12px;border-top:1px solid rgba(148,163,184,.16);margin-top:8px;padding-top:8px;font-size:12px}.poiPopupClose{position:absolute;right:8px;top:7px;width:28px;height:28px;min-height:0;padding:0;border-radius:999px}\n.nearItem.clickable{cursor:pointer}.nearItem.clickable:hover{background:rgba(56,189,248,.12);border-radius:10px;padding-left:6px;padding-right:6px}\n.player{position:absolute;width:24px;height:24px;border-radius:999px;background:#39ff14;border:4px solid #eaffea;box-shadow:0 0 0 5px rgba(57,255,20,.24),0 0 24px rgba(57,255,20,.95),0 8px 18px rgba(0,0,0,.45);z-index:100;margin-left:-12px;margin-top:-12px}\n.player:after{content:"";position:absolute;left:50%;top:50%;width:8px;height:8px;margin-left:-4px;margin-top:-4px;background:#052e05;border-radius:999px;opacity:.65}#app.navMode .player:before{content:"";position:absolute;left:50%;top:-13px;margin-left:-6px;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:14px solid #eaffea;filter:drop-shadow(0 0 8px rgba(57,255,20,.9))}\n.topbar{position:absolute;left:12px;top:12px;right:12px;display:flex;gap:10px;align-items:stretch;justify-content:space-between;pointer-events:none;z-index:200}\n.panel{background:var(--panel);border:1px solid var(--border);backdrop-filter:blur(14px);border-radius:16px;padding:10px 12px;box-shadow:0 12px 30px rgba(0,0,0,.28);pointer-events:auto}\n.status{min-width:280px}.title{font-weight:800;letter-spacing:.02em;font-size:15px}.sub{color:var(--muted);font-size:12px;margin-top:2px}\n.row{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-top:8px}.metric{min-width:86px}.label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.value{font-size:16px;font-weight:750;margin-top:1px}\n.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:700;background:rgba(148,163,184,.12);border:1px solid var(--border);white-space:nowrap}.dot{width:8px;height:8px;border-radius:50%;background:var(--bad)}.dot.on{background:var(--good);box-shadow:0 0 12px rgba(34,197,94,.8)}.dot.hold{background:var(--warn);box-shadow:0 0 12px rgba(245,158,11,.75)}\n.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}\nbutton,select{color:var(--text);background:var(--panel2);border:1px solid var(--border);border-radius:12px;min-height:38px;padding:0 12px;font:inherit}\nbutton{cursor:pointer;font-weight:750}button.active{background:rgba(56,189,248,.22);border-color:rgba(56,189,248,.7)}select{max-width:180px}\n.bottom{position:absolute;left:12px;bottom:12px;right:12px;display:flex;gap:10px;align-items:flex-end;justify-content:space-between;pointer-events:none;z-index:200}\n.nearest{max-width:min(520px,calc(100vw - 24px));pointer-events:auto}.nearestList{margin-top:8px;display:grid;gap:6px}\n.nearItem{display:flex;justify-content:space-between;gap:12px;font-size:13px;color:#d1d5db;border-top:1px solid rgba(148,163,184,.12);padding-top:6px}.nearItem b{color:#f8fafc}\n.searchPanel{min-width:300px;max-width:390px;pointer-events:auto}.searchBox{display:flex;gap:8px;margin-top:8px}.searchBox input{width:100%;min-height:38px;border-radius:12px;border:1px solid var(--border);background:rgba(15,23,42,.95);color:var(--text);padding:0 12px;font:inherit;outline:none}.searchBox input:focus{border-color:rgba(56,189,248,.75);box-shadow:0 0 0 3px rgba(56,189,248,.12)}.searchClear{min-width:38px;padding:0 10px}.searchResults{display:none;margin-top:8px;max-height:260px;overflow:auto;border-top:1px solid rgba(148,163,184,.16);padding-top:6px}.searchResults.open{display:grid;gap:6px}.searchItem{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;padding:7px 0;border-bottom:1px solid rgba(148,163,184,.10);font-size:13px}.searchItemTitle{font-weight:800;color:#f8fafc;line-height:1.15}.searchItemMeta{color:#9ca3af;font-size:12px;margin-top:2px}.searchItem button{min-height:32px;border-radius:10px;padding:0 10px;background:rgba(56,189,248,.16);border-color:rgba(56,189,248,.45)}.searchEmpty{color:var(--muted);font-size:12px;padding:6px 0}\n.hint{color:var(--muted);font-size:12px;line-height:1.35}.crosshair{position:absolute;left:50%;top:50%;width:14px;height:14px;margin-left:-7px;margin-top:-7px;border:1px solid rgba(255,255,255,.25);border-radius:999px;pointer-events:none;z-index:80}\n@media(max-width:900px),(pointer:coarse){.pcLinkPanel{display:none!important}}@media(max-width:760px){.topbar{flex-direction:column;right:8px;left:8px;top:8px}.panel{border-radius:14px;padding:9px}.status{min-width:0}.row{gap:8px}.metric{min-width:70px}.value{font-size:14px}.controls{justify-content:stretch}.searchPanel{min-width:0;max-width:none}.searchResults{max-height:190px}button,select{min-height:36px;padding:0 9px}.bottom{left:8px;right:8px;bottom:8px}.nearest{display:none}}\n\n/* v0.9.15 stable renderer + compact lower-left nearest POI */\n.mobileDock{display:none}\n#app.mediaCollapsed .musicWidget{display:none!important}\n.mobileSheetClose,.navInfoToggle,.navMediaToggle,.mediaCollapseBtn{color:var(--text);background:rgba(15,23,42,.92);border:1px solid var(--border)}\n.panelTitleRow{display:flex;align-items:center;justify-content:space-between;gap:10px}.mobileSheetClose{display:none;width:34px;height:34px;min-height:0;padding:0;border-radius:12px;font-size:20px;line-height:1}.musicHeader{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px}.musicHeader .musicTitle{margin-bottom:0}.mediaCollapseBtn{width:34px;height:34px;min-height:0;padding:0;border-radius:12px;font-size:18px;line-height:1}.navInfoToggle,.navMediaToggle{width:48px;height:48px;border-radius:14px;min-height:0;padding:0;font-size:22px;background:#e5e7eb;color:#111827;border:0}.navInfoToggle{font-weight:900}.navMediaToggle{margin-left:0}.navMetrics{flex:1}.mobileDockBtn .dockLabel{font-size:10px;line-height:1;letter-spacing:.02em}.mobileDockBtn .dockIcon{font-size:21px;line-height:1}.mobileInfoNearest{display:none}.mobileNearestOverlay{display:none;position:absolute;left:10px;right:auto;bottom:calc(var(--mobileDockH,68px) + env(safe-area-inset-bottom,0px) + 16px);z-index:346;width:min(235px,56vw);max-height:min(15dvh,128px);overflow:hidden;pointer-events:auto;border-radius:14px;padding:8px 10px;box-shadow:0 14px 34px rgba(0,0,0,.38)}.mobileNearestOverlay .panelTitleRow{gap:6px}.mobileNearestOverlay .title{font-size:12px;line-height:1.05}.mobileNearestOverlay .sub{display:none}.mobileNearestOverlay .mobileSheetClose{width:26px;height:26px;border-radius:9px;font-size:17px}.mobileNearestOverlay .nearestList{margin-top:4px;display:grid;gap:0}.mobileNearestOverlay .nearItem{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11px;line-height:1.15;padding:3px 0;border-top:1px solid rgba(148,163,184,.14);min-height:24px}.mobileNearestOverlay .nearItem:first-child{border-top:0}.mobileNearestOverlay .nearItem b{display:block;max-width:154px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11.5px;line-height:1.05}.mobileNearestOverlay .nearItem>span:first-child{min-width:0;overflow:hidden}.mobileNearestOverlay .nearItem>span:last-child{font-size:11px;white-space:nowrap;color:#dbeafe;font-weight:800}.mobileNearestOverlay .nearItem .sub{display:none!important}.mobileNearestOverlay .nearItem:nth-child(n+4){display:none}\n@media(max-width:760px),(pointer:coarse){\n  #app{--mobileDockH:68px;--mobileGap:10px}\n  body.mobileUi .topbar{left:0;right:0;top:0;bottom:0;display:block;pointer-events:none;z-index:330}\n  body.mobileUi .topbar .mobileSheet{position:absolute;left:10px;right:10px;top:10px;display:none;max-height:calc(100dvh - var(--mobileDockH) - 22px);overflow:auto;pointer-events:auto;border-radius:18px;padding:12px;box-shadow:0 18px 44px rgba(0,0,0,.44)}\n  body.mobileUi .topbar .mobileSheet.mobileOpen{display:block}\n  body.mobileUi .topbar .status{min-width:0}\n  body.mobileUi .topbar .controls{display:none;grid-template-columns:1fr 1fr;gap:8px;align-items:stretch;justify-content:stretch}\n  body.mobileUi .topbar .controls.mobileOpen{display:grid}\n  body.mobileUi .topbar .controls button,body.mobileUi .topbar .controls select{width:100%;max-width:none;min-height:44px}\n  body.mobileUi .topbar .controls .panelTitleRow{grid-column:1/-1}\n  body.mobileUi .mobileSheetClose{display:inline-flex;align-items:center;justify-content:center}\n  body.mobileUi .mobileInfoNearest{display:none!important}\n  body.mobileUi #app.nearestOpen .mobileNearestOverlay{display:block}\n  body.mobileUi #app.navMode.nearestOpen .mobileNearestOverlay{bottom:calc(env(safe-area-inset-bottom,0px) + 76px)}\n  body.mobileUi .searchPanel{min-width:0;max-width:none}\n  body.mobileUi .searchBox input{min-height:46px;font-size:16px}\n  body.mobileUi .searchClear{min-width:46px}\n  body.mobileUi .searchResults{max-height:min(48dvh,360px)}\n  body.mobileUi .bottom{display:none!important}\n  body.mobileUi .mobileDock{position:absolute;left:10px;right:10px;bottom:calc(env(safe-area-inset-bottom,0px) + 8px);z-index:340;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:8px;background:rgba(8,13,24,.78);border:1px solid rgba(148,163,184,.24);border-radius:20px;box-shadow:0 16px 38px rgba(0,0,0,.36);backdrop-filter:blur(16px);pointer-events:auto}\n  body.mobileUi .mobileDockBtn{height:52px;min-height:0;border-radius:16px;padding:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;background:rgba(15,23,42,.88)}\n  body.mobileUi .mobileDockBtn.active{background:rgba(56,189,248,.28);border-color:rgba(56,189,248,.75)}\n  body.mobileUi #app.navMode .mobileDock{display:none}\n  body.mobileUi .musicWidget{display:none!important;left:10px;right:10px;bottom:calc(var(--mobileDockH) + env(safe-area-inset-bottom,0px) + 18px);min-width:0;width:auto;padding:10px 12px;border-radius:18px;z-index:345}\n  body.mobileUi #app.mediaOpen .musicWidget{display:block!important}\n  body.mobileUi #app.navMode .musicWidget{display:none!important}\n  body.mobileUi #app.navMode.mediaOpen .musicWidget{display:block!important;bottom:calc(env(safe-area-inset-bottom,0px) + 84px)}\n  body.mobileUi .musicButtons{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.musicButtons button{min-width:0;width:100%;min-height:42px}\n  body.mobileUi .navBottomBar{left:10px;right:10px;bottom:calc(env(safe-area-inset-bottom,0px) + 10px);border-radius:18px;padding:8px 10px;gap:10px}\n  body.mobileUi .navExit,body.mobileUi .navInfoToggle,body.mobileUi .navMediaToggle{width:46px;height:46px;border-radius:14px}body.mobileUi .navMetrics{justify-content:flex-start;min-width:0;gap:9px}\n  body.mobileUi .navTopInstruction{left:10px;right:10px;top:10px}.navSpeedBubble{right:10px}.navCompass{left:10px}\n}\n\n\n.mapPickMarker{position:absolute;width:26px;height:26px;margin-left:-13px;margin-top:-13px;border-radius:50%;border:3px solid #fff;background:rgba(239,68,68,.92);box-shadow:0 0 0 6px rgba(239,68,68,.24),0 0 24px rgba(239,68,68,.7);z-index:135;pointer-events:none}\n.mapPickMarker:after{content:"";position:absolute;left:50%;top:50%;width:6px;height:6px;margin-left:-3px;margin-top:-3px;border-radius:50%;background:#fff}\n.mapContextMenu{position:absolute;z-index:420;width:220px;background:rgba(8,13,24,.95);border:1px solid rgba(148,163,184,.34);border-radius:16px;padding:10px;box-shadow:0 18px 42px rgba(0,0,0,.45);pointer-events:auto;color:#e5e7eb;backdrop-filter:blur(12px)}\n.mapContextTitle{font-size:14px;font-weight:850;line-height:1.15}.mapContextMeta{font-size:12px;color:#9ca3af;margin-top:4px;margin-bottom:10px}.mapContextMenu button{width:100%;min-height:36px;border-radius:12px;margin-top:6px}.mapContextRoute{background:rgba(56,189,248,.20);border-color:rgba(56,189,248,.58)}.mapContextCancel{background:rgba(148,163,184,.12)}\n@media(max-width:760px),(pointer:coarse){.mapContextMenu{left:50%!important;top:auto!important;bottom:calc(env(safe-area-inset-bottom,0px) + 82px);transform:translateX(-50%);width:min(320px,calc(100vw - 22px));border-radius:18px;padding:12px}.mapContextMenu button{min-height:44px;font-weight:800}.mapPickMarker{width:30px;height:30px;margin-left:-15px;margin-top:-15px}}\n</style>\n</head>\n<body>\n<div id="app">\n  <div id="mapViewport"><div id="mapWorld"><img id="mapFallback" src="/asset/fh6_full_map_source.jpeg" alt=""><div id="tileLayer"></div><svg id="routeLayer"></svg><div id="markerLayer"></div></div><div id="playerLayer"></div><div class="crosshair"></div></div>\n  <div class="navTopInstruction" id="navTopInstruction"><div class="navArrow" id="navArrow">↑</div><div><div class="navText" id="navInstruction">Select a POI and press Build route</div><div class="navSub" id="navSub">Heading-up navigation preview</div></div></div>\n  <div class="navSpeedBubble" id="navSpeedBubble">0 km/h</div>\n  <div class="navCompass" id="navCompass">N</div>\n  <div class="navTargetName" id="navTargetName">No destination</div>\n  <div class="navBottomBar" id="navBottomBar"><button class="navExit" id="navExitBtn" title="Stop navigation">×</button><div class="navMetrics"><span id="navDistance">—</span><span id="navEta">—</span></div><button class="navInfoToggle" id="navInfoToggleBtn" title="Nearest POI">ⓘ</button><button class="navMediaToggle" id="navMediaToggleBtn" title="Media controls">♫</button></div>\n  <div class="mobileNearestOverlay panel" id="mobileNearestOverlay"><div class="panelTitleRow"><div><div class="title">Nearest POI</div><div class="sub">Closest markers from your current position</div></div><button class="mobileSheetClose" id="mobileNearestCloseBtn" title="Hide panel">×</button></div><div class="nearestList" id="mobileNearestList" data-nearest-list><div class="hint">Waiting for telemetry…</div></div></div>\n  <div class="routeLine" id="routeLine"></div>\n  <div class="navDestination" id="navDestination"></div>\n  <div class="musicWidget" id="musicWidget"><div class="musicHeader"><div class="musicTitle">Spotify / System Media</div><button class="mediaCollapseBtn" id="mediaCollapseBtn" title="Collapse media controls">⌄</button></div><div class="musicButtons"><button id="mediaPrevBtn" title="Previous track">⏮</button><button id="mediaPlayBtn" title="Play/Pause">⏯</button><button id="mediaNextBtn" title="Next track">⏭</button><button id="mediaVolDownBtn" title="Volume down">−</button><button id="mediaVolUpBtn" title="Volume up">+</button></div><div class="musicStatus" id="musicStatus">Windows media keys</div></div>\n\n\n  <div class="mobileDock" id="mobileDock">\n    <button class="mobileDockBtn" data-panel="info" title="Information"><span class="dockIcon">ⓘ</span><span class="dockLabel">Info</span></button>\n    <button class="mobileDockBtn" data-panel="search" title="Search"><span class="dockIcon">⌕</span><span class="dockLabel">Search</span></button>\n    <button class="mobileDockBtn" data-panel="settings" title="Settings"><span class="dockIcon">⚙</span><span class="dockLabel">Settings</span></button>\n    <button class="mobileDockBtn" data-panel="media" title="Media"><span class="dockIcon">♫</span><span class="dockLabel">Media</span></button>\n  </div>\n\n  <div class="topbar">\n    <div class="panel status mobileSheet" id="statusPanel" data-mobile-panel="info">\n      <div style="display:flex;justify-content:space-between;gap:10px;align-items:center">\n        <div><div class="title">FH6 Live Map v0.9.15</div><div class="sub">Forza Horizon 6 Data Out → GamerGuides Japan map</div></div><button class="mobileSheetClose" data-close-mobile title="Hide panel">×</button>\n        <div class="pill"><span id="statusDot" class="dot"></span><span id="statusText">WAITING</span></div>\n      </div>\n      <div class="row">\n        <div class="metric"><div class="label">Speed</div><div class="value"><span id="speed">0</span> km/h</div></div>\n        <div class="metric"><div class="label">Gear</div><div class="value" id="gear">-</div></div>\n        <div class="metric"><div class="label">Heading</div><div class="value"><span id="heading">0</span>°</div></div>\n        <div class="metric"><div class="label">Map</div><div class="value"><span id="mapxy">—</span></div></div>\n      </div>\n      <div class="mobileInfoNearest"><div class="title">Nearest POI</div><div class="nearestList" id="mobileInfoNearestList" data-nearest-list><div class="hint">Waiting for telemetry…</div></div></div>\n    </div>\n    <div class="panel searchPanel mobileSheet" id="searchPanel" data-mobile-panel="search">\n      <div class="panelTitleRow"><div><div class="title">Search destination</div><div class="sub">Find POI by name or category</div></div><button class="mobileSheetClose" data-close-mobile title="Hide panel">×</button></div>\n      <div class="searchBox"><input id="searchInput" type="search" autocomplete="off" placeholder="Start typing: race, board, house…"><button class="searchClear" id="searchClearBtn" title="Clear search">×</button></div>\n      <div class="searchResults" id="searchResults"></div>\n    </div>\n    <div class="panel controls mobileSheet" id="settingsPanel" data-mobile-panel="settings">\n      <div class="panelTitleRow"><div><div class="title">Settings</div><div class="sub">Follow, navigator, map layer and POI filters</div></div><button class="mobileSheetClose" data-close-mobile title="Hide panel">×</button></div>\n      <button id="followBtn" class="active" title="Go to current car location and keep following">Locate / Follow</button><button id="navBtn" title="Open automotive navigator view">Navigator</button><button id="northUpBtn" title="Keep north at the top of the map">North up</button><button id="markersBtn" class="active">Markers</button>\n      \n      <select id="layerSelect"><option value="760">Summer</option><option value="757">Autumn</option><option value="758">Winter</option><option value="759">Spring</option><option value="756">All Seasons</option></select>\n      <select id="categorySelect"><option value="">All POI</option></select>\n    </div>\n  </div>\n  <div class="bottom">\n    <div class="panel nearest"><div class="title">Nearest POI</div><div class="nearestList" id="nearestList" data-nearest-list><div class="hint">Waiting for telemetry…</div></div></div>\n    <div class="panel hint pcLinkPanel" id="pcLinkPanel"><div class="ipLine">PC URL to open on phone: <span id="phoneUrl">detecting local IP…</span><button class="copyIpBtn" id="copyIpBtn">Copy</button></div><div class="qrWrap"><img id="phoneQr" alt="QR code for phone URL"></div><small>Scan this QR from your phone, or open the URL in the phone browser while both devices are on the same local network.</small><br>Click POI to inspect. Drag to pan. Pinch/wheel to zoom. Press Locate / Follow to re-center.</div>\n  </div>\n</div>\n<script>\n\n\nconst MAP_WIDTH=20000,MAP_HEIGHT=20000,TILE_SIZE=256,MIN_ZOOM=12,MAX_ZOOM=18;\nconst viewport=document.getElementById(\'mapViewport\'),mapWorld=document.getElementById(\'mapWorld\'),tileLayer=document.getElementById(\'tileLayer\'),routeLayer=document.getElementById(\'routeLayer\'),markerLayer=document.getElementById(\'markerLayer\'),playerLayer=document.getElementById(\'playerLayer\');\nlet telemetry=null,markers=[],selectedPoi=null,routeTarget=null,currentRoute=null,navMode=false,northUp=(localStorage.getItem(\'fh6_north_up\')===\'1\'),follow=true,showMarkers=true,zoom=Math.max(MIN_ZOOM,Math.min(MAX_ZOOM,Math.round(Number(localStorage.getItem(\'fh6_zoom\')||16)))),layerId=localStorage.getItem(\'fh6_layer\')||"760",categoryFilter=localStorage.getItem(\'fh6_category\')||"",panX=0,panY=0,dragging=false,dragStart=null,playerMapX=10387,playerMapY=9846,targetMapX=null,targetMapY=null,displayMapX=null,displayMapY=null,targetHeadingDeg=0,displayHeadingDeg=0,lastTelemetryMapX=null,lastTelemetryMapY=null,lastMovementHeadingDeg=null,lastMovementHeadingAt=0,lastTileKey="",activePointers=new Map(),pinchStart=null,lastPinchZoom=zoom,lastMarkerRenderAt=0,lastNearestRenderAt=0,lastRouteRequestAt=0,routeRequestInFlight=false,lastRouteAnchorX=null,lastRouteAnchorY=null,lastRouteOffRoutePx=0,offRouteSince=0,navTouchLookUntil=0;\nlet markerDomByKey=new Map(),playerEl=null,routeEls=null,lastRouteSize=\'\',lastRoutePoints=\'\',interactionRenderRaf=0,arriveSince=0,mapContextTarget=null,mapContextMenuEl=null,mapPickEl=null,lastTapAt=0,lastTapX=0,lastTapY=0,lastManualZoomAt=0,lastAutoZoomCheckAt=0,autoZoomInCandidate=null,autoZoomInCandidateAt=0,tapStart=null,tapWasMulti=false;\nconst NAV_TOUCH_LOOK_MS=0,REROUTE_MIN_INTERVAL_MS=14000,REROUTE_STICKY_OFF_PX=170,REROUTE_STICKY_MS=22000,REROUTE_HARD_OFF_PX=360,REROUTE_HARD_MS=9000,REROUTE_HUGE_OFF_PX=650,REROUTE_HUGE_MS=3500,REROUTE_REFRESH_MOVE_PX=760,REROUTE_LONG_ROUTE_LOCK_MS=32000;\nconst MAP_PX_PER_METER=0.655,NAV_ARRIVE_METERS=30,NAV_ARRIVE_STOPPED_METERS=62,NAV_ARRIVE_PX=NAV_ARRIVE_METERS*MAP_PX_PER_METER,NAV_ARRIVE_STOPPED_PX=NAV_ARRIVE_STOPPED_METERS*MAP_PX_PER_METER,NAV_ARRIVE_STOPPED_MAX_KMH=8,NAV_ARRIVE_HOLD_MS=1100;\nconst FALLBACK_IMG_W=1638,FALLBACK_IMG_H=2048,FALLBACK_SX=6.58487266,FALLBACK_SY=6.60554791,FALLBACK_OX=4594.21749925,FALLBACK_OY=3225.79270983;\nconst NAV_AUTO_ZOOM_SECONDS=4.0,NAV_AUTO_ZOOM_MIN_METERS=170,NAV_AUTO_ZOOM_HOLD_IN_MS=4200,NAV_AUTO_ZOOM_CHECK_MS=450,NAV_AUTO_ZOOM_MANUAL_COOLDOWN_MS=5500,NAV_AUTO_ZOOM_MIN_ZOOM=15,NAV_AUTO_ZOOM_TOP_MARGIN=128,NAV_AUTO_ZOOM_SIDE_MARGIN=42,NAV_AUTO_ZOOM_BOTTOM_MARGIN=96;\n\n// v0.9.15 compact lower-left nearest POI\nlet mobileActivePanel=null;\nfunction isMobileLayout(){return window.matchMedia(\'(max-width:760px), (pointer:coarse)\').matches}\nfunction setMobileUiClass(){document.body.classList.toggle(\'mobileUi\',isMobileLayout())}\nfunction setDockActive(panel){document.querySelectorAll(\'.mobileDockBtn\').forEach(btn=>btn.classList.toggle(\'active\',btn.dataset.panel===panel));}\nfunction closeMobilePanels(){\n  mobileActivePanel=null;\n  document.querySelectorAll(\'.mobileSheet\').forEach(el=>el.classList.remove(\'mobileOpen\'));\n  document.getElementById(\'app\').classList.remove(\'mediaOpen\');\n  document.getElementById(\'app\').classList.remove(\'nearestOpen\');\n  setDockActive(null);\n}\nfunction openMobilePanel(panel){\n  setMobileUiClass();\n  const app=document.getElementById(\'app\');\n  const same=mobileActivePanel===panel || (panel===\'media\'&&app.classList.contains(\'mediaOpen\'));\n  closeMobilePanels();\n  if(same)return;\n  mobileActivePanel=panel;\n  setDockActive(panel);\n  if(panel===\'media\'){\n    app.classList.remove(\'mediaCollapsed\');\n    app.classList.add(\'mediaOpen\');\n    return;\n  }\n  const el=document.querySelector(\'.mobileSheet[data-mobile-panel="\'+panel+\'"]\');\n  if(el)el.classList.add(\'mobileOpen\');\n  if(panel===\'info\'){app.classList.add(\'nearestOpen\');updateNearest();}\n  if(panel===\'search\')setTimeout(()=>document.getElementById(\'searchInput\')?.focus(),70);\n}\n\nfunction isNavTouchLookActive(){return false}\nfunction keepNavigatorFollow(){if(navMode)follow=true;const btn=document.getElementById(\'followBtn\');if(btn)btn.classList.add(\'active\')}\nfunction suspendNavFollow(ms=NAV_TOUCH_LOOK_MS){if(navMode&&follow){navTouchLookUntil=0;keepNavigatorFollow()}}\nfunction centerIfFollowing(){if(follow)centerOnPlayer()}\nfunction setFollowEnabled(value){follow=!!value;const btn=document.getElementById(\'followBtn\');if(btn)btn.classList.toggle(\'active\',follow);if(follow){navTouchLookUntil=0;centerOnPlayer();renderTiles(true);renderPlayer();renderMarkers();renderRouteLine();updateNearest();}}\nfunction toggleNearestOverlay(){\n  const app=document.getElementById(\'app\');\n  const next=!app.classList.contains(\'nearestOpen\');\n  closeMobilePanels();\n  app.classList.toggle(\'nearestOpen\',next);\n  if(next)updateNearest();\n}\nfunction clamp(n,a,b){return Math.max(a,Math.min(b,n))}function scale(){return Math.pow(2,zoom-MAX_ZOOM)}function mapToScreen(mx,my){const s=scale();return{x:mx*s-panX,y:my*s-panY}}function rotatePointAround(px,py,cx,cy,deg){if(!deg)return{x:px,y:py};const rad=deg*Math.PI/180,cos=Math.cos(rad),sin=Math.sin(rad),dx=px-cx,dy=py-cy;return{x:cx+dx*cos-dy*sin,y:cy+dx*sin+dy*cos}}function screenToMap(sx,sy){const a=navAnchor(),deg=navRotationDeg();const u=rotatePointAround(sx,sy,a.x,a.y,-deg);const s=scale();return{x:(u.x+panX)/s,y:(u.y+panY)/s}}function dist(a,b){const dx=a.map_x-b.map_x,dy=a.map_y-b.map_y;return Math.sqrt(dx*dx+dy*dy)}function metersFromMapPx(px){return px/MAP_PX_PER_METER}function mapPxFromMeters(m){return m*MAP_PX_PER_METER}\nfunction initControls(){\n  document.getElementById(\'layerSelect\').value=layerId;\n  document.getElementById(\'categorySelect\').value=categoryFilter;\n  const northBtn=document.getElementById(\'northUpBtn\');\n  if(northBtn)northBtn.classList.toggle(\'active\',northUp);\n  document.getElementById(\'followBtn\').classList.add(\'active\');\n  follow=true;\n  document.getElementById(\'followBtn\').onclick=()=>setFollowEnabled(!follow);\n  document.getElementById(\'navBtn\').onclick=()=>enterNavMode();\n  if(northBtn)northBtn.onclick=()=>{setNorthUp(!northUp);lastTileKey=\'\';renderAll(true)};\n  document.getElementById(\'navExitBtn\').onclick=()=>exitNavMode();\n  document.getElementById(\'mediaPrevBtn\').onclick=()=>sendMediaKey(\'prev\');\n  document.getElementById(\'mediaPlayBtn\').onclick=()=>sendMediaKey(\'playpause\');\n  document.getElementById(\'mediaNextBtn\').onclick=()=>sendMediaKey(\'next\');\n  document.getElementById(\'mediaVolDownBtn\').onclick=()=>sendMediaKey(\'voldown\');\n  document.getElementById(\'mediaVolUpBtn\').onclick=()=>sendMediaKey(\'volup\');\n  document.getElementById(\'mediaCollapseBtn\')?.addEventListener(\'click\',()=>{const app=document.getElementById(\'app\');app.classList.remove(\'mediaOpen\');app.classList.add(\'mediaCollapsed\');mobileActivePanel=null;setDockActive(null);});\n  document.getElementById(\'navMediaToggleBtn\')?.addEventListener(\'click\',()=>openMobilePanel(\'media\'));\n  document.getElementById(\'navInfoToggleBtn\')?.addEventListener(\'click\',()=>toggleNearestOverlay());\n  document.getElementById(\'mobileNearestCloseBtn\')?.addEventListener(\'click\',()=>document.getElementById(\'app\').classList.remove(\'nearestOpen\'));\n  document.querySelectorAll(\'.mobileDockBtn\').forEach(btn=>btn.addEventListener(\'click\',()=>openMobilePanel(btn.dataset.panel)));\n  document.querySelectorAll(\'[data-close-mobile]\').forEach(btn=>btn.addEventListener(\'click\',()=>closeMobilePanels()));\n  document.getElementById(\'markersBtn\').onclick=()=>{showMarkers=!showMarkers;document.getElementById(\'markersBtn\').classList.toggle(\'active\',showMarkers);renderMarkers()};\n  document.getElementById(\'layerSelect\').onchange=e=>{layerId=e.target.value;localStorage.setItem(\'fh6_layer\',layerId);tileLayer.innerHTML="";lastTileKey="";renderTiles(true)};\n  document.getElementById(\'categorySelect\').onchange=e=>{categoryFilter=e.target.value;localStorage.setItem(\'fh6_category\',categoryFilter);renderMarkers();updateNearest();runSearch(document.getElementById(\'searchInput\')?.value||\'\')};\n  initSearch();\n}\nfunction setNorthUp(value){northUp=!!value;localStorage.setItem(\'fh6_north_up\',northUp?\'1\':\'0\');const northBtn=document.getElementById(\'northUpBtn\');if(northBtn)northBtn.classList.toggle(\'active\',northUp);applyMapRotation()}\nfunction setZoom(n,cx=null,cy=null,opts={}){const isAuto=!!(opts&&opts.auto);n=clamp(Math.round(n),MIN_ZOOM,MAX_ZOOM);if(!isAuto)lastManualZoomAt=Date.now();if(n===zoom)return;let anchor;if(cx!==null&&cy!==null){const r0=viewport.getBoundingClientRect();anchor=screenToMap(cx-r0.left,cy-r0.top)}else anchor={x:playerMapX,y:playerMapY};zoom=n;if(!isAuto)localStorage.setItem(\'fh6_zoom\',String(zoom));const r=viewport.getBoundingClientRect(),s=scale();if(cx!==null&&cy!==null){panX=anchor.x*s-(cx-r.left);panY=anchor.y*s-(cy-r.top)}else centerOnPlayer();clampPan();tileLayer.innerHTML="";lastTileKey="";applyMapRotation();renderAll(true)}\nfunction centerOnPlayer(){const a=navAnchor(),s=scale();panX=playerMapX*s-a.x;panY=playerMapY*s-a.y;clampPan();applyMapRotation()}\nfunction clampPan(){const r=viewport.getBoundingClientRect(),s=scale(),ww=MAP_WIDTH*s,hh=MAP_HEIGHT*s;if(ww<=r.width)panX=(ww-r.width)/2;else panX=clamp(panX,0,ww-r.width);if(hh<=r.height)panY=(hh-r.height)/2;else panY=clamp(panY,0,hh-r.height)}\nfunction navAnchor(){const r=viewport.getBoundingClientRect();return{x:r.width/2,y:navMode?r.height*0.68:r.height/2}}\nfunction navRotationDeg(){return (navMode&&follow&&routeTarget&&!northUp)?-(displayHeadingDeg||0):0}\nfunction normalizeAngleDeg(deg){return ((Number(deg)||0)%360+360)%360}\nfunction mapVectorToHeadingDeg(dx,dy){return normalizeAngleDeg(Math.atan2(dx,-dy)*180/Math.PI)}\nfunction updateHeadingFromMotion(mx,my,speedKmh,serverHeadingDeg){let heading=Number(serverHeadingDeg)||0;const now=performance.now();if(lastTelemetryMapX!==null&&lastTelemetryMapY!==null){const dx=mx-lastTelemetryMapX,dy=my-lastTelemetryMapY,step=Math.hypot(dx,dy);if(step>0.45&&(speedKmh||0)>2){heading=mapVectorToHeadingDeg(dx,dy);lastMovementHeadingDeg=heading;lastMovementHeadingAt=now}else if(lastMovementHeadingDeg!==null&&(now-lastMovementHeadingAt)<3500){heading=lastMovementHeadingDeg}}lastTelemetryMapX=mx;lastTelemetryMapY=my;return normalizeAngleDeg(heading)}\nfunction applyMapRotation(){const a=navAnchor(),deg=navRotationDeg();if(mapWorld){mapWorld.style.transformOrigin=`${a.x}px ${a.y}px`;mapWorld.style.transform=`rotate(${deg}deg)`}}\n\nfunction renderMapFallback(){const img=document.getElementById(\'mapFallback\');if(!img)return;const s=scale();img.style.left=`${(FALLBACK_OX*s-panX).toFixed(1)}px`;img.style.top=`${(FALLBACK_OY*s-panY).toFixed(1)}px`;img.style.width=`${(FALLBACK_IMG_W*FALLBACK_SX*s).toFixed(1)}px`;img.style.height=`${(FALLBACK_IMG_H*FALLBACK_SY*s).toFixed(1)}px`}\nfunction renderTiles(force=false){renderMapFallback();const r=viewport.getBoundingClientRect(),s=scale(),margin=navMode?5:1,x0=Math.floor(panX/TILE_SIZE)-margin,y0=Math.floor(panY/TILE_SIZE)-margin,x1=Math.ceil((panX+r.width)/TILE_SIZE)+margin,y1=Math.ceil((panY+r.height)/TILE_SIZE)+margin,maxTx=Math.ceil((MAP_WIDTH*s)/TILE_SIZE)-1,maxTy=Math.ceil((MAP_HEIGHT*s)/TILE_SIZE)-1,key=[zoom,layerId,x0,y0,x1,y1,Math.round(panX),Math.round(panY)].join(\':\');if(!force&&key===lastTileKey){applyMapRotation();return}lastTileKey=key;const need=new Set();for(let ty=y0;ty<=y1;ty++)for(let tx=x0;tx<=x1;tx++){if(tx<0||ty<0||tx>maxTx||ty>maxTy)continue;const id=`${zoom}-${tx}-${ty}`;need.add(id);let img=document.getElementById(\'tile-\'+id);if(!img){img=document.createElement(\'img\');img.className=\'tile\';img.id=\'tile-\'+id;img.decoding=\'async\';img.loading=\'eager\';img.src=`/tile/${layerId}/${zoom}/${tx}/${ty}.png`;img.onerror=()=>{img.style.opacity=0};tileLayer.appendChild(img)}img.style.left=`${tx*TILE_SIZE-panX}px`;img.style.top=`${ty*TILE_SIZE-panY}px`}for(const img of Array.from(tileLayer.children))if(!need.has(img.id.replace(\'tile-\',\'\')))img.remove();applyMapRotation()}\nfunction renderPlayer(){if(playerMapX===null||playerMapY===null){if(playerEl)playerEl.style.display=\'none\';return}if(!playerEl){playerEl=document.createElement(\'div\');playerEl.className=\'player\';playerLayer.appendChild(playerEl)}const p=mapToScreen(playerMapX,playerMapY);playerEl.style.display=\'block\';playerEl.style.left=`${p.x}px`;playerEl.style.top=`${p.y}px`}\nfunction populateCategories(){const cats=[...new Set(markers.map(m=>m.category).filter(Boolean))].sort(),sel=document.getElementById(\'categorySelect\');for(const c of cats){let o=document.createElement(\'option\');o.value=c;o.textContent=c;sel.appendChild(o)}if(categoryFilter)sel.value=categoryFilter}\nfunction markerKey(m){return String(m.markerId||m.id||((m.title||\'poi\')+\'@\'+Math.round(m.map_x)+\',\'+Math.round(m.map_y)))}\nfunction renderMarkers(){if(!showMarkers){for(const el of markerDomByKey.values())el.remove();markerDomByKey.clear();const popup=document.getElementById(\'poiPopup\');if(popup)popup.remove();return}if(!markers||!markers.length){const popup=document.getElementById(\'poiPopup\');if(popup)popup.remove();return}const r=viewport.getBoundingClientRect(),pad=navMode?Math.max(r.width,r.height):80;let pool=markers;if(categoryFilter)pool=pool.filter(m=>m.category===categoryFilter);const need=new Set();let count=0;for(const m of pool){const p=mapToScreen(m.map_x,m.map_y);if(p.x<-pad||p.y<-pad||p.x>r.width+pad||p.y>r.height+pad)continue;const key=markerKey(m);need.add(key);let d=markerDomByKey.get(key);if(!d){d=document.createElement(\'div\');d.onpointerdown=(ev)=>{ev.stopPropagation();selectPoi(d._fh6Marker,true)};markerDomByKey.set(key,d);markerLayer.appendChild(d)}d._fh6Marker=m;const isSpeed=/speed/i.test(m.category||"");const selected=selectedPoi&&String(selectedPoi.markerId||selectedPoi.id)===String(m.markerId||m.id);d.className=\'marker\'+(isSpeed?\' speed\':\'\')+(selected?\' selected\':\'\');d.style.left=`${p.x}px`;d.style.top=`${p.y}px`;d.style.background=m.color||\'#7dd3fc\';d.title=`${m.title} | ${m.category}`;if(++count>600)break}for(const [key,el] of Array.from(markerDomByKey.entries())){if(!need.has(key)){el.remove();markerDomByKey.delete(key)}}renderPoiPopup();applyMapRotation()}\nfunction selectPoi(m,keepMap=false){selectedPoi=m;if(!keepMap&&!navMode){follow=false;document.getElementById(\'followBtn\').classList.remove(\'active\');const r=viewport.getBoundingClientRect(),s=scale();panX=m.map_x*s-r.width/2;panY=m.map_y*s-r.height/2;clampPan()}else if(navMode){keepNavigatorFollow()}renderMarkers();updateNearest()}\nfunction clearPoi(){selectedPoi=null;closeMapContextMenu(true);renderMarkers();updateNearest()}\nfunction renderPoiPopup(){const old=document.getElementById(\'poiPopup\');if(old)old.remove();if(!selectedPoi)return;const p=mapToScreen(selectedPoi.map_x,selectedPoi.map_y);const r=viewport.getBoundingClientRect();const popup=document.createElement(\'div\');popup.id=\'poiPopup\';popup.className=\'poiPopup\';let distanceText=\'—\';if(telemetry&&telemetry.map_x!==null){distanceText=markerDistanceText(selectedPoi)||\'—\'}const desc=selectedPoi.description||selectedPoi.desc||\'Description slot is ready. Later we can load richer GamerGuides popup text here.\';popup.innerHTML=`<button class="poiPopupClose" title="Close">×</button><div class="poiPopupTitle">${esc(selectedPoi.title||\'Unknown POI\')}</div><div class="poiPopupMeta">${esc(selectedPoi.category||\'Unknown category\')}${selectedPoi.parent_category?\' · \'+esc(selectedPoi.parent_category):\'\'}</div><div class="poiPopupDesc">${esc(desc)}</div><div class="poiPopupRow"><span>Map coordinates</span><b>${Math.round(selectedPoi.map_x)}, ${Math.round(selectedPoi.map_y)}</b></div><div class="poiPopupRow"><span>Distance from car</span><b>${distanceText}</b></div><div class="poiPopupActions"><button class="routeBtn" id="buildRouteBtn">Build route</button></div>`;popup.querySelector(\'.poiPopupClose\').onclick=(ev)=>{ev.stopPropagation();clearPoi()};const buildBtn=popup.querySelector(\'#buildRouteBtn\');buildBtn.onpointerdown=(ev)=>{ev.preventDefault();ev.stopPropagation();startRouteToPoi(selectedPoi)};markerLayer.appendChild(popup);let left=p.x+18,top=p.y-24;if(left+330>r.width)left=p.x-348;if(top+210>r.height)top=r.height-226;if(top<10)top=10;if(left<10)left=10;popup.style.left=`${left}px`;popup.style.top=`${top}px`}\nfunction makeMapPointTarget(mx,my){return{isCustom:true,title:\'Selected point\',category:\'Custom point\',map_x:mx,map_y:my}}\nfunction closeMapContextMenu(clearTarget=true){if(mapContextMenuEl){mapContextMenuEl.remove();mapContextMenuEl=null}if(clearTarget){mapContextTarget=null;if(mapPickEl){mapPickEl.remove();mapPickEl=null}}}\nfunction renderMapPickMarker(){if(!mapContextTarget){if(mapPickEl)mapPickEl.style.display=\'none\';return}if(!mapPickEl){mapPickEl=document.createElement(\'div\');mapPickEl.className=\'mapPickMarker\';markerLayer.appendChild(mapPickEl)}const p=mapToScreen(mapContextTarget.map_x,mapContextTarget.map_y);mapPickEl.style.display=\'block\';mapPickEl.style.left=`${p.x}px`;mapPickEl.style.top=`${p.y}px`}\nfunction showMapContextMenu(mx,my,clientX,clientY,source=\'map\'){closeMapContextMenu(true);clearPoi();mapContextTarget=makeMapPointTarget(mx,my);renderMapPickMarker();const r=viewport.getBoundingClientRect();const menu=document.createElement(\'div\');menu.className=\'mapContextMenu\';const meters=telemetry&&telemetry.map_x!==null?Math.round(metersFromMapPx(dist({map_x:telemetry.map_x,map_y:telemetry.map_y},mapContextTarget))):null;menu.innerHTML=`<div class="mapContextTitle">Selected point</div><div class="mapContextMeta">${Math.round(mx)}, ${Math.round(my)}${meters!==null?\' · \'+(meters>=1000?(meters/1000).toFixed(1)+\' km\':meters+\' m\'):\'\'}</div><button class="mapContextRoute">Build route</button><button class="mapContextCancel">Cancel</button>`;menu.querySelector(\'.mapContextRoute\').onpointerdown=(ev)=>{ev.preventDefault();ev.stopPropagation();const target=mapContextTarget;closeMapContextMenu(true);startRouteToPoi(target)};menu.querySelector(\'.mapContextCancel\').onpointerdown=(ev)=>{ev.preventDefault();ev.stopPropagation();closeMapContextMenu(true)};viewport.appendChild(menu);mapContextMenuEl=menu;let left=clientX-r.left,top=clientY-r.top;if(left+220>r.width)left=r.width-230;if(top+132>r.height)top=r.height-142;if(left<10)left=10;if(top<10)top=10;menu.style.left=left+\'px\';menu.style.top=top+\'px\'}\nfunction showContextMenuForScreen(clientX,clientY,useCrosshair=false){const r=viewport.getBoundingClientRect();const sx=useCrosshair?r.width/2:clientX-r.left,sy=useCrosshair?r.height/2:clientY-r.top;const m=screenToMap(sx,sy);const menuX=useCrosshair?r.left+r.width/2:clientX,menuY=useCrosshair?r.top+r.height/2:clientY;showMapContextMenu(clamp(m.x,0,MAP_WIDTH),clamp(m.y,0,MAP_HEIGHT),menuX,menuY,useCrosshair?\'crosshair\':\'map\')}\nfunction maybeHandleDoubleTap(e){if(!isMobileLayout()&&(navigator.maxTouchPoints||0)<2)return false;const now=Date.now(),dx=e.clientX-lastTapX,dy=e.clientY-lastTapY;const hit=(now-lastTapAt)<460&&Math.hypot(dx,dy)<44;if(hit){lastTapAt=0;showContextMenuForScreen(e.clientX,e.clientY,true);return true}lastTapAt=now;lastTapX=e.clientX;lastTapY=e.clientY;return false}\n\nasync function startRouteToPoi(poi){if(!poi)return;closeMapContextMenu(true);routeTarget=poi;selectedPoi=null;currentRoute=null;lastRouteAnchorX=null;lastRouteAnchorY=null;lastRouteOffRoutePx=0;offRouteSince=0;autoZoomInCandidate=null;autoZoomInCandidateAt=0;await requestRoute(poi,true);enterNavMode(true)}\nasync function requestRoute(target,force=false){if(!target)return null;if(routeRequestInFlight&&!force)return currentRoute;const now=Date.now();if(!force&&now-lastRouteRequestAt<2200)return currentRoute;routeRequestInFlight=true;lastRouteRequestAt=now;try{const qs=new URLSearchParams({target_x:String(target.map_x),target_y:String(target.map_y),target_title:String(target.title||\'Destination\')});if(!target.isCustom&&(target.markerId||target.id))qs.set(\'marker_id\',String(target.markerId||target.id));const r=await fetch(\'/api/route?\'+qs.toString(),{cache:\'no-store\'});const data=await r.json();if(data){const incomingPts=Array.isArray(data.polyline)?data.polyline.map(p=>({map_x:Number(p.map_x),map_y:Number(p.map_y)})).filter(p=>Number.isFinite(p.map_x)&&Number.isFinite(p.map_y)):[];const incomingDist=incomingPts.length>=2?routeDistancePx(incomingPts):Infinity;const currentRemaining=routePointsForRender();const currentRemainingDist=currentRemaining.length>=2?routeDistancePx(currentRemaining):Infinity;const off=telemetry&&telemetry.map_x!==null?distanceToCurrentRoute(Number(telemetry.map_x),Number(telemetry.map_y)):Infinity;const holdingOriginalRoute=!!offRouteSince&&((now-offRouteSince)<REROUTE_LONG_ROUTE_LOCK_MS);const suspiciousReroute=!force&&currentRoute&&currentRoute.mode===\'graph\'&&data.mode===\'graph\'&&Number.isFinite(incomingDist)&&Number.isFinite(currentRemainingDist)&&incomingDist>Math.max(currentRemainingDist*1.25,currentRemainingDist+350)&&off<520&&holdingOriginalRoute;if(suspiciousReroute){console.warn(\'FH6 route ignored sticky reroute\', {incomingDist,currentRemainingDist,off,heldForMs:now-offRouteSince,data});return currentRoute}currentRoute=data;currentRoute.client_requested_at=Date.now();offRouteSince=0;console.log(\'FH6 route\',data.mode,data.message||\'\',data.routing||{});if(telemetry&&telemetry.map_x!==null){lastRouteAnchorX=Number(telemetry.map_x);lastRouteAnchorY=Number(telemetry.map_y)}}else{currentRoute=null}return currentRoute}catch(e){console.warn(\'route request failed\',e);return currentRoute}finally{routeRequestInFlight=false}}\nfunction pointSegmentDistance(px,py,ax,ay,bx,by){const vx=bx-ax,vy=by-ay,wx=px-ax,wy=py-ay;const c1=vx*wx+vy*wy;const c2=vx*vx+vy*vy;if(c2<=0)return{d:Math.hypot(px-ax,py-ay),x:ax,y:ay,t:0};let t=c1/c2;t=clamp(t,0,1);const x=ax+vx*t,y=ay+vy*t;return{d:Math.hypot(px-x,py-y),x,y,t}}\nfunction normalizedRoutePolyline(){if(!currentRoute||!Array.isArray(currentRoute.polyline))return[];return currentRoute.polyline.map(p=>({map_x:Number(p.map_x),map_y:Number(p.map_y)})).filter(p=>Number.isFinite(p.map_x)&&Number.isFinite(p.map_y))}\nfunction routeDistancePx(pts){let total=0;if(!pts||pts.length<2)return 0;for(let i=1;i<pts.length;i++)total+=Math.hypot(pts[i].map_x-pts[i-1].map_x,pts[i].map_y-pts[i-1].map_y);return total}\nfunction trimRoutePolyline(raw,px,py){if(!raw||raw.length<2)return[];let best={d:Infinity,i:0,x:raw[0].map_x,y:raw[0].map_y,t:0};for(let i=0;i<raw.length-1;i++){const a=raw[i],b=raw[i+1];const hit=pointSegmentDistance(px,py,a.map_x,a.map_y,b.map_x,b.map_y);if(hit.d<best.d)best={...hit,i}}lastRouteOffRoutePx=best.d;const remaining=[];if(best.d<160){remaining.push({map_x:best.x,map_y:best.y});const startIdx=best.t>0.72?best.i+2:best.i+1;for(let j=startIdx;j<raw.length;j++)remaining.push(raw[j])}else{for(let j=1;j<raw.length;j++)remaining.push(raw[j])}if(remaining.length&&Math.hypot(remaining[0].map_x-px,remaining[0].map_y-py)<3)remaining.shift();return remaining}\nfunction distanceToCurrentRoute(px,py){const raw=normalizedRoutePolyline();if(raw.length<2)return Infinity;let best=Infinity;for(let i=0;i<raw.length-1;i++){const a=raw[i],b=raw[i+1];const hit=pointSegmentDistance(px,py,a.map_x,a.map_y,b.map_x,b.map_y);if(hit.d<best)best=hit.d}return best}\nfunction routePointAtDistance(pts,wantPx){if(!pts||pts.length<2)return pts&&pts.length?pts[pts.length-1]:null;let left=wantPx;for(let i=1;i<pts.length;i++){const a=pts[i-1],b=pts[i],seg=Math.hypot(b.map_x-a.map_x,b.map_y-a.map_y);if(seg<=0)continue;if(left<=seg){const t=left/seg;return{map_x:a.map_x+(b.map_x-a.map_x)*t,map_y:a.map_y+(b.map_y-a.map_y)*t}}left-=seg}return pts[pts.length-1]}\nfunction desiredNavZoomForSpeed(){if(!navMode||!follow||!routeTarget||!telemetry||telemetry.map_x===null)return zoom;const pts=routePointsForRender();if(!pts||pts.length<2)return zoom;const speed=Number(telemetry.speed_kmh)||0;const lookMeters=Math.max(NAV_AUTO_ZOOM_MIN_METERS,(speed/3.6)*NAV_AUTO_ZOOM_SECONDS);const lookPx=mapPxFromMeters(lookMeters);const look=routePointAtDistance(pts,lookPx);if(!look)return zoom;const r=viewport.getBoundingClientRect(),a=navAnchor(),deg=navRotationDeg();function panFor(z){const s=Math.pow(2,z-MAX_ZOOM);let px=playerMapX*s-a.x,py=playerMapY*s-a.y;const ww=MAP_WIDTH*s,hh=MAP_HEIGHT*s;if(ww<=r.width)px=(ww-r.width)/2;else px=clamp(px,0,ww-r.width);if(hh<=r.height)py=(hh-r.height)/2;else py=clamp(py,0,hh-r.height);return{px,py,s}}for(let z=MAX_ZOOM;z>=NAV_AUTO_ZOOM_MIN_ZOOM;z--){const pp=panFor(z);const raw={x:look.map_x*pp.s-pp.px,y:look.map_y*pp.s-pp.py};const screen=rotatePointAround(raw.x,raw.y,a.x,a.y,deg);if(screen.x>=NAV_AUTO_ZOOM_SIDE_MARGIN&&screen.x<=r.width-NAV_AUTO_ZOOM_SIDE_MARGIN&&screen.y>=NAV_AUTO_ZOOM_TOP_MARGIN&&screen.y<=r.height-NAV_AUTO_ZOOM_BOTTOM_MARGIN)return z}return NAV_AUTO_ZOOM_MIN_ZOOM}\nfunction maybeAutoZoomNavigation(){if(!navMode||!follow||!routeTarget||!telemetry||telemetry.map_x===null)return;const now=Date.now();if(now-lastManualZoomAt<NAV_AUTO_ZOOM_MANUAL_COOLDOWN_MS)return;if(now-lastAutoZoomCheckAt<NAV_AUTO_ZOOM_CHECK_MS)return;lastAutoZoomCheckAt=now;const desired=desiredNavZoomForSpeed();if(desired<zoom){autoZoomInCandidate=null;autoZoomInCandidateAt=0;setZoom(desired,null,null,{auto:true});return}if(desired>zoom){if(autoZoomInCandidate!==desired){autoZoomInCandidate=desired;autoZoomInCandidateAt=now;return}if(now-autoZoomInCandidateAt>=NAV_AUTO_ZOOM_HOLD_IN_MS){autoZoomInCandidate=null;autoZoomInCandidateAt=0;setZoom(desired,null,null,{auto:true})}}else{autoZoomInCandidate=null;autoZoomInCandidateAt=0}}\nfunction maybeRerouteNavigation(){if(!navMode||!routeTarget||!telemetry||telemetry.map_x===null||routeRequestInFlight)return;const now=Date.now();const px=Number(telemetry.map_x),py=Number(telemetry.map_y);const toTarget=dist({map_x:px,map_y:py},routeTarget);if(toTarget<35)return;const weakRoute=(!currentRoute||!Array.isArray(currentRoute.polyline)||currentRoute.polyline.length<2);if(weakRoute){if(now-lastRouteRequestAt>2800)requestRoute(routeTarget,false);return}const off=distanceToCurrentRoute(px,py);lastRouteOffRoutePx=off;const moved=(lastRouteAnchorX===null||lastRouteAnchorY===null)?0:Math.hypot(px-lastRouteAnchorX,py-lastRouteAnchorY);if(off<=REROUTE_STICKY_OFF_PX){offRouteSince=0;if(moved>REROUTE_REFRESH_MOVE_PX&&now-lastRouteRequestAt>16000)requestRoute(routeTarget,false);return}if(!offRouteSince)offRouteSince=now;const offMs=now-offRouteSince;if(now-lastRouteRequestAt<REROUTE_MIN_INTERVAL_MS)return;const shouldReroute=(off>REROUTE_HUGE_OFF_PX&&offMs>REROUTE_HUGE_MS)||(off>REROUTE_HARD_OFF_PX&&offMs>REROUTE_HARD_MS)||(off>REROUTE_STICKY_OFF_PX&&offMs>REROUTE_STICKY_MS);if(shouldReroute)requestRoute(routeTarget,false)}\nfunction enterNavMode(forceHeadingUp=false){closeMobilePanels();navMode=true;follow=true;document.getElementById(\'app\').classList.add(\'navMode\');document.getElementById(\'followBtn\').classList.add(\'active\');if(!routeTarget&&selectedPoi)routeTarget=selectedPoi;if(forceHeadingUp&&routeTarget)setNorthUp(false);setZoom(Math.max(zoom,17),null,null,{auto:true});centerOnPlayer();renderTiles(true);renderPlayer();renderMarkers();renderRouteLine();updateNearest();updateNavUi()}\nfunction exitNavMode(){closeMobilePanels();navMode=false;document.getElementById(\'app\').classList.remove(\'navMode\');applyMapRotation();renderAll(true)}\nfunction routePointsForRender(){if(!routeTarget||playerMapX===null||playerMapY===null)return[];const pts=[{map_x:playerMapX,map_y:playerMapY}];const raw=normalizedRoutePolyline();if(raw.length>=2){const tail=trimRoutePolyline(raw,playerMapX,playerMapY);for(const p of tail)pts.push(p)}else if(currentRoute&&currentRoute.mode===\'direct\'){pts.push({map_x:routeTarget.map_x,map_y:routeTarget.map_y})}else{return[]}return pts.filter(p=>Number.isFinite(p.map_x)&&Number.isFinite(p.map_y))}\nfunction ensureRouteEls(){if(routeEls)return routeEls;routeLayer.innerHTML=\'\';const ns=\'http://www.w3.org/2000/svg\';const outer=document.createElementNS(ns,\'polyline\');outer.setAttribute(\'fill\',\'none\');outer.setAttribute(\'stroke\',\'#63f000\');outer.setAttribute(\'stroke-width\',\'10\');outer.setAttribute(\'stroke-linecap\',\'round\');outer.setAttribute(\'stroke-linejoin\',\'round\');outer.setAttribute(\'opacity\',\'0.96\');const inner=document.createElementNS(ns,\'polyline\');inner.setAttribute(\'fill\',\'none\');inner.setAttribute(\'stroke\',\'rgba(255,255,255,.82)\');inner.setAttribute(\'stroke-width\',\'3\');inner.setAttribute(\'stroke-linecap\',\'round\');inner.setAttribute(\'stroke-linejoin\',\'round\');inner.setAttribute(\'opacity\',\'0.85\');const dest=document.createElementNS(ns,\'circle\');dest.setAttribute(\'r\',\'13\');dest.setAttribute(\'fill\',\'#ef4444\');dest.setAttribute(\'stroke\',\'#fff\');dest.setAttribute(\'stroke-width\',\'4\');routeLayer.appendChild(outer);routeLayer.appendChild(inner);routeLayer.appendChild(dest);routeEls={outer,inner,dest};return routeEls}\nfunction renderRouteLine(){if(!routeTarget||playerMapX===null||playerMapY===null){routeLayer.style.display=\'none\';routeLayer.innerHTML=\'\';routeEls=null;lastRoutePoints=\'\';return}const pts=routePointsForRender();if(pts.length<2){routeLayer.style.display=\'none\';routeLayer.innerHTML=\'\';routeEls=null;lastRoutePoints=\'\';return}const r=viewport.getBoundingClientRect();const w=Math.round(r.width),h=Math.round(r.height),sizeSig=w+\'x\'+h;if(sizeSig!==lastRouteSize){routeLayer.setAttribute(\'viewBox\',`0 0 ${w} ${h}`);routeLayer.setAttribute(\'width\',String(w));routeLayer.setAttribute(\'height\',String(h));lastRouteSize=sizeSig;lastRoutePoints=\'\'}const screen=pts.map(p=>mapToScreen(p.map_x,p.map_y));const points=screen.map(p=>`${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(\' \');const last=screen[screen.length-1];const sig=(navMode?\'1\':\'0\')+\'|\'+points+\'|\'+last.x.toFixed(1)+\',\'+last.y.toFixed(1);if(sig!==lastRoutePoints){lastRoutePoints=sig;const els=ensureRouteEls();els.outer.setAttribute(\'points\',points);els.inner.setAttribute(\'points\',points);els.dest.setAttribute(\'cx\',last.x.toFixed(1));els.dest.setAttribute(\'cy\',last.y.toFixed(1))}routeLayer.style.display=navMode?\'block\':\'none\';applyMapRotation()}\nfunction maybeFinishNavigation(){if(!navMode||!routeTarget||!telemetry||telemetry.map_x===null)return false;const now=Date.now();const px=Number(telemetry.map_x),py=Number(telemetry.map_y);const speed=Number(telemetry.speed_kmh)||0;const directPx=dist({map_x:px,map_y:py},routeTarget);const routePts=routePointsForRender();const routePx=routePts.length>=2?routeDistancePx(routePts):Infinity;const arrivePx=Math.min(directPx,routePx);const limitPx=(speed<=NAV_ARRIVE_STOPPED_MAX_KMH)?NAV_ARRIVE_STOPPED_PX:NAV_ARRIVE_PX;if(arrivePx<=limitPx){if(!arriveSince)arriveSince=now;if(now-arriveSince>=NAV_ARRIVE_HOLD_MS){exitNavMode(true,true);return true}}else if(arrivePx>limitPx*1.35){arriveSince=0}return false}\nfunction updateNavUi(){if(!navMode)return;const speed=Math.round((telemetry&&telemetry.speed_kmh)||0);document.getElementById(\'navSpeedBubble\').textContent=speed+\' km/h\';const compass=document.getElementById(\'navCompass\');if(telemetry){compass.textContent=northUp?\'N · north up\':`${Math.round(normalizeAngleDeg(displayHeadingDeg||0))}° · heading up`}const target=routeTarget;document.getElementById(\'navTargetName\').textContent=target?target.title:\'No destination\';if(!telemetry||telemetry.map_x===null||!target){document.getElementById(\'navDistance\').textContent=\'—\';document.getElementById(\'navEta\').textContent=\'—\';document.getElementById(\'navInstruction\').textContent=\'Select a POI and press Build route\';document.getElementById(\'navSub\').textContent=\'Heading-up navigation preview\';renderRouteLine();return}const routePts=routePointsForRender();const remainingPx=routePts.length>=2?routeDistancePx(routePts):dist({map_x:telemetry.map_x,map_y:telemetry.map_y},target);const meters=Math.max(0,Math.round(metersFromMapPx(remainingPx)));const km=meters>=1000?(meters/1000).toFixed(1)+\' km\':meters+\' m\';const etaMin=Math.max(1,Math.round((meters/1000)/Math.max(15,telemetry.speed_kmh||0)*60));document.getElementById(\'navDistance\').textContent=km;document.getElementById(\'navEta\').textContent=etaMin+\' min\';const mode=currentRoute&&currentRoute.mode?currentRoute.mode:\'none\';const failed=currentRoute&&currentRoute.ok===false;let titlePrefix=routeRequestInFlight?\'Recalculating: \':(failed?\'No road route to \':(mode===\'graph\'?\'Route to \':(mode===\'direct\'?\'Direct to \':\'Route to \')));let routeKind=failed?(currentRoute.message||\'road graph failed\'):(mode===\'graph\'?\'road graph route\':(mode===\'direct\'?\'direct preview: no graph loaded\':\'waiting for route\'));document.getElementById(\'navInstruction\').textContent=titlePrefix+target.title;const navRouteHint=routeRequestInFlight?\' · recalculating…\':((offRouteSince&&lastRouteOffRoutePx>REROUTE_STICKY_OFF_PX&&!failed)?\' · holding original route\':(lastRouteOffRoutePx>42&&!failed?\' · return to route\':\'\'));const arrivalHint=arriveSince?\' · arriving…\':\'\';document.getElementById(\'navSub\').textContent=`${km} · ${target.category||\'POI\'} · ${routeKind}${navRouteHint}${arrivalHint}`;document.getElementById(\'navArrow\').textContent=failed?\'!\':\'↑\';renderRouteLine()}\nasync function sendMediaKey(action){const el=document.getElementById(\'musicStatus\');try{const r=await fetch(\'/api/media/\'+action,{method:\'POST\'});const data=await r.json();el.textContent=data.ok?\'Sent: \'+action:(data.error||\'Media key failed\')}catch(e){el.textContent=\'Media key failed\'}setTimeout(()=>{if(el)el.textContent=\'Windows media keys\'},1600)}\nfunction isMobileOrTablet(){return /Android|iPhone|iPad|iPod|Mobile|Tablet/i.test(navigator.userAgent)||((navigator.maxTouchPoints||0)>1&&Math.min(window.innerWidth,window.innerHeight)<1024)}\nasync function loadServerInfo(){const panel=document.getElementById(\'pcLinkPanel\');if(panel&&isMobileOrTablet()){panel.classList.add(\'hideOnDevice\');return}try{const r=await fetch(\'/api/info\',{cache:\'no-store\'});const info=await r.json();const el=document.getElementById(\'phoneUrl\');const btn=document.getElementById(\'copyIpBtn\');const qr=document.getElementById(\'phoneQr\');const url=(info.phone_urls&&info.phone_urls.length)?info.phone_urls[0]:location.origin;if(el)el.textContent=url;if(qr)qr.src=\'/api/qr.svg?text=\'+encodeURIComponent(url);if(btn)btn.onclick=async()=>{try{await navigator.clipboard.writeText(url);btn.textContent=\'Copied\';setTimeout(()=>btn.textContent=\'Copy\',1200)}catch(e){btn.textContent=\'Copy failed\';setTimeout(()=>btn.textContent=\'Copy\',1200)}}}catch(e){const el=document.getElementById(\'phoneUrl\');if(el)el.textContent=location.origin}}\nfunction nearestDistanceTextFromPx(dpx){const meters=Math.max(0,Math.round(metersFromMapPx(dpx)));return meters>=1000?(meters/1000).toFixed(1)+\' km\':meters+\' m\'}\nfunction updateNearest(){const lists=[...document.querySelectorAll(\'[data-nearest-list]\')];if(!lists.length)return;function setAll(html){for(const list of lists)list.innerHTML=html}if(!telemetry||telemetry.map_x===null){setAll(\'<div class="hint">Waiting for telemetry…</div>\');return}if(!markers||!markers.length){setAll(\'<div class="hint">POI markers are loading…</div>\');return}const p={map_x:telemetry.map_x,map_y:telemetry.map_y};let pool=markers;if(categoryFilter)pool=pool.filter(m=>m.category===categoryFilter);const near=pool.map(m=>({...m,dist:dist(p,m)})).sort((a,b)=>a.dist-b.dist).slice(0,4);for(const list of lists){list.innerHTML="";for(const n of near){const div=document.createElement(\'div\');div.className=\'nearItem clickable\';const selected=selectedPoi&&String(selectedPoi.markerId||selectedPoi.id)===String(n.markerId||n.id);div.innerHTML=`<span><b>${selected?\'▶ \':\'\'}${esc(n.title)}</b><br><span class="sub">${esc(n.category)}</span></span><span>${nearestDistanceTextFromPx(n.dist)}</span>`;div.onpointerdown=(ev)=>{ev.stopPropagation();selectPoi(n,false)};list.appendChild(div)}}}\nfunction initSearch(){const input=document.getElementById(\'searchInput\'),clear=document.getElementById(\'searchClearBtn\');if(!input)return;input.addEventListener(\'input\',()=>runSearch(input.value));input.addEventListener(\'focus\',()=>runSearch(input.value));input.addEventListener(\'keydown\',ev=>{if(ev.key===\'Enter\'){const first=document.querySelector(\'.searchItem\');if(first)first.dispatchEvent(new PointerEvent(\'pointerdown\',{bubbles:true}))}});if(clear)clear.onclick=()=>{input.value=\'\';runSearch(\'\');input.focus()}}\nfunction markerDistanceText(m){if(!telemetry||telemetry.map_x===null)return\'\';const dpx=dist({map_x:telemetry.map_x,map_y:telemetry.map_y},m);const meters=Math.round(metersFromMapPx(dpx));return meters>=1000?(meters/1000).toFixed(1)+\' km\':meters+\' m\'}\nfunction runSearch(raw){const box=document.getElementById(\'searchResults\');if(!box)return;const q=String(raw||\'\').trim().toLowerCase();if(q.length<2){box.classList.remove(\'open\');box.innerHTML=\'\';return}let pool=markers||[];if(categoryFilter)pool=pool.filter(m=>m.category===categoryFilter);const terms=q.split(/\\s+/).filter(Boolean);let results=pool.filter(m=>{const hay=[m.title,m.category,m.parent_category,m.description].filter(Boolean).join(\' \').toLowerCase();return terms.every(t=>hay.includes(t))});if(telemetry&&telemetry.map_x!==null){const p={map_x:telemetry.map_x,map_y:telemetry.map_y};results=results.map(m=>({...m,_d:dist(p,m)})).sort((a,b)=>(a._d||0)-(b._d||0))}else{results=results.sort((a,b)=>String(a.title).localeCompare(String(b.title)))}results=results.slice(0,8);box.classList.add(\'open\');if(!results.length){box.innerHTML=\'<div class="searchEmpty">Nothing found. Try another POI name/category.</div>\';return}box.innerHTML=\'\';for(const m of results){const div=document.createElement(\'div\');div.className=\'searchItem\';div.innerHTML=`<div><div class="searchItemTitle">${esc(m.title)}</div><div class="searchItemMeta">${esc(m.category||\'POI\')}${m.parent_category?\' · \'+esc(m.parent_category):\'\'}${markerDistanceText(m)?\' · \'+markerDistanceText(m):\'\'}</div></div><button title="Build route">Route</button>`;div.onpointerdown=(ev)=>{if(ev.target&&ev.target.tagName===\'BUTTON\')return;ev.stopPropagation();selectPoi(m,false)};div.querySelector(\'button\').onpointerdown=(ev)=>{ev.preventDefault();ev.stopPropagation();startRouteToPoi(m)};box.appendChild(div)}}\nfunction esc(s){return String(s).replace(/[&<>"\']/g,ch=>({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',\'"\':\'&quot;\',"\'":\'&#39;\'}[ch]))}\nfunction updateHud(){if(!telemetry)return;const hasError=!!telemetry.udp_error;const on=!hasError&&!!telemetry.receiving;const hasPos=telemetry.map_x!==null&&telemetry.map_y!==null;const dot=document.getElementById(\'statusDot\');dot.classList.toggle(\'on\',on);document.getElementById(\'statusText\').textContent=hasError?\'UDP ERROR\':(telemetry.pause_coordinate_hold?\'HOLDING\':(on?\'LIVE\':(hasPos?\'HOLDING\':\'WAITING\')));document.getElementById(\'speed\').textContent=Math.round(telemetry.speed_kmh||0);document.getElementById(\'gear\').textContent=telemetry.gear||\'-\';document.getElementById(\'heading\').textContent=Math.round(telemetry.heading_deg||0);document.getElementById(\'mapxy\').textContent=telemetry.map_x!==null?`${Math.round(telemetry.map_x)}, ${Math.round(telemetry.map_y)}`:\'—\'}\nfunction renderAll(force=false){renderTiles(force);renderPlayer();renderMarkers();renderMapPickMarker();updateNearest();renderRouteLine();updateNavUi()}\nfunction renderInteractionFrame(){interactionRenderRaf=0;renderTiles();renderPlayer();renderRouteLine();renderMarkers();renderMapPickMarker();updateNavUi()}\nfunction scheduleInteractionRender(){if(interactionRenderRaf)return;interactionRenderRaf=requestAnimationFrame(renderInteractionFrame)}\nfunction lerpAngleDeg(current,target,alpha){let delta=((target-current+540)%360)-180;return current+delta*alpha}\nfunction animationLoop(){try{if(targetMapX!==null&&targetMapY!==null){if(displayMapX===null){displayMapX=targetMapX;displayMapY=targetMapY;displayHeadingDeg=targetHeadingDeg}else{const posAlpha=navMode?0.16:0.24;displayMapX+=(targetMapX-displayMapX)*posAlpha;displayMapY+=(targetMapY-displayMapY)*posAlpha;displayHeadingDeg=lerpAngleDeg(displayHeadingDeg,targetHeadingDeg,0.14)}playerMapX=displayMapX;playerMapY=displayMapY;maybeAutoZoomNavigation();centerIfFollowing();renderTiles();renderPlayer();renderRouteLine();renderMapPickMarker();if(!maybeFinishNavigation()){updateNavUi();maybeRerouteNavigation()}applyMapRotation();const now=performance.now();if(now-lastMarkerRenderAt>260){renderMarkers();lastMarkerRenderAt=now}if(now-lastNearestRenderAt>700){updateNearest();lastNearestRenderAt=now}}}catch(e){console.warn(\'animation error\',e)}requestAnimationFrame(animationLoop)}\nasync function pollTelemetry(){try{const r=await fetch(\'/api/state?ts=\'+Date.now(),{cache:\'no-store\'});telemetry=await r.json();updateHud();if(telemetry&&telemetry.map_x!==null){targetMapX=Number(telemetry.map_x);targetMapY=Number(telemetry.map_y);targetHeadingDeg=updateHeadingFromMotion(targetMapX,targetMapY,Number(telemetry.speed_kmh)||0,telemetry.heading_deg||0);if(displayMapX===null){displayMapX=targetMapX;displayMapY=targetMapY;displayHeadingDeg=targetHeadingDeg;playerMapX=displayMapX;playerMapY=displayMapY;}}}catch(e){console.warn(\'telemetry poll error\',e)}finally{setTimeout(pollTelemetry,120)}}\nasync function loadMarkers(){try{const r=await fetch(\'/api/markers?ts=\'+Date.now(),{cache:\'no-store\'});const data=await r.json();markers=Array.isArray(data)?data:[];console.log(\'POI markers loaded\',markers.length)}catch(e){console.warn(\'markers fetch error\',e);markers=[]}try{populateCategories();renderTiles(true);renderMarkers();updateNearest()}catch(renderError){console.warn(\'markers render error\',renderError)}}\nfunction pointerDistance(){const pts=[...activePointers.values()];if(pts.length<2)return 0;const dx=pts[0].x-pts[1].x,dy=pts[0].y-pts[1].y;return Math.sqrt(dx*dx+dy*dy)}\nfunction pointerCenter(){const pts=[...activePointers.values()];return{x:(pts[0].x+pts[1].x)/2,y:(pts[0].y+pts[1].y)/2}}\nviewport.addEventListener(\'pointerdown\',e=>{\n  if(e.button===2)return;\n  if(e.target.closest&&e.target.closest(\'.marker,.poiPopup,.mapContextMenu,.nearest,.searchPanel,.musicWidget,.navBottomBar,.navTopInstruction,.cachePanel,.mobileDock,.mobileSheet,.mobileSheetClose,.mobileNearestOverlay,.navInfoToggle,.navMediaToggle\'))return;\n  activePointers.set(e.pointerId,{x:e.clientX,y:e.clientY});\n  tapStart={id:e.pointerId,x:e.clientX,y:e.clientY,t:Date.now()};tapWasMulti=false;\n  if(e.target===viewport||e.target.id===\'mapWorld\'||e.target.id===\'tileLayer\'||e.target.id===\'playerLayer\')clearPoi();\n  try{viewport.setPointerCapture(e.pointerId)}catch(_){}\n  if(activePointers.size===2){\n    tapWasMulti=true;tapStart=null;pinchStart={dist:pointerDistance(),zoom};lastPinchZoom=zoom;dragging=false;dragStart=null;viewport.classList.remove(\'dragging\');\n    if(navMode)keepNavigatorFollow();\n    return;\n  }\n  dragging=true;\n  if(navMode&&follow){keepNavigatorFollow();centerOnPlayer()}\n  else{follow=false;document.getElementById(\'followBtn\').classList.remove(\'active\')}\n  viewport.classList.add(\'dragging\');\n  dragStart={x:e.clientX,y:e.clientY,panX,panY};\n});\nviewport.addEventListener(\'pointermove\',e=>{\n  if(!activePointers.has(e.pointerId))return;\n  activePointers.set(e.pointerId,{x:e.clientX,y:e.clientY});\n  if(tapStart&&tapStart.id===e.pointerId&&Math.hypot(e.clientX-tapStart.x,e.clientY-tapStart.y)>22)tapStart=null;\n  if(activePointers.size>=2&&pinchStart){\n    if(navMode)keepNavigatorFollow();\n    const d=pointerDistance();\n    if(d>0&&pinchStart.dist>0){\n      const ratio=d/pinchStart.dist;let target=pinchStart.zoom;\n      if(ratio>1.18)target=pinchStart.zoom+1;if(ratio>1.55)target=pinchStart.zoom+2;if(ratio<0.85)target=pinchStart.zoom-1;if(ratio<0.62)target=pinchStart.zoom-2;\n      target=clamp(target,MIN_ZOOM,MAX_ZOOM);\n      if(target!==lastPinchZoom){const c=pointerCenter();setZoom(target,c.x,c.y);lastPinchZoom=target}\n    }\n    return;\n  }\n  if(navMode&&follow){keepNavigatorFollow();centerOnPlayer();return}\n  if(!dragging||!dragStart)return;\n  panX=dragStart.panX-(e.clientX-dragStart.x);panY=dragStart.panY-(e.clientY-dragStart.y);clampPan();scheduleInteractionRender();\n});\nfunction endPointer(e){const wasTap=!!(tapStart&&tapStart.id===e.pointerId&&!tapWasMulti&&Math.hypot(e.clientX-tapStart.x,e.clientY-tapStart.y)<=22&&(Date.now()-tapStart.t)<650);activePointers.delete(e.pointerId);if(activePointers.size<2)pinchStart=null;if(activePointers.size===0){dragging=false;dragStart=null;tapWasMulti=false;viewport.classList.remove(\'dragging\');if(wasTap)maybeHandleDoubleTap(e);tapStart=null;if(navMode&&follow){keepNavigatorFollow();centerOnPlayer();renderTiles(true);renderPlayer();renderRouteLine();renderMapPickMarker();updateNavUi()}}}\nviewport.addEventListener(\'pointerup\',endPointer);viewport.addEventListener(\'pointercancel\',endPointer);\nviewport.addEventListener(\'contextmenu\',e=>{e.preventDefault();if(e.target.closest&&e.target.closest(\'.marker,.poiPopup,.mapContextMenu,.nearest,.searchPanel,.musicWidget,.navBottomBar,.navTopInstruction,.cachePanel,.mobileDock,.mobileSheet,.mobileSheetClose,.mobileNearestOverlay,.navInfoToggle,.navMediaToggle\'))return;showContextMenuForScreen(e.clientX,e.clientY,false)},{passive:false});\nviewport.addEventListener(\'wheel\',e=>{e.preventDefault();setZoom(zoom+(e.deltaY<0?1:-1),e.clientX,e.clientY)},{passive:false});\nwindow.addEventListener(\'resize\',()=>{setMobileUiClass();if(!isMobileLayout())closeMobilePanels();centerIfFollowing();renderAll(true)});\nsetMobileUiClass();initControls();loadServerInfo();centerOnPlayer();renderTiles(true);requestAnimationFrame(animationLoop);pollTelemetry();loadMarkers();\n\n\n</script>\n</body>\n</html>'
def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative_path
    return Path(__file__).resolve().parent / relative_path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


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
            self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
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
