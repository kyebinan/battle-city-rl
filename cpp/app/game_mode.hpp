// cpp/app/game_mode.hpp
//
// App-level (front-end) description of the playable / visitable modes and a
// small helper to discover the map files that belong to each mode.
//
// This is intentionally a FRONT-END concern: the engine (bc::World) does not
// know about "modes". The app picks a mode, finds its map files, loads one,
// and decides whether to drive the engine (play) or freeze it (visit).
//
//   CLASSIC      assets/maps/classic/N.txt          26 x 26   PLAYABLE
//   ADVERSARIAL  assets/maps/custom/medium/N.txt     50 x 50   visit-only (for now)
//   BIG          assets/maps/custom/xlarge/NAME.txt  74 x 58   visit-only (for now)
//
// Map sizes are fixed PER MODE (cols x rows), matching the _model.txt templates.

#pragma once

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <string>
#include <vector>

namespace ui {

enum class GameMode : int {
    CLASSIC     = 0,
    ADVERSARIAL = 1,   // "medium" folder
    BIG         = 2,   // "xlarge" folder
    COUNT       = 3
};

// Static description of one mode.
struct ModeInfo {
    GameMode    mode;
    const char* label;        // shown in the menu
    const char* subfolder;    // relative to <assets>/maps/
    int         cols;
    int         rows;
    bool        playable;     // true => drive engine; false => frozen "visit"
};

// Order matches the menu order (index == int(GameMode)).
inline const ModeInfo& mode_info(GameMode m) {
    static const ModeInfo table[] = {
        { GameMode::CLASSIC,     "CLASSIC",     "classic",        26, 26, true  },
        { GameMode::ADVERSARIAL, "ADVERSARIAL", "custom/medium",  50, 50, false },
        { GameMode::BIG,         "BIG BATTLE",  "custom/xlarge",  74, 58, false },
    };
    return table[static_cast<int>(m)];
}

inline const ModeInfo& mode_info(int idx) {
    return mode_info(static_cast<GameMode>(idx));
}

// One discovered map file for a mode.
struct MapEntry {
    std::string display;   // what to show in the picker (full filename stem)
    std::string path;      // absolute/relative path to load
    int         number;    // leading integer in the filename, for sorting
};

// Pull the leading integer out of a filename stem like "2" or "13.bunker_rush".
// Returns a large number if there is no leading digit, so such files sort last.
inline int leading_number(const std::string& stem) {
    std::size_t i = 0;
    while (i < stem.size() && std::isdigit(static_cast<unsigned char>(stem[i]))) ++i;
    if (i == 0) return 1'000'000;
    return std::stoi(stem.substr(0, i));
}

// Discover the *.txt maps for a mode, skipping the "_model.txt" template.
// `assets_root` is the path that contains the "maps" directory (e.g. "assets").
// Sorted by the leading number; the display string keeps the full stem so the
// descriptive xlarge names ("steel_fortress_rings") remain visible.
inline std::vector<MapEntry> discover_maps(const std::string& assets_root,
                                           const ModeInfo& info) {
    namespace fs = std::filesystem;
    std::vector<MapEntry> out;

    const fs::path dir = fs::path(assets_root) / "maps" / info.subfolder;
    std::error_code ec;
    if (!fs::is_directory(dir, ec)) return out;   // empty => caller handles

    for (const auto& de : fs::directory_iterator(dir, ec)) {
        if (ec) break;
        if (!de.is_regular_file()) continue;
        const fs::path p = de.path();
        if (p.extension() != ".txt") continue;
        const std::string stem = p.stem().string();   // "1", "2.steel_fortress_rings"
        if (stem == "_model" || stem.empty() || stem[0] == '_') continue;

        out.push_back(MapEntry{ stem, p.string(), leading_number(stem) });
    }

    std::sort(out.begin(), out.end(), [](const MapEntry& a, const MapEntry& b) {
        if (a.number != b.number) return a.number < b.number;
        return a.display < b.display;
    });
    return out;
}

}  // namespace ui