"""
scripts/view_map.py

Standalone pygame map viewer -- reads .txt map files directly.
Uses real tile sprites from assets/.

Supported formats (auto-detected from parent folder name):
    classic : 26x26 blocks = 208x208px  (13x13 logical tiles)
    medium  : 50x50 blocks = 400x400px  (25x25 logical tiles)
    xlarge  : 74x50 blocks = 592x400px  (37x25 logical tiles)

Usage:
    python scripts/view_map.py assets/maps/classic/1.txt
    python scripts/view_map.py assets/maps/classic/1.txt --scale 2
    python scripts/view_map.py assets/maps/classic/

Controls:
    LEFT / RIGHT  -- previous / next map
    + / -         -- zoom in / out
    G             -- toggle grid overlay
    R             -- reload current map
    ESC / Q       -- quit
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

import pygame

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ASSETS_DIR  = PROJECT_DIR / "assets"

HUD_HEIGHT = 120

# Format detection from parent folder name
FORMAT_BY_FOLDER: dict[str, str] = {
    "classic": "classic",
    "medium":  "medium",
    "xlarge":  "xlarge",
}

# cols x rows per format  (74 cols confirmed from _model.txt)
FORMAT_DIMS: dict[str, tuple[int, int]] = {
    "classic": (26, 26),
    "medium":  (50, 50),
    "xlarge":  (74, 50),
}

# Tile char -> sprite key
CHAR_KEY: dict[str, str] = {
    '.': "empty",
    '#': "brick",
    '@': "steel",
    '~': "water",
    '%': "forest",
    '-': "ice",
}

VALID_CHARS = set(CHAR_KEY.keys())

# Fallback colours when a sprite file is missing
FALLBACK: dict[str, tuple[int, int, int]] = {
    "empty":  (  0,   0,   0),
    "brick":  (180,  80,  40),
    "steel":  (160, 160, 160),
    "water":  ( 40,  80, 180),
    "forest": ( 30, 120,  30),
    "ice":    (180, 220, 240),
}

# Eagle + spawn positions per format (x,y pixels, top-left of 16x16 sprite)
EAGLE_POS: dict[str, tuple[int, int]] = {
    # x = (pixel_width - 16) // 2  -- eagle sprite centred horizontally
    # y = (rows - 2) * 8           -- always on the last two block rows
    "classic": (96,  192),   # (208-16)//2=96,  col=12, row=24
    "medium":  (192, 384),   # (400-16)//2=192, col=24, row=48
    "xlarge":  (288, 384),   # (592-16)//2=288, col=36, row=48
}

PLAYER_SPAWNS: dict[str, list[tuple[int, int]]] = {
    # Flanking eagle: P1 left of eagle, P2 right of eagle (each 16px wide)
    "classic": [(96 - 24, 192), (96 + 24, 192)],   # x=64, x=112
    "medium":  [(192 - 24, 384), (192 + 24, 384)], # x=160, x=208
    "xlarge":  [(288 - 24, 384), (288 + 24, 384)], # x=256, x=304
}

ENEMY_SPAWNS: dict[str, list[tuple[int, int]]] = {
    # Three spawn points: left edge, centre, right edge (top of map)
    "classic": [(0, 0), (96,  0), (192, 0)],   # 208px wide, centre=96
    "medium":  [(0, 0), (192, 0), (384, 0)],   # 400px wide, centre=192
    "xlarge":  [(0, 0), (288, 0), (576, 0)],   # 592px wide, centre=288
}

EAGLE_OUTLINE = (220, 180,  30)
SPAWN_P_COLOR = ( 30, 180, 220)
SPAWN_E_COLOR = (220,  60,  60)
GRID_COLOR    = ( 25,  25,  25)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(path: Path) -> str:
    """Infer format from parent folder name, then from line length."""
    parent = path.parent.name.lower()
    if parent in FORMAT_BY_FOLDER:
        return FORMAT_BY_FOLDER[parent]
    try:
        lines = [l for l in path.read_text(encoding="utf-8")
                 .splitlines() if set(l) <= VALID_CHARS and l]
        n = max((len(l) for l in lines), default=0)
        if n <= 28:  return "classic"
        if n <= 52:  return "medium"
        return "xlarge"
    except Exception:
        return "classic"


# ---------------------------------------------------------------------------
# Asset loading (call AFTER pygame.display.set_mode)
# ---------------------------------------------------------------------------

def load_sprites(assets_dir: Path) -> dict[str, pygame.Surface]:
    spec: dict[str, Path] = {
        "brick":  assets_dir / "tiles/brick.png",
        "steel":  assets_dir / "tiles/steel.png",
        "water":  assets_dir / "tiles/water.png",
        "forest": assets_dir / "tiles/grass.png",
        "ice":    assets_dir / "tiles/ice.png",
        "eagle":  assets_dir / "sprites/eagle/0.png",
    }
    surfs: dict[str, pygame.Surface] = {}

    empty = pygame.Surface((8, 8))
    empty.fill((0, 0, 0))
    surfs["empty"] = empty

    for key, path in spec.items():
        if path.exists():
            surfs[key] = pygame.image.load(str(path)).convert_alpha()
        else:
            print(f"[view_map] missing: {path}")
            fb = pygame.Surface((16, 16))
            fb.fill((255, 0, 255))
            surfs[key] = fb

    return surfs


# ---------------------------------------------------------------------------
# Map parsing
# ---------------------------------------------------------------------------

def parse_txt(path: Path, fmt: str) -> list[list[str]]:
    """Read a .txt map file -- skip legend lines, return 2D list of keys."""
    cols, rows = FORMAT_DIMS[fmt]
    all_lines  = path.read_text(encoding="utf-8").splitlines()
    # Keep only lines that contain valid map characters
    map_lines  = [l for l in all_lines if l and set(l) <= VALID_CHARS]

    grid: list[list[str]] = []
    for i in range(rows):
        line = map_lines[i] if i < len(map_lines) else ""
        line = line[:cols].ljust(cols, '.')
        grid.append([CHAR_KEY.get(c, "empty") for c in line])
    return grid


# ---------------------------------------------------------------------------
# Scale cache
# ---------------------------------------------------------------------------

_sc: dict[tuple[int, int, int], pygame.Surface] = {}

def sc(surf: pygame.Surface, px: int) -> pygame.Surface:
    key = (id(surf), surf.get_width(), px)
    if key not in _sc:
        _sc[key] = pygame.transform.scale(surf, (px, px))
    return _sc[key]

def clear_sc() -> None:
    _sc.clear()


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_map(
    screen:    pygame.Surface,
    grid:      list[list[str]],
    fmt:       str,
    surfs:     dict[str, pygame.Surface],
    bpx:       int,
    show_grid: bool,
) -> None:
    screen.fill((0, 0, 0))

    for r, row in enumerate(grid):
        for c, key in enumerate(row):
            x  = c * bpx
            y  = r * bpx
            sf = surfs.get(key)
            if sf:
                screen.blit(sc(sf, bpx), (x, y))
            else:
                pygame.draw.rect(screen, FALLBACK.get(key, (80, 0, 80)),
                                 (x, y, bpx, bpx))
            if show_grid and bpx >= 4:
                pygame.draw.rect(screen, GRID_COLOR,
                                 (x, y, bpx, bpx), 1)

    # Eagle -- 16x16 sprite = 2x2 blocks at scale
    eagle_px = bpx * 2
    base_ex, base_ey = EAGLE_POS[fmt]
    ex = base_ex * bpx // 8
    ey = base_ey * bpx // 8
    eagle_sf = surfs.get("eagle")
    if eagle_sf:
        screen.blit(
            pygame.transform.scale(eagle_sf, (eagle_px, eagle_px)),
            (ex, ey),
        )
    pygame.draw.rect(screen, EAGLE_OUTLINE, (ex, ey, eagle_px, eagle_px), 2)

    # Player spawns (2x2 block outline)
    for base_px, base_py in PLAYER_SPAWNS[fmt]:
        sx = base_px * bpx // 8
        sy = base_py * bpx // 8
        pygame.draw.rect(screen, SPAWN_P_COLOR,
                         (sx, sy, bpx * 2, bpx * 2), 2)

    # Enemy spawns (2x2 block outline)
    for base_px, base_py in ENEMY_SPAWNS[fmt]:
        sx = base_px * bpx // 8
        sy = base_py * bpx // 8
        pygame.draw.rect(screen, SPAWN_E_COLOR,
                         (sx, sy, bpx * 2, bpx * 2), 2)


def draw_hud(
    screen:    pygame.Surface,
    font:      pygame.font.Font,
    path:      Path,
    fmt:       str,
    win_w:     int,
    win_h:     int,
    scale:     float,
    show_grid: bool,
    idx:       int,
    total:     int,
) -> None:
    cols, rows = FORMAT_DIMS[fmt]
    bpx        = 8
    ex, ey     = EAGLE_POS[fmt]
    ps         = PLAYER_SPAWNS[fmt]
    es         = ENEMY_SPAWNS[fmt]
    g_lbl      = "ON" if show_grid else "OFF"

    lines = [
        f"{path.name}  [{fmt}]  map {idx + 1}/{total}",
        f"grid {cols}x{rows} blocks @ {bpx}px = "
        f"{cols*bpx}x{rows*bpx}px  "
        f"logical {cols//2}x{rows//2} tiles  scale x{scale:.2f}",
        f"eagle  x={ex}px  y={ey}px",
        f"P spawns  {['x='+str(x)+' y='+str(y) for x, y in ps]}",
        f"E spawns  {['x='+str(x)+' y='+str(y) for x, y in es]}",
        f"ESC/Q quit   R reload   LEFT/RIGHT prev/next   "
        f"+/- zoom   G grid [{g_lbl}]",
    ]

    bar_y = win_h - HUD_HEIGHT
    bar   = pygame.Surface((win_w, HUD_HEIGHT), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 200))
    screen.blit(bar, (0, bar_y))

    y = bar_y + 6
    for line in lines:
        screen.blit(font.render(line, True, (210, 210, 210)), (8, y))
        y += 18


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------

def compute_bpx(scale: float) -> int:
    return max(1, int(8 * scale))


def compute_win(fmt: str, scale: float) -> tuple[int, int]:
    cols, rows = FORMAT_DIMS[fmt]
    bpx = compute_bpx(scale)
    return cols * bpx, rows * bpx + HUD_HEIGHT


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Battle City map viewer")
    parser.add_argument("path",  help=".txt map file or directory")
    parser.add_argument("--scale", type=float, default=2.0,
                        help="Display scale (default 2.0)")
    parser.add_argument("--no-grid", action="store_true",
                        help="Hide block grid lines")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        map_files = sorted(
            f for f in target.glob("*.txt")
            if not f.name.startswith("_")
        )
    elif target.is_file():
        map_files = [target]
    else:
        print(f"Error: '{target}' not found")
        sys.exit(1)

    if not map_files:
        print("No .txt map files found.")
        sys.exit(1)

    idx       = 0
    scale     = args.scale
    show_grid = not args.no_grid

    pygame.init()
    font  = pygame.font.SysFont("monospace", 12)
    clock = pygame.time.Clock()

    fmt    = detect_format(map_files[idx])
    ww, wh = compute_win(fmt, scale)
    screen = pygame.display.set_mode((ww, wh), pygame.RESIZABLE)
    pygame.display.set_caption(f"Battle City -- {map_files[idx].name}")

    # Load assets AFTER set_mode -- convert_alpha() requires a video mode
    surfs = load_sprites(ASSETS_DIR)
    grid  = parse_txt(map_files[idx], fmt)

    dirty   = True
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                k = event.key

                if k in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

                elif k == pygame.K_r:
                    fmt   = detect_format(map_files[idx])
                    grid  = parse_txt(map_files[idx], fmt)
                    dirty = True

                elif k == pygame.K_RIGHT:
                    idx   = (idx + 1) % len(map_files)
                    fmt   = detect_format(map_files[idx])
                    grid  = parse_txt(map_files[idx], fmt)
                    clear_sc()
                    dirty = True

                elif k == pygame.K_LEFT:
                    idx   = (idx - 1) % len(map_files)
                    fmt   = detect_format(map_files[idx])
                    grid  = parse_txt(map_files[idx], fmt)
                    clear_sc()
                    dirty = True

                elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    scale = min(scale + 0.25, 8.0)
                    clear_sc()
                    dirty = True

                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    scale = max(scale - 0.25, 0.25)
                    clear_sc()
                    dirty = True

                elif k == pygame.K_g:
                    show_grid = not show_grid
                    dirty     = True

        if dirty:
            nw, nh = compute_win(fmt, scale)
            if (nw, nh) != (ww, wh):
                ww, wh = nw, nh
                screen = pygame.display.set_mode((ww, wh), pygame.RESIZABLE)

            pygame.display.set_caption(
                f"Battle City -- {map_files[idx].name}")

            bpx = compute_bpx(scale)
            draw_map(screen, grid, fmt, surfs, bpx, show_grid)
            draw_hud(screen, font, map_files[idx], fmt,
                     ww, wh, scale, show_grid, idx, len(map_files))
            pygame.display.flip()
            dirty = False

        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()