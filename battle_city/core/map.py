"""
battle_city/core/map.py

TileMap -- 8x8px block grid for the Battle City game engine.

Three map formats, all using 8px blocks:

    classic : 26 cols x 26 rows  = 208x208px  (13x13 logical 16px tiles)
    medium  : 50 cols x 50 rows  = 400x400px  (25x25 logical 16px tiles)
    xlarge  : 74 cols x 50 rows  = 592x400px  (37x25 logical 16px tiles)

Text file format (one char = one 8x8 block):
    '.' EMPTY  (0)
    '#' BRICK  (1)  -- destructible
    '@' STEEL  (2)  -- indestructible by default
    '~' WATER  (3)  -- blocks tanks, bullets pass through
    '%' FOREST (4)  -- hides tanks, bullets pass through
    '-' ICE    (5)  -- passable, causes sliding

Maps are loaded exclusively from .txt files via MapData.from_txt().
Spawnable objects (eagle, tanks) use x,y pixel coordinates (top-left
corner of the 16x16 sprite). They are NOT stored in the grid -- they
are spawned by World at runtime from the map metadata.

No external dependencies (no pygame).
Loaded by MapLoader, not directly by client code.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# TileType
# ---------------------------------------------------------------------------

class TileType(IntEnum):
    """One 8x8px block type. Values match the txt file symbol encoding."""
    EMPTY  = 0
    BRICK  = 1
    STEEL  = 2
    WATER  = 3
    FOREST = 4
    ICE    = 5


CHAR_TO_TILE: dict[str, TileType] = {
    '.': TileType.EMPTY,
    '#': TileType.BRICK,
    '@': TileType.STEEL,
    '~': TileType.WATER,
    '%': TileType.FOREST,
    '-': TileType.ICE,
}

TILE_TO_CHAR: dict[TileType, str] = {v: k for k, v in CHAR_TO_TILE.items()}

VALID_CHARS: frozenset[str] = frozenset(CHAR_TO_TILE.keys())


# ---------------------------------------------------------------------------
# TileProperties
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TileProperties:
    """Immutable physical properties of a tile type."""
    passable_tank:   bool
    passable_bullet: bool
    destructible:    bool
    hides_tank:      bool  # forest conceals tanks visually
    slippery:        bool  # ice causes tanks to slide


_TILE_PROPS: dict[TileType, TileProperties] = {
    TileType.EMPTY:  TileProperties(True,  True,  False, False, False),
    TileType.BRICK:  TileProperties(False, False, True,  False, False),
    TileType.STEEL:  TileProperties(False, False, False, False, False),
    # Steel IS destructible by 3-star bullet -- CollisionSystem calls set()
    # directly after checking bullet power level.
    TileType.WATER:  TileProperties(False, True,  False, False, False),
    TileType.FOREST: TileProperties(True,  True,  False, True,  False),
    TileType.ICE:    TileProperties(True,  True,  False, False, True),
}


def tile_properties(tile: TileType) -> TileProperties:
    return _TILE_PROPS[tile]


# ---------------------------------------------------------------------------
# Position -- immutable (col, row) in 8px block units
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Position:
    """Immutable grid coordinate in 8px block units."""
    col: int
    row: int

    def neighbors(self) -> list[Position]:
        return [
            Position(self.col,     self.row - 1),
            Position(self.col,     self.row + 1),
            Position(self.col - 1, self.row),
            Position(self.col + 1, self.row),
        ]

    def __add__(self, other: Position) -> Position:
        return Position(self.col + other.col, self.row + other.row)

    def to_pixel(self, block_px: int = 8) -> tuple[int, int]:
        """Return the top-left pixel coordinate for this block."""
        return self.col * block_px, self.row * block_px

    @staticmethod
    def from_pixel(x: int, y: int, block_px: int = 8) -> Position:
        """Convert a pixel coordinate to a block Position."""
        return Position(col=x // block_px, row=y // block_px)


# ---------------------------------------------------------------------------
# Spawnable object descriptors -- x,y in pixels, NOT col/row
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EagleSpawn:
    """
    Eagle spawn data.
    x, y: top-left pixel position of the 16x16 eagle sprite.
    """
    x: int
    y: int


@dataclass(frozen=True)
class TankSpawn:
    """
    Tank spawn data.
    x, y: top-left pixel position of the 16x16 tank sprite.
    direction: initial facing direction.
    """
    x:         int
    y:         int
    direction: str   # "UP" | "DOWN" | "LEFT" | "RIGHT"


# ---------------------------------------------------------------------------
# MapFormat -- the three supported map sizes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MapFormat:
    """Static definition of a map format."""
    name:     str
    cols:     int
    rows:     int
    block_px: int = 8

    @property
    def pixel_width(self) -> int:
        return self.cols * self.block_px

    @property
    def pixel_height(self) -> int:
        return self.rows * self.block_px

    @property
    def logical_cols(self) -> int:
        return self.cols // 2

    @property
    def logical_rows(self) -> int:
        return self.rows // 2


FORMATS: dict[str, MapFormat] = {
    "classic": MapFormat("classic", cols=26, rows=26),  # 208x208px, 13x13 tiles
    "medium":  MapFormat("medium",  cols=50, rows=50),  # 400x400px, 25x25 tiles
    "xlarge":  MapFormat("xlarge",  cols=74, rows=50),  # 592x400px, 37x25 tiles
}

# Default eagle + spawn positions per format (x,y pixels, top-left of 16x16 sprite)
# Derived from _model.txt files for each format.
_DEFAULT_EAGLE: dict[str, EagleSpawn] = {
    # x = (pixel_width - 16) // 2  -- eagle sprite centred horizontally
    # y = (rows - 2) * 8           -- always on the last two block rows
    "classic": EagleSpawn(x=96,  y=192),   # (208-16)//2=96,  col=12, row=24
    "medium":  EagleSpawn(x=192, y=384),   # (400-16)//2=192, col=24, row=48
    "xlarge":  EagleSpawn(x=288, y=384),   # (592-16)//2=288, col=36, row=48
}

_DEFAULT_PLAYER_SPAWNS: dict[str, list[TankSpawn]] = {
    # P1 = eagle_x - 32 (two 16px tiles to the left)
    # P2 = eagle_x + 16 (one 16px tile to the right)
    "classic": [
        TankSpawn(x=64,  y=192, direction="UP"),
        TankSpawn(x=112, y=192, direction="UP"),
    ],
    "medium": [
        TankSpawn(x=160, y=384, direction="UP"),
        TankSpawn(x=208, y=384, direction="UP"),
    ],
    "xlarge": [
        TankSpawn(x=256, y=384, direction="UP"),
        TankSpawn(x=304, y=384, direction="UP"),
    ],
}

_DEFAULT_ENEMY_SPAWNS: dict[str, list[TankSpawn]] = {
    # Three spawn points: left edge, centre, right edge (y=0, top of map)
    "classic": [
        TankSpawn(x=0,   y=0, direction="DOWN"),   # left
        TankSpawn(x=96,  y=0, direction="DOWN"),   # centre
        TankSpawn(x=192, y=0, direction="DOWN"),   # right
    ],
    "medium": [
        TankSpawn(x=0,   y=0, direction="DOWN"),
        TankSpawn(x=192, y=0, direction="DOWN"),
        TankSpawn(x=384, y=0, direction="DOWN"),
    ],
    "xlarge": [
        TankSpawn(x=0,   y=0, direction="DOWN"),
        TankSpawn(x=288, y=0, direction="DOWN"),
        TankSpawn(x=576, y=0, direction="DOWN"),
    ],
}


# ---------------------------------------------------------------------------
# MapData -- immutable value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MapData:
    """
    Static map configuration loaded from a .txt file.
    Immutable after construction -- acts as a Value Object.

    Single construction path: MapData.from_txt()
    Maps are always loaded from text files -- no JSON loading.

    Spawnable objects (eagle, tanks) use x,y pixel coordinates.
    The grid contains terrain tiles only.
    """
    name:           str
    format_name:    str          # "classic" | "medium" | "xlarge"
    stage:          int | None   # classic stage number
    scenario:       int | None   # custom scenario number
    description:    str
    cols:           int
    rows:           int
    block_px:       int
    raw_grid:       tuple[tuple[int, ...], ...]
    eagle:          EagleSpawn
    player_spawns:  tuple[TankSpawn, ...]
    enemy_spawns:   tuple[TankSpawn, ...]
    enemies:        dict[str, int]
    max_on_screen:  int
    total_enemies:  int

    # ------------------------------------------------------------------
    # Derived dimensions
    # ------------------------------------------------------------------

    @property
    def pixel_width(self) -> int:
        return self.cols * self.block_px

    @property
    def pixel_height(self) -> int:
        return self.rows * self.block_px

    @property
    def logical_cols(self) -> int:
        return self.cols // 2

    @property
    def logical_rows(self) -> int:
        return self.rows // 2

    @property
    def is_classic(self) -> bool:
        return self.format_name == "classic"

    @property
    def is_medium(self) -> bool:
        return self.format_name == "medium"

    @property
    def is_xlarge(self) -> bool:
        return self.format_name == "xlarge"

    # ------------------------------------------------------------------
    # Construction -- single entry point
    # ------------------------------------------------------------------

    @classmethod
    def from_txt(
        cls,
        path:        Path,
        format_name: str,
        stage:       int | None = None,
        scenario:    int | None = None,
        enemies:     dict[str, int] | None = None,
    ) -> MapData:
        """
        Load a .txt map file and build a MapData.

        This is the only way to construct a MapData.

        Args:
            path:        path to the .txt file
            format_name: "classic" | "medium" | "xlarge"
            stage:       NES stage number (classic maps only)
            scenario:    custom scenario number (medium / xlarge maps)
            enemies:     enemy composition -- uses defaults if None

        Raises:
            FileNotFoundError: if the file does not exist
            ValueError:        if format_name is unknown
        """
        if not path.exists():
            raise FileNotFoundError(f"Map file not found: {path}")
        if format_name not in FORMATS:
            raise ValueError(
                f"Unknown format '{format_name}'. "
                f"Valid: {list(FORMATS)}"
            )

        fmt   = FORMATS[format_name]
        lines = path.read_text(encoding="utf-8").splitlines()

        # Filter out legend / comment lines -- keep only valid map rows
        map_lines = [l for l in lines if l and set(l) <= VALID_CHARS]

        grid_rows: list[tuple[int, ...]] = []
        for i in range(fmt.rows):
            line = map_lines[i] if i < len(map_lines) else ""
            line = line[:fmt.cols].ljust(fmt.cols, '.')
            grid_rows.append(
                tuple(CHAR_TO_TILE.get(c, TileType.EMPTY).value
                      for c in line)
            )

        default_enemies: dict[str, int] = {
            "basic": 18, "fast": 2, "power": 0, "armor": 0
        }
        ens = enemies or default_enemies

        return cls(
            name          = path.stem,
            format_name   = format_name,
            stage         = stage,
            scenario      = scenario,
            description   = (
                f"Stage {stage}" if stage
                else f"Scenario {scenario} ({format_name})"
            ),
            cols          = fmt.cols,
            rows          = fmt.rows,
            block_px      = fmt.block_px,
            raw_grid      = tuple(grid_rows),
            eagle         = _DEFAULT_EAGLE[format_name],
            player_spawns = tuple(_DEFAULT_PLAYER_SPAWNS[format_name]),
            enemy_spawns  = tuple(_DEFAULT_ENEMY_SPAWNS[format_name]),
            enemies       = ens,
            max_on_screen = 4,
            total_enemies = sum(ens.values()),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Raise ValueError if grid dimensions are inconsistent."""
        if len(self.raw_grid) != self.rows:
            raise ValueError(
                f"Grid has {len(self.raw_grid)} rows, expected {self.rows}"
            )
        for i, row in enumerate(self.raw_grid):
            if len(row) != self.cols:
                raise ValueError(
                    f"Row {i} has {len(row)} cols, expected {self.cols}"
                )


