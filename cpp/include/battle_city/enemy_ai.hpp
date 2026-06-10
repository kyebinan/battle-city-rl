// battle_city/cpp/include/battle_city/enemy_ai.hpp
//
// Simple scripted enemy policy -- NOT a behaviour tree yet, just enough to make
// the game move so it can be watched/played. Pure C++, uses the per-state RNG
// so behaviour stays deterministic for a given seed.
//
// Per enemy tank each frame: always moving; retarget direction on a jittered
// interval (biased toward the eagle); fire on a phase-shifted cooldown.
// This only sets intent (direction/moving) + calls a fire callback -- movement
// is done by physics::move_tank, same contract as player actions.

#pragma once

#include "battle_city/config.hpp"
#include "battle_city/entities.hpp"
#include "battle_city/game_state.hpp"

#include <cstdlib>
#include <random>

namespace bc::ai {

inline constexpr int RETARGET_INTERVAL = 32;
inline constexpr int FIRE_COOLDOWN     = 45;
inline constexpr int EAGLE_BIAS_PCT    = 55;

inline config::Direction toward_eagle(const Tank& t, const Eagle& e,
                                      std::mt19937& rng) {
    const int dx = e.x - t.x;
    const int dy = e.y - t.y;
    const bool horiz = (std::abs(dx) > std::abs(dy)) ||
                       (std::abs(dx) == std::abs(dy) && (rng() & 1u));
    if (horiz) return dx > 0 ? config::Direction::RIGHT : config::Direction::LEFT;
    return dy > 0 ? config::Direction::DOWN : config::Direction::UP;
}

inline config::Direction random_dir(std::mt19937& rng) {
    return static_cast<config::Direction>(rng() % 4u);
}

template <typename FireFn>
inline void drive_enemies(GameState& gs, FireFn&& fire_fn) {
    for (auto& t : gs.tanks) {
        if (!t.alive || !t.is_enemy()) continue;

        const int phase = (gs.frame + t.id) % RETARGET_INTERVAL;
        if (phase == 0) {
            if (static_cast<int>(gs.rng() % 100u) < EAGLE_BIAS_PCT)
                t.direction = toward_eagle(t, gs.eagle, gs.rng);
            else
                t.direction = random_dir(gs.rng);
        }
        t.moving = true;

        const int fphase = (gs.frame + t.id) % FIRE_COOLDOWN;
        if (fphase == 0)
            fire_fn(t);
    }
}

}  // namespace bc::ai