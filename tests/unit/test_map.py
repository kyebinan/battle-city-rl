"""
tests/unit/test_map.py

Unit tests for battle_city/core/map.py.

Symbol mapping (from _model.txt):
    '.' EMPTY  (0)
    '#' BRICK  (1)
    '@' STEEL  (2)
    '~' WATER  (3)
    '%' FOREST (4)
    '-' ICE    (5)

Coverage:
    - TileType values and CHAR_TO_TILE / TILE_TO_CHAR mappings
    - TileProperties per type
    - Position: creation, add, neighbors, to_pixel, from_pixel, hash
    - EagleSpawn / TankSpawn: x,y pixel fields, no col/row
    - MapFormat: pixel/logical dimensions for all 3 formats
    - MapData.from_txt: classic (26x26), medium (50x50), xlarge (74x50)
    - MapData: only from_txt -- no from_json / to_json
    - MapData: pixel dims, logical dims, validate, format flags
    - TileMap: get/set/destroy, passability, reset, clone
    - TileMap: block_pixel_rect, position_from_pixel, pixel_size
    - TileMap pixel_size: classic (208,208), medium (400,400), xlarge (592,400)
    - TileMap: iter_blocks count, blocks_of_type, repr symbols
    - TileMap metadata: eagle/spawns expose x,y not col/row
"""

import pytest
from pathlib import Path

