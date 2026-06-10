// battle_city/cpp/include/battle_city/game_state.hpp

#pragma once

#include "battle_city/config.hpp"
#include "battle_city/entities.hpp"
#include "battle_city/tilemap.hpp"

#include <cstdint>
#include <random>
#include <vector>

namespace bc {

struct GameState {
    // ----- terrain -----
    TileMap map;

    // ----- entities (each type its own contiguous vector) -----
    std::vector<Tank>   tanks;
    std::vector<Bullet> bullets;
    Eagle               eagle;

    // ----- scalar game state -----
    std::int32_t score          = 0;
    std::int32_t lives          = config::STARTING_LIVES;
    std::int32_t frame          = 0;
    std::int32_t enemies_killed = 0;
    std::int32_t enemies_spawned = 0;   // running count -> drives flash-tank rule
    bool         game_over      = false;

    // ----- id source (local to this state) -----
    std::int32_t next_id = 1;

    // ----- per-state RNG (reproducible) -----
    std::mt19937 rng;

    GameState() : rng(0) {}
    explicit GameState(std::uint32_t seed) : rng(seed) {}

    std::int32_t alloc_id() { return next_id++; }

    // Reserve to avoid reallocation during a step (100-entity custom game).
    void reserve(std::size_t max_tanks, std::size_t max_bullets) {
        tanks.reserve(max_tanks);
        bullets.reserve(max_bullets);
    }

    // ----- spawning -----
    // Return INDEX, not reference: push_back may reallocate the vector and
    // invalidate any held reference/pointer. Index stays valid until removal.
    std::size_t spawn_tank(int x, int y, TankType type, TankTeam team, Direction dir = Direction::UP) {
        Tank t;
        t.id = alloc_id();
        t.x = x; t.y = y;
        t.type = type; t.team = team; t.direction = dir;
        t.hp = config::tank_hp(type);
        tanks.push_back(t);
        return tanks.size() - 1;
    }

    std::size_t spawn_bullet(const Bullet& proto) {
        bullets.push_back(proto);
        bullets.back().id = alloc_id();
        return bullets.size() - 1;
    }

    // ----- swap-and-pop cleanup -----
    // Remove every entity with alive==false. O(n), no element shifting.
    void remove_dead() {
        remove_dead_vec(tanks);
        remove_dead_vec(bullets);
    }

private:
    template <typename T>
    static void remove_dead_vec(std::vector<T>& v) {
        std::size_t i = 0;
        while (i < v.size()) {
            if (v[i].alive) {
                ++i;
            } else {
                v[i] = v.back();   // overwrite hole with last element
                v.pop_back();      // shrink; do NOT advance i (re-check moved elt)
            }
        }
    }
};

}  // namespace bc