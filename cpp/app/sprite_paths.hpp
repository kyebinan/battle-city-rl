// cpp/app/sprite_paths.hpp
//
// Maps engine state -> asset file paths. Render-only (SDL app), NOT part of the
// headless engine. Keeps the path convention in one place.
//
// Conventions discovered from the assets tree:
//   tanks/allies/{color}/{star}/{dir}_{frame}.png   color: green|yellow, star 0..3
//   tanks/enemies/{type}/{shade}/{dir}_{frame}.png  type: basic|fast|power|armor
//   bullets/{dir}.png
//   eagle/0.png (alive)  eagle/1.png (destroyed)
//   tiles/{brick|steel|water|grass|ice}.png

#pragma once

#include "battle_city/config.hpp"
#include "battle_city/entities.hpp"
#include "battle_city/tilemap.hpp"

#include <string>

namespace bc::app {

inline const char* dir_name(config::Direction d) {
    switch (d) {
        case config::Direction::UP:    return "up";
        case config::Direction::RIGHT: return "right";
        case config::Direction::DOWN:  return "down";
        case config::Direction::LEFT:  return "left";
    }
    return "up";
}

inline std::string tank_sprite(const Tank& t, int anim_frame /*0|1*/, const std::string& assets) {
    const char* d = dir_name(t.direction);
    const int f = anim_frame & 1;
    if (t.is_player()) {
        const int star = static_cast<int>(t.star_level);  // 0..3
        return assets + "/sprites/tanks/allies/green/" + std::to_string(star) +
               "/" + d + "_" + std::to_string(f) + ".png";
    }
    // enemy: pick subfolder by type, shade grey by default
    const char* type = "basic";
    switch (t.type) {
        case config::TankType::FAST:  type = "fast";  break;
        case config::TankType::POWER: type = "power"; break;
        case config::TankType::ARMOR: type = "armor"; break;
        default:                      type = "basic"; break;
    }
    return assets + "/sprites/tanks/enemies/" + type + "/grey/" +
           d + "_" + std::to_string(f) + ".png";
}

inline std::string bullet_sprite(const Bullet& b, const std::string& assets) {
    return assets + "/sprites/bullets/" + dir_name(b.direction) + ".png";
}

inline std::string eagle_sprite(const Eagle& e, const std::string& assets) {
    return assets + "/sprites/eagle/" + (e.destroyed ? "1" : "0") + ".png";
}

inline const char* tile_sprite_name(TileType t) {
    switch (t) {
        case TileType::BRICK:  return "brick";
        case TileType::STEEL:  return "steel";
        case TileType::WATER:  return "water";
        case TileType::FOREST: return "grass";
        case TileType::ICE:    return "ice";
        default:               return nullptr;  // EMPTY -> no sprite
    }
}

}  // namespace bc::app