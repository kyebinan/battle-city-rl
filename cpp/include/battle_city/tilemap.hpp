// battle_city/cpp/include/battle_city/tilemap.hpp


#pragma once

#include "battle_city/config.hpp"
#include "battle_city/geometry.hpp"

#include <cstdint>
#include <vector>

namespace bc {

// One 8x8 block type. Values match the .txt symbol encoding from map.py.
enum class TileType : std::uint8_t {
    EMPTY  = 0,
    BRICK  = 1,
    STEEL  = 2,
    WATER  = 3,
    FOREST = 4,
    ICE    = 5,
};

// Immutable physical properties of a tile (port of TileProperties dataclass).
struct TileProperties {
    bool passable_tank;
    bool passable_bullet;
    bool destructible;
    bool hides_tank;     // forest conceals tanks
    bool slippery;       // ice causes sliding
};

inline constexpr TileProperties tile_properties(TileType t) {
    switch (t) {
        //                          tank   bullet destr  hide   slip
        case TileType::EMPTY:  return {true,  true,  false, false, false};
        case TileType::BRICK:  return {false, false, true,  false, false};
        // Steel destructible only by 3-star bullet -- handled by set() in the
        // collision system after checking bullet power, like the Python note.
        case TileType::STEEL:  return {false, false, false, false, false};
        case TileType::WATER:  return {false, true,  false, false, false};
        case TileType::FOREST: return {true,  true,  false, true,  false};
        case TileType::ICE:    return {true,  true,  false, false, true};
    }
    return {true, true, false, false, false};
}

// ---------------------------------------------------------------------------
// TileMap
// ---------------------------------------------------------------------------
struct TileMap {
    std::int32_t cols = 0;
    std::int32_t rows = 0;
    std::int32_t block_px = config::BLOCK_PX;
    std::vector<TileType> grid;  // size = cols*rows, row-major

    TileMap() = default;
    TileMap(std::int32_t c, std::int32_t r, std::int32_t bpx = config::BLOCK_PX)
        : cols(c), rows(r), block_px(bpx), grid(static_cast<std::size_t>(c) * r, TileType::EMPTY) {}

    // ----- dimensions -----
    constexpr std::int32_t pixel_width()  const { return cols * block_px; }
    constexpr std::int32_t pixel_height() const { return rows * block_px; }

    // ----- bounds -----
    constexpr bool in_bounds(int col, int row) const {
        return col >= 0 && col < cols && row >= 0 && row < rows;
    }
    constexpr bool in_bounds(Position p) const { return in_bounds(p.col, p.row); }

    constexpr std::size_t index(int col, int row) const {
        return static_cast<std::size_t>(row) * cols + col;
    }

    // ----- grid access (caller guarantees bounds, or use checked queries) -----
    TileType get(Position p) const { return grid[index(p.col, p.row)]; }
    void     set(Position p, TileType t) { grid[index(p.col, p.row)] = t; }

    // Destroy block if destructible. True on success, False if indestructible
    // or OOB. (Steel destruction by 3-star goes through set() in collision sys.)
    bool destroy(Position p) {
        if (!in_bounds(p)) return false;
        if (!tile_properties(grid[index(p.col, p.row)]).destructible) return false;
        grid[index(p.col, p.row)] = TileType::EMPTY;
        return true;
    }

    // ----- passability queries (OOB = blocking, like Python) -----
    bool is_passable_for_tank(Position p) const {
        if (!in_bounds(p)) return false;
        return tile_properties(get(p)).passable_tank;
    }
    bool is_passable_for_bullet(Position p) const {
        if (!in_bounds(p)) return false;
        return tile_properties(get(p)).passable_bullet;
    }
    bool hides_tank(Position p) const {
        if (!in_bounds(p)) return false;
        return tile_properties(get(p)).hides_tank;
    }
    bool is_slippery(Position p) const {
        if (!in_bounds(p)) return false;
        return tile_properties(get(p)).slippery;
    }

    // ----- pixel helpers -----
    Position position_from_pixel(int x, int y) const {
        return Position{x / block_px, y / block_px};
    }
};

// char <-> tile (txt loading). Returns EMPTY for unknown char.
inline constexpr TileType char_to_tile(char c) {
    switch (c) {
        case '.': return TileType::EMPTY;
        case '#': return TileType::BRICK;
        case '@': return TileType::STEEL;
        case '~': return TileType::WATER;
        case '%': return TileType::FOREST;
        case '-': return TileType::ICE;
    }
    return TileType::EMPTY;
}

// True if c is one of the 6 terrain symbols. Used by the loader to reject
// stray characters (e.g. legend/template files) with a clear error.
inline constexpr bool is_valid_map_char(char c) {
    return c == '.' || c == '#' || c == '@' ||
           c == '~' || c == '%' || c == '-';
}

inline constexpr char tile_to_char(TileType t) {
    switch (t) {
        case TileType::EMPTY:  return '.';
        case TileType::BRICK:  return '#';
        case TileType::STEEL:  return '@';
        case TileType::WATER:  return '~';
        case TileType::FOREST: return '%';
        case TileType::ICE:    return '-';
    }
    return '.';
}

}  // namespace bc