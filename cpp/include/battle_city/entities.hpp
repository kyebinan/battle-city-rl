// battle_city/cpp/include/battle_city/entities.hpp

#pragma once

#include "battle_city/config.hpp"
#include "battle_city/geometry.hpp"

#include <cstdint>

namespace bc {

using config::Direction;
using config::TankType;
using config::TankTeam;
using config::StarLevel;
using config::BulletOwner;
using config::BulletSpeed;

// ---------------------------------------------------------------------------
// Tank
// ---------------------------------------------------------------------------
struct Tank {
    std::int32_t id = 0;

    std::int32_t x = 0;
    std::int32_t y = 0;
    std::int32_t w = config::TANK_PX;
    std::int32_t h = config::TANK_PX;

    TankType  type      = TankType::BASIC;
    TankTeam  team      = TankTeam::ENEMY;
    Direction direction = Direction::UP;

    std::int32_t hp         = 1;
    StarLevel    star_level = StarLevel::BASE;

    std::int32_t invincible_frames = config::SPAWN_INVINCIBLE_FRAMES;
    std::int32_t slide_frames      = 0;

    bool moving = false;

    // Count of bullets this tank has on screen (the max-bullets rule only ever
    // needed the count, not the ids).
    std::int32_t active_bullets = 0;

    bool alive = true;

    // ----- pure accessors -----
    constexpr bool is_player() const { return team == TankTeam::PLAYER; }
    constexpr bool is_enemy()  const { return team == TankTeam::ENEMY; }
    constexpr BoundingBox bbox() const { return BoundingBox{x, y, w, h}; }
    constexpr int speed_px() const { return config::tank_speed_px(type); }
    constexpr bool invincible() const { return invincible_frames > 0; }
    constexpr bool sliding()    const { return slide_frames > 0; }
    constexpr BulletSpeed bullet_speed() const {
        return config::star_bullet_speed(star_level);
    }
    constexpr int max_bullets() const {
        return is_player() ? config::star_max_bullets(star_level) : 1;
    }
    constexpr bool can_destroy_steel() const {
        return is_player() && config::star_destroys_steel(star_level);
    }
    constexpr bool can_fire() const { return active_bullets < max_bullets(); }
    constexpr bool flashing() const {
        if (!invincible()) return false;
        return (invincible_frames % (config::SPAWN_FLASH_INTERVAL * 2))
               < config::SPAWN_FLASH_INTERVAL;
    }
};

// ---------------------------------------------------------------------------
// Bullet
// ---------------------------------------------------------------------------
struct Bullet {
    std::int32_t id = 0;

    std::int32_t x = 0;
    std::int32_t y = 0;
    std::int32_t w = config::BULLET_W_PX;
    std::int32_t h = config::BULLET_H_PX;

    Direction    direction  = Direction::UP;
    std::int32_t owner_id   = 0;
    BulletOwner  owner_team  = BulletOwner::ENEMY;
    std::int32_t speed_px   = config::bullet_speed_px(BulletSpeed::SLOW);
    bool         destroys_steel = false;

    bool alive = true;

    constexpr BoundingBox bbox() const { return BoundingBox{x, y, w, h}; }
    constexpr bool is_player_bullet() const { return owner_team == BulletOwner::PLAYER; }
    constexpr bool is_enemy_bullet()  const { return owner_team == BulletOwner::ENEMY; }
};

// Factory: compute a bullet's initial geometry from the firing tank, centred on
// the barrel tip (port of Bullet.from_tank). The owning system assigns the id.
inline Bullet make_bullet_from_tank(const Tank& t, BulletSpeed speed, bool destroys_steel) {
    Bullet b;
    b.direction = t.direction;
    b.owner_id  = t.id;
    b.owner_team = t.is_player() ? BulletOwner::PLAYER : BulletOwner::ENEMY;
    b.speed_px  = config::bullet_speed_px(speed);
    b.destroys_steel = destroys_steel;

    const bool vertical = (t.direction == Direction::UP || t.direction == Direction::DOWN);
    b.w = vertical ? config::BULLET_W_PX : config::BULLET_H_PX;
    b.h = vertical ? config::BULLET_H_PX : config::BULLET_W_PX;

    const int cx = t.x + t.w / 2;
    const int cy = t.y + t.h / 2;

    switch (t.direction) {
        case Direction::UP:    b.x = cx - b.w / 2; b.y = t.y - b.h;    break;
        case Direction::DOWN:  b.x = cx - b.w / 2; b.y = t.y + t.h;    break;
        case Direction::LEFT:  b.x = t.x - b.w;    b.y = cy - b.h / 2; break;
        case Direction::RIGHT: b.x = t.x + t.w;    b.y = cy - b.h / 2; break;
    }
    return b;
}

// ---------------------------------------------------------------------------
// Eagle (exactly one per GameState; stored as a single value, not a vector)
// ---------------------------------------------------------------------------
struct Eagle {
    std::int32_t x = 0;
    std::int32_t y = 0;
    std::int32_t w = config::TILE_PX;
    std::int32_t h = config::TILE_PX;
    bool destroyed = false;

    constexpr BoundingBox bbox() const { return BoundingBox{x, y, w, h}; }
};

}  // namespace bc