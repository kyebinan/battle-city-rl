// battle_city/cpp/include/battle_city/map_loader.hpp

#pragma once

#include "battle_city/config.hpp"
#include "battle_city/geometry.hpp"
#include "battle_city/tilemap.hpp"

#include <fstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace bc {

// A spawn point in pixels (top-left of the 16px sprite) + a facing.
struct SpawnPoint {
    std::int32_t x = 0;
    std::int32_t y = 0;
    config::Direction direction = config::Direction::UP;
};

// Everything a reset needs: the terrain template + derived spawn points.
struct MapTemplate {
    TileMap map;
    SpawnPoint eagle;
    std::vector<SpawnPoint> ally_spawns;   // P1, P2
    std::vector<SpawnPoint> enemy_spawns;  // 3 fixed top spots
};

// ---------------------------------------------------------------------------
// Spawn derivation -- pure function of dimensions (NES layout).
// ---------------------------------------------------------------------------
inline void derive_spawns(MapTemplate& t) {
    const int W = t.map.pixel_width();
    const int s = t.map.block_px;
    const int rows = t.map.rows;
    const int sprite = config::TILE_PX;  // 16

    const int eagle_x = (W - sprite) / 2;
    const int eagle_y = (rows - 2) * s;

    t.eagle = SpawnPoint{eagle_x, eagle_y, config::Direction::UP};

    // Allies beside the eagle: P1 two tiles left, P2 one tile right.
    t.ally_spawns = {
        SpawnPoint{eagle_x - 2 * sprite, eagle_y, config::Direction::UP},
        SpawnPoint{eagle_x + sprite,     eagle_y, config::Direction::UP},
    };

    // Enemies: three fixed top spots (left corner, centre, right corner).
    t.enemy_spawns = {
        SpawnPoint{0,            0, config::Direction::DOWN},
        SpawnPoint{(W - sprite)/2, 0, config::Direction::DOWN},
        SpawnPoint{W - sprite,   0, config::Direction::DOWN},
    };
}

// ---------------------------------------------------------------------------
// Parse a txt grid into a MapTemplate. Strict: unknown chars throw.
// expected_cols/rows: pass 0 to accept whatever the file has; else validate.
// ---------------------------------------------------------------------------
inline MapTemplate load_map_from_txt(const std::string& path,
                                     int expected_cols = 0,
                                     int expected_rows = 0) {
    std::ifstream in(path);
    if (!in)
        throw std::runtime_error("map_loader: cannot open '" + path + "'");

    std::vector<std::string> lines;
    std::string line;
    while (std::getline(in, line)) {
        // strip trailing CR (Windows line endings) so widths match
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;  // skip blank lines
        lines.push_back(line);
    }
    if (lines.empty())
        throw std::runtime_error("map_loader: empty file '" + path + "'");

    const int rows = static_cast<int>(lines.size());
    const int cols = static_cast<int>(lines[0].size());

    for (int r = 0; r < rows; ++r)
        if (static_cast<int>(lines[r].size()) != cols)
            throw std::runtime_error("map_loader: ragged row " +
                std::to_string(r) + " in '" + path + "'");

    if (expected_cols && cols != expected_cols)
        throw std::runtime_error("map_loader: cols mismatch in '" + path + "'");
    if (expected_rows && rows != expected_rows)
        throw std::runtime_error("map_loader: rows mismatch in '" + path + "'");

    MapTemplate t;
    t.map = TileMap(cols, rows);
    for (int r = 0; r < rows; ++r) {
        for (int c = 0; c < cols; ++c) {
            const char ch = lines[r][c];
            if (!is_valid_map_char(ch))
                throw std::runtime_error(
                    std::string("map_loader: invalid char '") + ch + "' at (" +
                    std::to_string(c) + "," + std::to_string(r) + ") in '" + path + "'");
            t.map.set(Position{c, r}, char_to_tile(ch));
        }
    }

    derive_spawns(t);
    return t;
}

// ---------------------------------------------------------------------------
// MapRegistry -- load-once cache. Key = caller-chosen name (e.g. "classic/1").
// ---------------------------------------------------------------------------
class MapRegistry {
public:
    // Load a map from disk under a name. Re-loading the same name re-reads disk
    // (use when the file changed); otherwise call get().
    const MapTemplate& load(const std::string& name, const std::string& path,
                            int expected_cols = 0, int expected_rows = 0) {
        cache_[name] = load_map_from_txt(path, expected_cols, expected_rows);
        return cache_.at(name);
    }

    bool has(const std::string& name) const {
        return cache_.find(name) != cache_.end();
    }

    const MapTemplate& get(const std::string& name) const {
        auto it = cache_.find(name);
        if (it == cache_.end())
            throw std::runtime_error("map_loader: map '" + name + "' not loaded");
        return it->second;
    }

    std::size_t size() const { return cache_.size(); }

private:
    std::unordered_map<std::string, MapTemplate> cache_;
};

}  // namespace bc