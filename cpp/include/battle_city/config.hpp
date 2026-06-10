// battle_city/cpp/include/battle_city/config.hpp

#pragma once

#include <cstdint>

namespace bc::config {

// ---------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------

inline constexpr int FPS         = 60;  // physics / game loop tick rate
inline constexpr int BLOCK_PX    = 8;   // one grid cell in pixels
inline constexpr int TILE_PX     = 16;  // one logical tile = 2x2 blocks
inline constexpr int TANK_PX     = 16;  // tank sprite size
inline constexpr int BULLET_W_PX = 4;   // bullet width
inline constexpr int BULLET_H_PX = 8;   // bullet height (vertical orientation)

// ---------------------------------------------------------------------------
// Direction
// ---------------------------------------------------------------------------

enum class Direction : std::uint8_t {
    UP    = 0,
    RIGHT = 1,
    DOWN  = 2,
    LEFT  = 3,
};

// Direction -> (dcol, drow) movement delta in block units.
struct Delta { int dcol; int drow; };

inline constexpr Delta direction_delta(Direction d) {
    switch (d) {
        case Direction::UP:    return { 0, -1};
        case Direction::RIGHT: return { 1,  0};
        case Direction::DOWN:  return { 0,  1};
        case Direction::LEFT:  return {-1,  0};
    }
    return {0, 0};  // unreachable; silences compiler warning
}

// ---------------------------------------------------------------------------
// Tank types
// ---------------------------------------------------------------------------

enum class TankType : std::uint8_t {
    PLAYER = 0,  // ally -- can receive Star upgrades and power-ups
    BASIC  = 1,  // enemy -- slow speed, slow bullet, 1 HP
    FAST   = 2,  // enemy -- fast speed, slow bullet, 1 HP
    POWER  = 3,  // enemy -- slow speed, fast bullet, 1 HP
    ARMOR  = 4,  // enemy -- slow speed, fast bullet, 4 HP
};

enum class TankTeam : std::uint8_t {
    PLAYER = 0,
    ENEMY  = 1,
};

// Tank movement speed in pixels per frame (at 60 FPS).
inline constexpr int tank_speed_px(TankType t) {
    switch (t) {
        case TankType::PLAYER: return 1;
        case TankType::BASIC:  return 1;
        case TankType::FAST:   return 2;
        case TankType::POWER:  return 1;
        case TankType::ARMOR:  return 1;
    }
    return 1;
}

// Tank HP (armor takes 4 hits).
inline constexpr int tank_hp(TankType t) {
    switch (t) {
        case TankType::PLAYER: return 1;
        case TankType::BASIC:  return 1;
        case TankType::FAST:   return 1;
        case TankType::POWER:  return 1;
        case TankType::ARMOR:  return 4;
    }
    return 1;
}

// Points awarded when an enemy tank is destroyed.
inline constexpr int tank_points(TankType t) {
    switch (t) {
        case TankType::BASIC: return 100;
        case TankType::FAST:  return 200;
        case TankType::POWER: return 300;
        case TankType::ARMOR: return 400;
        default:              return 0;  // PLAYER awards no points
    }
}

inline constexpr int MAX_ENEMIES_ON_SCREEN = 4;

// Flash tank spawn indices -- 4th, 11th, 18th enemy carry a power-up.
inline constexpr int FLASH_TANK_INDICES[3] = {3, 10, 17};

inline constexpr bool is_flash_tank_index(int idx) {
    for (int fi : FLASH_TANK_INDICES)
        if (fi == idx) return true;
    return false;
}

// ---------------------------------------------------------------------------
// Bullet
// ---------------------------------------------------------------------------

enum class BulletOwner : std::uint8_t {
    PLAYER = 0,
    ENEMY  = 1,
};

enum class BulletSpeed : std::uint8_t {
    SLOW = 0,  // basic / fast enemy tanks, player base bullet
    FAST = 1,  // power / armor enemy tanks, player 1-star+ bullet
};

inline constexpr int bullet_speed_px(BulletSpeed s) {
    switch (s) {
        case BulletSpeed::SLOW: return 4;
        case BulletSpeed::FAST: return 8;
    }
    return 4;
}

inline constexpr int MAX_BULLET_POWER   = 3;  // maximum star level
inline constexpr int MAX_BULLETS_SCREEN = 2;  // max player bullets at star 2+

// ---------------------------------------------------------------------------
// Player upgrade levels (Star power-up)
// Star upgrades affect bullets only -- movement speed never changes.
// ---------------------------------------------------------------------------

enum class StarLevel : std::uint8_t {
    BASE   = 0,  // slow bullet, 1 bullet max
    STAR_1 = 1,  // fast bullet, 1 bullet max
    STAR_2 = 2,  // fast bullet, 2 bullets on screen
    STAR_3 = 3,  // fast bullet, 2 bullets, destroys steel
};

inline constexpr BulletSpeed star_bullet_speed(StarLevel s) {
    return s == StarLevel::BASE ? BulletSpeed::SLOW : BulletSpeed::FAST;
}

inline constexpr int star_max_bullets(StarLevel s) {
    return (s == StarLevel::STAR_2 || s == StarLevel::STAR_3) ? 2 : 1;
}

inline constexpr bool star_destroys_steel(StarLevel s) {
    return s == StarLevel::STAR_3;
}

// ---------------------------------------------------------------------------
// Power-ups
// ---------------------------------------------------------------------------

enum class PowerUpType : std::uint8_t {
    STAR    = 0,  // upgrade player bullet
    HELMET  = 1,  // temporary invincibility
    GRENADE = 2,  // destroy all enemies on screen (no points)
    CLOCK   = 3,  // freeze all enemies
    SHOVEL  = 4,  // fortify eagle with steel (temporary)
    TANK    = 5,  // extra life (1-UP)
};

inline constexpr int POWERUP_POINTS = 500;  // collecting any power-up = +500

// Duration of timed power-ups in frames (0 = not a timed power-up).
inline constexpr int powerup_duration_frames(PowerUpType p) {
    switch (p) {
        case PowerUpType::HELMET: return 60 * 10;  // 10s invincibility
        case PowerUpType::CLOCK:  return 60 * 10;  // 10s freeze
        case PowerUpType::SHOVEL: return 60 * 20;  // 20s steel eagle
        default:                  return 0;
    }
}

// ---------------------------------------------------------------------------
// Scoring / lives
// ---------------------------------------------------------------------------

inline constexpr int EXTRA_LIFE_SCORE = 20000;  // threshold for an extra life
inline constexpr int STARTING_LIVES   = 3;

// ---------------------------------------------------------------------------
// Spawn invincibility
// ---------------------------------------------------------------------------

inline constexpr int SPAWN_INVINCIBLE_FRAMES = 60 * 3;  // 3s after respawn
inline constexpr int SPAWN_FLASH_INTERVAL    = 4;       // flash every N frames

// ---------------------------------------------------------------------------
// Ice physics
// ---------------------------------------------------------------------------

inline constexpr int ICE_SLIDE_FRAMES = 16;  // frames a tank slides on ice

// ---------------------------------------------------------------------------
// Bullet impact zones (sub-pixel offset thresholds)
// ---------------------------------------------------------------------------

inline constexpr int IMPACT_MULTI_BLOCK_LOW  = 3;
inline constexpr int IMPACT_MULTI_BLOCK_HIGH = 5;

}  // namespace bc::config