from battle_city.core.map import (
    TileType, TileProperties, TileMap, MapData,
    Position, EagleSpawn, TankSpawn, MapFormat,
    tile_properties, CHAR_TO_TILE, TILE_TO_CHAR, VALID_CHARS,
    FORMATS, _DEFAULT_EAGLE, _DEFAULT_PLAYER_SPAWNS, _DEFAULT_ENEMY_SPAWNS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_txt(cols: int, rows: int, tmp: Path, name: str = "map.txt") -> Path:
    """
    Write a minimal .txt map with one of each tile type in row 0.
    Row 0: # @ ~ % - . . . ...   (BRICK STEEL WATER FOREST ICE EMPTY...)
    All other rows: EMPTY
    """
    row0  = "#@~%-" + "." * (cols - 5)
    lines = [row0[:cols]] + ["." * cols] * (rows - 1)
    p = tmp / name
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classic_txt(tmp_path):
    return _make_txt(26, 26, tmp_path)

@pytest.fixture
def medium_txt(tmp_path):
    return _make_txt(50, 50, tmp_path)

@pytest.fixture
def xlarge_txt(tmp_path):
    return _make_txt(74, 50, tmp_path)

@pytest.fixture
def classic_data(classic_txt):
    return MapData.from_txt(classic_txt, "classic", stage=1)

@pytest.fixture
def medium_data(medium_txt):
    return MapData.from_txt(medium_txt, "medium", scenario=1)

@pytest.fixture
def xlarge_data(xlarge_txt):
    return MapData.from_txt(xlarge_txt, "xlarge", scenario=1)

@pytest.fixture
def classic_tm(classic_data):
    return TileMap.from_map_data(classic_data)

@pytest.fixture
def medium_tm(medium_data):
    return TileMap.from_map_data(medium_data)

@pytest.fixture
def xlarge_tm(xlarge_data):
    return TileMap.from_map_data(xlarge_data)


# ---------------------------------------------------------------------------
# TileType & symbol mapping
# ---------------------------------------------------------------------------

class TestTileType:
    def test_values(self):
        assert TileType.EMPTY  == 0
        assert TileType.BRICK  == 1
        assert TileType.STEEL  == 2
        assert TileType.WATER  == 3
        assert TileType.FOREST == 4
        assert TileType.ICE    == 5

    def test_from_int(self):
        assert TileType(1) == TileType.BRICK

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            TileType(99)

    def test_char_to_tile(self):
        assert CHAR_TO_TILE['.'] == TileType.EMPTY
        assert CHAR_TO_TILE['#'] == TileType.BRICK
        assert CHAR_TO_TILE['@'] == TileType.STEEL
        assert CHAR_TO_TILE['~'] == TileType.WATER   # ~ = WATER
        assert CHAR_TO_TILE['%'] == TileType.FOREST  # % = FOREST
        assert CHAR_TO_TILE['-'] == TileType.ICE     # - = ICE

    def test_tile_to_char(self):
        assert TILE_TO_CHAR[TileType.EMPTY]  == '.'
        assert TILE_TO_CHAR[TileType.BRICK]  == '#'
        assert TILE_TO_CHAR[TileType.STEEL]  == '@'
        assert TILE_TO_CHAR[TileType.WATER]  == '~'
        assert TILE_TO_CHAR[TileType.FOREST] == '%'
        assert TILE_TO_CHAR[TileType.ICE]    == '-'

    def test_roundtrip(self):
        for ch, tile in CHAR_TO_TILE.items():
            assert TILE_TO_CHAR[tile] == ch

    def test_valid_chars(self):
        assert '.' in VALID_CHARS
        assert '#' in VALID_CHARS
        assert '@' in VALID_CHARS
        assert '~' in VALID_CHARS
        assert '%' in VALID_CHARS
        assert '-' in VALID_CHARS
        assert 'X' not in VALID_CHARS


# ---------------------------------------------------------------------------
# TileProperties
# ---------------------------------------------------------------------------

class TestTileProperties:
    def test_empty(self):
        p = tile_properties(TileType.EMPTY)
        assert p.passable_tank   is True
        assert p.passable_bullet is True
        assert p.destructible    is False
        assert p.hides_tank      is False
        assert p.slippery        is False

    def test_brick(self):
        p = tile_properties(TileType.BRICK)
        assert p.passable_tank   is False
        assert p.passable_bullet is False
        assert p.destructible    is True

    def test_steel(self):
        p = tile_properties(TileType.STEEL)
        assert p.passable_tank   is False
        assert p.passable_bullet is False
        assert p.destructible    is False  # 3-star handled by CollisionSystem

    def test_water(self):
        p = tile_properties(TileType.WATER)
        assert p.passable_tank   is False
        assert p.passable_bullet is True
        assert p.destructible    is False

    def test_forest(self):
        p = tile_properties(TileType.FOREST)
        assert p.passable_tank   is True
        assert p.passable_bullet is True
        assert p.hides_tank      is True
        assert p.destructible    is False

    def test_ice(self):
        p = tile_properties(TileType.ICE)
        assert p.passable_tank   is True
        assert p.passable_bullet is True
        assert p.slippery        is True
        assert p.destructible    is False


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

class TestPosition:
    def test_fields(self):
        p = Position(3, 7)
        assert p.col == 3 and p.row == 7

    def test_immutable(self):
        with pytest.raises(Exception):
            Position(1, 2).col = 9  # type: ignore

    def test_add(self):
        assert Position(1, 2) + Position(3, 4) == Position(4, 6)

    def test_neighbors(self):
        n = Position(5, 5).neighbors()
        assert len(n) == 4
        assert Position(5, 4) in n
        assert Position(5, 6) in n
        assert Position(4, 5) in n
        assert Position(6, 5) in n

    def test_to_pixel(self):
        assert Position(3, 4).to_pixel(8) == (24, 32)
        assert Position(0, 0).to_pixel(8) == (0,  0)

    def test_from_pixel(self):
        assert Position.from_pixel(24, 32, 8) == Position(3, 4)
        assert Position.from_pixel(0,  0,  8) == Position(0, 0)

    def test_hashable(self):
        s = {Position(1, 2), Position(1, 2), Position(3, 4)}
        assert len(s) == 2

    def test_equality(self):
        assert Position(1, 2) == Position(1, 2)
        assert Position(1, 2) != Position(2, 1)


# ---------------------------------------------------------------------------
# EagleSpawn / TankSpawn -- x,y pixel fields only
# ---------------------------------------------------------------------------

class TestSpawnDescriptors:
    def test_eagle_fields(self):
        e = EagleSpawn(x=96, y=192)
        assert e.x == 96 and e.y == 192

    def test_eagle_no_col_row(self):
        e = EagleSpawn(x=96, y=192)
        assert not hasattr(e, 'col')
        assert not hasattr(e, 'row')

    def test_tank_fields(self):
        t = TankSpawn(x=64, y=192, direction="UP")
        assert t.x == 64 and t.y == 192 and t.direction == "UP"

    def test_tank_no_col_row(self):
        t = TankSpawn(x=64, y=192, direction="UP")
        assert not hasattr(t, 'col')
        assert not hasattr(t, 'row')

    def test_eagle_immutable(self):
        with pytest.raises(Exception):
            EagleSpawn(x=96, y=192).x = 0  # type: ignore

    # Default positions per format
    def test_classic_eagle(self):
        e = _DEFAULT_EAGLE["classic"]
        assert e.x == 96 and e.y == 192    # (208-16)//2 = 96

    def test_medium_eagle(self):
        e = _DEFAULT_EAGLE["medium"]
        assert e.x == 192 and e.y == 384   # (400-16)//2 = 192

    def test_xlarge_eagle(self):
        e = _DEFAULT_EAGLE["xlarge"]
        assert e.x == 288 and e.y == 384   # (592-16)//2 = 288

    def test_classic_player_spawns(self):
        ps = _DEFAULT_PLAYER_SPAWNS["classic"]
        assert len(ps) == 2
        assert ps[0].x == 64  and ps[0].y == 192
        assert ps[1].x == 112 and ps[1].y == 192

    def test_medium_player_spawns(self):
        ps = _DEFAULT_PLAYER_SPAWNS["medium"]
        assert ps[0].x == 160 and ps[0].y == 384
        assert ps[1].x == 208 and ps[1].y == 384

    def test_xlarge_player_spawns(self):
        ps = _DEFAULT_PLAYER_SPAWNS["xlarge"]
        assert ps[0].x == 256 and ps[0].y == 384
        assert ps[1].x == 304 and ps[1].y == 384

    def test_classic_enemy_spawns(self):
        es = _DEFAULT_ENEMY_SPAWNS["classic"]
        assert len(es) == 3
        assert es[0].x == 0   and es[0].y == 0
        assert es[1].x == 96  and es[1].y == 0
        assert es[2].x == 192 and es[2].y == 0

    def test_xlarge_enemy_spawns(self):
        es = _DEFAULT_ENEMY_SPAWNS["xlarge"]
        assert es[0].x == 0   and es[0].y == 0
        assert es[1].x == 288 and es[1].y == 0
        assert es[2].x == 576 and es[2].y == 0

    def test_all_directions_valid(self):
        valid = {"UP", "DOWN", "LEFT", "RIGHT"}
        for fmt in ("classic", "medium", "xlarge"):
            for s in _DEFAULT_PLAYER_SPAWNS[fmt]:
                assert s.direction in valid
            for s in _DEFAULT_ENEMY_SPAWNS[fmt]:
                assert s.direction in valid


# ---------------------------------------------------------------------------
# MapFormat
# ---------------------------------------------------------------------------

class TestMapFormat:
    def test_classic(self):
        f = FORMATS["classic"]
        assert f.cols == 26 and f.rows == 26
        assert f.pixel_width  == 208
        assert f.pixel_height == 208
        assert f.logical_cols == 13
        assert f.logical_rows == 13

    def test_medium(self):
        f = FORMATS["medium"]
        assert f.cols == 50 and f.rows == 50
        assert f.pixel_width  == 400
        assert f.pixel_height == 400
        assert f.logical_cols == 25
        assert f.logical_rows == 25

    def test_xlarge(self):
        f = FORMATS["xlarge"]
        assert f.cols == 74 and f.rows == 50
        assert f.pixel_width  == 592
        assert f.pixel_height == 400
        assert f.logical_cols == 37
        assert f.logical_rows == 25


# ---------------------------------------------------------------------------
# MapData.from_txt -- single construction path
# ---------------------------------------------------------------------------

class TestMapDataFromTxt:

    # --- format flags ---
    def test_classic_fields(self, classic_data):
        d = classic_data
        assert d.format_name == "classic"
        assert d.cols        == 26
        assert d.rows        == 26
        assert d.block_px    == 8
        assert d.stage       == 1
        assert d.scenario    is None
        assert d.is_classic
        assert not d.is_medium
        assert not d.is_xlarge

    def test_medium_fields(self, medium_data):
        assert medium_data.format_name == "medium"
        assert medium_data.cols        == 50
        assert medium_data.rows        == 50
        assert medium_data.scenario    == 1
        assert medium_data.is_medium

    def test_xlarge_fields(self, xlarge_data):
        assert xlarge_data.format_name == "xlarge"
        assert xlarge_data.cols        == 74
        assert xlarge_data.rows        == 50
        assert xlarge_data.is_xlarge

    # --- tile parsing with correct symbol mapping ---
    def test_tile_parsing_symbols(self, classic_data):
        """Row 0: # @ ~ % - . -- verify correct symbol->TileType mapping."""
        g = classic_data.raw_grid
        assert g[0][0] == TileType.BRICK   # '#'
        assert g[0][1] == TileType.STEEL   # '@'
        assert g[0][2] == TileType.WATER   # '~'
        assert g[0][3] == TileType.FOREST  # '%'
        assert g[0][4] == TileType.ICE     # '-'
        assert g[0][5] == TileType.EMPTY   # '.'

    def test_water_is_tilde(self, tmp_path):
        """~ must map to WATER, not any other tile."""
        p = tmp_path / "w.txt"
        p.write_text("~" * 26 + "\n" + "." * 26 * 25, encoding="utf-8")
        d = MapData.from_txt(p, "classic")
        assert all(v == TileType.WATER for v in d.raw_grid[0])

    def test_forest_is_percent(self, tmp_path):
        """% must map to FOREST."""
        p = tmp_path / "f.txt"
        p.write_text("%" * 26 + "\n" + "." * 26 * 25, encoding="utf-8")
        d = MapData.from_txt(p, "classic")
        assert all(v == TileType.FOREST for v in d.raw_grid[0])

    def test_ice_is_dash(self, tmp_path):
        """- must map to ICE."""
        p = tmp_path / "i.txt"
        p.write_text("-" * 26 + "\n" + "." * 26 * 25, encoding="utf-8")
        d = MapData.from_txt(p, "classic")
        assert all(v == TileType.ICE for v in d.raw_grid[0])

    # --- grid dimensions ---
    def test_grid_dimensions_classic(self, classic_data):
        assert len(classic_data.raw_grid)    == 26
        assert len(classic_data.raw_grid[0]) == 26

    def test_grid_dimensions_medium(self, medium_data):
        assert len(medium_data.raw_grid)    == 50
        assert len(medium_data.raw_grid[0]) == 50

    def test_grid_dimensions_xlarge(self, xlarge_data):
        assert len(xlarge_data.raw_grid)    == 50
        assert len(xlarge_data.raw_grid[0]) == 74

    # --- eagle / spawns ---
    def test_eagle_x_y_classic(self, classic_data):
        assert classic_data.eagle.x == 96
        assert classic_data.eagle.y == 192

    def test_eagle_x_y_xlarge(self, xlarge_data):
        assert xlarge_data.eagle.x == 288
        assert xlarge_data.eagle.y == 384

    def test_player_spawns(self, classic_data):
        ps = classic_data.player_spawns
        assert len(ps) == 2
        assert ps[0].x == 64  and ps[0].y == 192
        assert ps[1].x == 112 and ps[1].y == 192

    def test_enemy_spawns_at_top(self, classic_data):
        assert all(s.y == 0 for s in classic_data.enemy_spawns)

    # --- errors ---
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            MapData.from_txt(tmp_path / "nope.txt", "classic")

    def test_unknown_format_raises(self, classic_txt):
        with pytest.raises(ValueError, match="Unknown format"):
            MapData.from_txt(classic_txt, "giant")

    # --- no JSON methods ---
    def test_no_from_json(self):
        assert not hasattr(MapData, 'from_json')

    def test_no_to_json(self):
        assert not hasattr(MapData, 'to_json')

    # --- validate ---
    def test_validate_classic(self, classic_data):
        classic_data.validate()

    def test_validate_medium(self, medium_data):
        medium_data.validate()

    def test_validate_xlarge(self, xlarge_data):
        xlarge_data.validate()

    def test_short_file_padded_with_empty(self, tmp_path):
        p = tmp_path / "short.txt"
        p.write_text("##\n", encoding="utf-8")
        d = MapData.from_txt(p, "classic")
        assert len(d.raw_grid)    == 26
        assert len(d.raw_grid[0]) == 26
        assert all(v == TileType.EMPTY for v in d.raw_grid[2])

    def test_legend_lines_filtered_out(self, tmp_path):
        """Lines with non-map chars (legend) must be ignored."""
        content = (
            "#" * 26 + "\n"
            + "." * 26 + "\n"
            + "'.' EMPTY  (0)\n"
            + "'#' BRICK  (1)\n"
            + "'~' WATER  (3)\n"
        )
        p = tmp_path / "legend.txt"
        p.write_text(content, encoding="utf-8")
        d = MapData.from_txt(p, "classic")
        assert len(d.raw_grid) == 26


# ---------------------------------------------------------------------------
# MapData pixel / logical dimensions
# ---------------------------------------------------------------------------

class TestMapDataDimensions:
    def test_classic(self, classic_data):
        assert classic_data.pixel_width  == 208   # 26 * 8
        assert classic_data.pixel_height == 208
        assert classic_data.logical_cols == 13    # 26 // 2
        assert classic_data.logical_rows == 13

    def test_medium(self, medium_data):
        assert medium_data.pixel_width  == 400    # 50 * 8
        assert medium_data.pixel_height == 400
        assert medium_data.logical_cols == 25
        assert medium_data.logical_rows == 25

    def test_xlarge(self, xlarge_data):
        assert xlarge_data.pixel_width  == 592    # 74 * 8
        assert xlarge_data.pixel_height == 400    # 50 * 8
        assert xlarge_data.logical_cols == 37     # 74 // 2
        assert xlarge_data.logical_rows == 25     # 50 // 2


# ---------------------------------------------------------------------------
# TileMap -- grid operations
# ---------------------------------------------------------------------------

class TestTileMapGrid:
    def test_initial_tiles(self, classic_tm):
        # Row 0: # @ ~ % - .
        assert classic_tm.get(Position(0, 0)) == TileType.BRICK
        assert classic_tm.get(Position(1, 0)) == TileType.STEEL
        assert classic_tm.get(Position(2, 0)) == TileType.WATER
        assert classic_tm.get(Position(3, 0)) == TileType.FOREST
        assert classic_tm.get(Position(4, 0)) == TileType.ICE
        assert classic_tm.get(Position(5, 0)) == TileType.EMPTY

    def test_set(self, classic_tm):
        pos = Position(5, 5)
        classic_tm.set(pos, TileType.WATER)
        assert classic_tm.get(pos) == TileType.WATER

    def test_get_oob_raises(self, classic_tm):
        with pytest.raises(IndexError):
            classic_tm.get(Position(99, 99))

    def test_set_oob_raises(self, classic_tm):
        with pytest.raises(IndexError):
            classic_tm.set(Position(-1, 0), TileType.BRICK)

    def test_destroy_brick(self, classic_tm):
        assert classic_tm.destroy(Position(0, 0)) is True
        assert classic_tm.get(Position(0, 0))     == TileType.EMPTY

    def test_destroy_steel_fails(self, classic_tm):
        assert classic_tm.destroy(Position(1, 0)) is False
        assert classic_tm.get(Position(1, 0))     == TileType.STEEL

    def test_destroy_water_fails(self, classic_tm):
        assert classic_tm.destroy(Position(2, 0)) is False

    def test_passable_tank(self, classic_tm):
        assert classic_tm.is_passable_for_tank(Position(5, 0)) is True   # EMPTY
        assert classic_tm.is_passable_for_tank(Position(0, 0)) is False  # BRICK
        assert classic_tm.is_passable_for_tank(Position(1, 0)) is False  # STEEL
        assert classic_tm.is_passable_for_tank(Position(2, 0)) is False  # WATER
        assert classic_tm.is_passable_for_tank(Position(3, 0)) is True   # FOREST
        assert classic_tm.is_passable_for_tank(Position(4, 0)) is True   # ICE

    def test_passable_bullet(self, classic_tm):
        assert classic_tm.is_passable_for_bullet(Position(2, 0)) is True   # WATER
        assert classic_tm.is_passable_for_bullet(Position(3, 0)) is True   # FOREST
        assert classic_tm.is_passable_for_bullet(Position(0, 0)) is False  # BRICK
        assert classic_tm.is_passable_for_bullet(Position(1, 0)) is False  # STEEL

    def test_oob_passable_false(self, classic_tm):
        assert classic_tm.is_passable_for_tank(Position(-1, 0))   is False
        assert classic_tm.is_passable_for_bullet(Position(0, 99)) is False

    def test_hides_forest_only(self, classic_tm):
        assert classic_tm.hides_tank(Position(3, 0)) is True   # FOREST
        assert classic_tm.hides_tank(Position(4, 0)) is False  # ICE
        assert classic_tm.hides_tank(Position(5, 0)) is False  # EMPTY

    def test_slippery_ice_only(self, classic_tm):
        assert classic_tm.is_slippery(Position(4, 0)) is True   # ICE
        assert classic_tm.is_slippery(Position(3, 0)) is False  # FOREST
        assert classic_tm.is_slippery(Position(5, 0)) is False  # EMPTY

    def test_reset(self, classic_tm):
        classic_tm.destroy(Position(0, 0))
        assert classic_tm.get(Position(0, 0)) == TileType.EMPTY
        classic_tm.reset()
        assert classic_tm.get(Position(0, 0)) == TileType.BRICK

    def test_clone_independent(self, classic_tm):
        clone = classic_tm.clone()
        classic_tm.destroy(Position(0, 0))
        assert clone.get(Position(0, 0)) == TileType.BRICK


# ---------------------------------------------------------------------------
# TileMap -- pixel dimensions per format
# ---------------------------------------------------------------------------

class TestTileMapPixelDimensions:
    def test_classic(self, classic_tm):
        assert classic_tm.pixel_size   == (208, 208)
        assert classic_tm.pixel_width  == 208
        assert classic_tm.pixel_height == 208
        assert classic_tm.block_px     == 8
        assert classic_tm.cols         == 26
        assert classic_tm.rows         == 26

    def test_medium(self, medium_tm):
        assert medium_tm.pixel_size   == (400, 400)
        assert medium_tm.pixel_width  == 400
        assert medium_tm.pixel_height == 400
        assert medium_tm.cols         == 50
        assert medium_tm.rows         == 50

    def test_xlarge(self, xlarge_tm):
        assert xlarge_tm.pixel_size   == (592, 400)
        assert xlarge_tm.pixel_width  == 592
        assert xlarge_tm.pixel_height == 400
        assert xlarge_tm.cols         == 74
        assert xlarge_tm.rows         == 50


# ---------------------------------------------------------------------------
# TileMap -- pixel coordinate helpers
# ---------------------------------------------------------------------------

class TestTileMapPixelHelpers:
    def test_block_pixel_rect_origin(self, classic_tm):
        assert classic_tm.block_pixel_rect(Position(0, 0)) == (0, 0, 8, 8)

    def test_block_pixel_rect_arbitrary(self, classic_tm):
        x, y, w, h = classic_tm.block_pixel_rect(Position(3, 5))
        assert x == 24 and y == 40 and w == 8 and h == 8

    def test_position_from_pixel(self, classic_tm):
        assert classic_tm.position_from_pixel(24, 40) == Position(3, 5)
        assert classic_tm.position_from_pixel(0,  0)  == Position(0, 0)

    def test_roundtrip(self, classic_tm):
        pos = Position(4, 7)
        x, y, w, h = classic_tm.block_pixel_rect(pos)
        assert classic_tm.position_from_pixel(x, y) == pos


# ---------------------------------------------------------------------------
# TileMap -- iteration
# ---------------------------------------------------------------------------

class TestTileMapIteration:
    def test_iter_classic(self, classic_tm):
        assert sum(1 for _ in classic_tm.iter_blocks()) == 26 * 26

    def test_iter_medium(self, medium_tm):
        assert sum(1 for _ in medium_tm.iter_blocks()) == 50 * 50

    def test_iter_xlarge(self, xlarge_tm):
        assert sum(1 for _ in xlarge_tm.iter_blocks()) == 74 * 50

    def test_blocks_of_type_brick(self, classic_tm):
        bricks = classic_tm.blocks_of_type(TileType.BRICK)
        assert Position(0, 0) in bricks

    def test_repr_symbols(self, classic_tm):
        r = repr(classic_tm)
        assert '#' in r   # BRICK
        assert '@' in r   # STEEL
        assert '~' in r   # WATER
        assert '%' in r   # FOREST
        assert '-' in r   # ICE
        assert '.' in r   # EMPTY


# ---------------------------------------------------------------------------
# TileMap -- metadata (eagle + spawns: x,y only)
# ---------------------------------------------------------------------------

class TestTileMapMetadata:
    def test_eagle_x_y(self, classic_tm):
        assert classic_tm.eagle.x == 96
        assert classic_tm.eagle.y == 192

    def test_eagle_no_col_row(self, classic_tm):
        assert not hasattr(classic_tm.eagle, 'col')
        assert not hasattr(classic_tm.eagle, 'row')

    def test_player_spawns_x_y(self, classic_tm):
        ps = classic_tm.player_spawns
        assert ps[0].x == 64  and ps[0].y == 192
        assert ps[1].x == 112 and ps[1].y == 192

    def test_enemy_spawns_x_y(self, classic_tm):
        es = classic_tm.enemy_spawns
        assert all(hasattr(s, 'x') and hasattr(s, 'y') for s in es)
        assert all(not hasattr(s, 'col') for s in es)
        assert all(s.y == 0 for s in es)

    def test_xlarge_eagle(self, xlarge_tm):
        assert xlarge_tm.eagle.x == 288
        assert xlarge_tm.eagle.y == 384

    def test_name(self, classic_tm):
        assert classic_tm.name == "map"

    def test_source(self, classic_tm, classic_data):
        assert classic_tm.source is classic_data