# ---------------------------------------------------------------------------
# TileMap -- mutable grid used during gameplay
# ---------------------------------------------------------------------------

class TileMap:
    """
    Mutable 8px-block grid representing live terrain state.

    Built from MapData via TileMap.from_map_data().
    The source MapData is preserved for reset().

    Pixel sizes by format:
        classic : (208, 208)
        medium  : (400, 400)
        xlarge  : (592, 400)
    """

    def __init__(
        self,
        grid:   list[list[TileType]],
        source: MapData,
    ) -> None:
        self._grid:   list[list[TileType]] = grid
        self._source: MapData              = source

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_map_data(cls, data: MapData) -> TileMap:
        grid = [
            [TileType(cell) for cell in row]
            for row in data.raw_grid
        ]
        return cls(grid=grid, source=data)

    # ------------------------------------------------------------------
    # Dimensions (read-only)
    # ------------------------------------------------------------------

    @property
    def cols(self) -> int:
        return self._source.cols

    @property
    def rows(self) -> int:
        return self._source.rows

    @property
    def block_px(self) -> int:
        return self._source.block_px

    @property
    def pixel_size(self) -> tuple[int, int]:
        """(width_px, height_px) of the full map."""
        return self._source.pixel_width, self._source.pixel_height

    @property
    def pixel_width(self) -> int:
        return self._source.pixel_width

    @property
    def pixel_height(self) -> int:
        return self._source.pixel_height

    # ------------------------------------------------------------------
    # Grid access
    # ------------------------------------------------------------------

    def get(self, pos: Position) -> TileType:
        self._check_bounds(pos)
        return self._grid[pos.row][pos.col]

    def set(self, pos: Position, tile: TileType) -> None:
        """Set tile -- called by CollisionSystem for destruction events."""
        self._check_bounds(pos)
        self._grid[pos.row][pos.col] = tile

    def destroy(self, pos: Position) -> bool:
        """
        Destroy the block at pos if destructible.
        Returns True on success, False if indestructible.
        Steel destruction is handled via set() in CollisionSystem.
        """
        self._check_bounds(pos)
        if not tile_properties(self._grid[pos.row][pos.col]).destructible:
            return False
        self._grid[pos.row][pos.col] = TileType.EMPTY
        return True

    # ------------------------------------------------------------------
    # Passability queries
    # ------------------------------------------------------------------

    def is_passable_for_tank(self, pos: Position) -> bool:
        if not self._in_bounds(pos):
            return False
        return tile_properties(self._grid[pos.row][pos.col]).passable_tank

    def is_passable_for_bullet(self, pos: Position) -> bool:
        if not self._in_bounds(pos):
            return False
        return tile_properties(self._grid[pos.row][pos.col]).passable_bullet

    def hides_tank(self, pos: Position) -> bool:
        if not self._in_bounds(pos):
            return False
        return tile_properties(self._grid[pos.row][pos.col]).hides_tank

    def is_slippery(self, pos: Position) -> bool:
        if not self._in_bounds(pos):
            return False
        return tile_properties(self._grid[pos.row][pos.col]).slippery

    # ------------------------------------------------------------------
    # Pixel coordinate helpers
    # ------------------------------------------------------------------

    def block_pixel_rect(self, pos: Position) -> tuple[int, int, int, int]:
        """(x, y, w, h) in pixels for a block -- used by renderer."""
        s = self._source.block_px
        return pos.col * s, pos.row * s, s, s

    def position_from_pixel(self, x: int, y: int) -> Position:
        """Convert pixel coords to block Position -- used by CollisionSystem."""
        s = self._source.block_px
        return Position(col=x // s, row=y // s)

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def iter_blocks(self) -> Iterator[tuple[Position, TileType]]:
        """Iterate every block -- used by renderer."""
        for row in range(self.rows):
            for col in range(self.cols):
                yield Position(col, row), self._grid[row][col]

    def blocks_of_type(self, tile_type: TileType) -> list[Position]:
        return [
            Position(col, row)
            for row in range(self.rows)
            for col in range(self.cols)
            if self._grid[row][col] == tile_type
        ]

    # ------------------------------------------------------------------
    # Reset / clone
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Restore to initial state. Called by World.reset()."""
        self._grid = [
            [TileType(cell) for cell in row]
            for row in self._source.raw_grid
        ]

    def clone(self) -> TileMap:
        return TileMap(
            grid=copy.deepcopy(self._grid),
            source=self._source,
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def source(self) -> MapData:
        return self._source

    @property
    def name(self) -> str:
        return self._source.name

    @property
    def eagle(self) -> EagleSpawn:
        """Eagle spawn position in pixels."""
        return self._source.eagle

    @property
    def player_spawns(self) -> tuple[TankSpawn, ...]:
        return self._source.player_spawns

    @property
    def enemy_spawns(self) -> tuple[TankSpawn, ...]:
        return self._source.enemy_spawns

    # ------------------------------------------------------------------
    # Bounds
    # ------------------------------------------------------------------

    def _in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.col < self.cols and 0 <= pos.row < self.rows

    def _check_bounds(self, pos: Position) -> None:
        if not self._in_bounds(pos):
            raise IndexError(
                f"Position {pos} out of bounds "
                f"(grid {self.cols}x{self.rows})"
            )

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return "\n".join(
            "".join(TILE_TO_CHAR[c] for c in row)
            for row in self._grid
        )