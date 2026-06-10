// battle_city/cpp/include/battle_city/world.hpp
//
// World -- the orchestrator. Owns a GameState and drives the fixed-order
// per-frame update. This is the surface the Python binding will wrap.
//
// reset(template): copy cached terrain, spawn eagle + allies + enemies.
// step(actions):   apply actions -> move -> collide -> cleanup -> terminal check.
//
// Action encoding (per controlled tank):
//   action = 0: idle (no move, no fire)
//   1..4    : move UP/RIGHT/DOWN/LEFT (face + move that direction)
//   5..8    : face UP/RIGHT/DOWN/LEFT without moving
//   +fire   : firing is a separate boolean per tank (see StepInput)
// Kept deliberately simple here; the Python/Gym layer can remap to its own
// action space. The engine just needs intent.

#pragma once

#include "battle_city/collision.hpp"
#include "battle_city/config.hpp"
#include "battle_city/entities.hpp"
#include "battle_city/game_state.hpp"
#include "battle_city/map_loader.hpp"
#include "battle_city/physics.hpp"

#include <cstdint>
#include <vector>

namespace bc {

// Intent for one controlled tank in a single step.
struct TankAction {
    config::Direction direction = config::Direction::UP;
    bool move = false;
    bool fire = false;
};

class World {
public:
    GameState gs;

    World() = default;
    explicit World(std::uint32_t seed) : gs(seed) {}

    // -----------------------------------------------------------------
    // reset: build a fresh episode from a cached MapTemplate.
    // allies/enemies spawned from the template's derived spawn points.
    // n_allies: how many ally tanks to place (1 or 2).
    // -----------------------------------------------------------------
    void reset(const MapTemplate& tmpl, int n_allies = 1) {
        // fresh state but keep the RNG stream (reproducible across resets)
        std::mt19937 saved_rng = gs.rng;
        gs = GameState();
        gs.rng = saved_rng;

        gs.map = tmpl.map;                       // the cache copy (memcpy)

        // eagle
        gs.eagle = Eagle{tmpl.eagle.x, tmpl.eagle.y,
                         config::TILE_PX, config::TILE_PX, false};

        // allies
        const int na = (n_allies < 1) ? 1 : (n_allies > (int)tmpl.ally_spawns.size()
                                             ? (int)tmpl.ally_spawns.size() : n_allies);
        for (int i = 0; i < na; ++i) {
            const SpawnPoint& sp = tmpl.ally_spawns[i];
            gs.spawn_tank(sp.x, sp.y, TankType::PLAYER, TankTeam::PLAYER, sp.direction);
        }

        // initial enemies: fill up to MAX_ENEMIES_ON_SCREEN from the 3 spots
        spawn_enemies_up_to_cap(tmpl);
    }

    // -----------------------------------------------------------------
    // step: advance one 60Hz frame.
    // actions[i] is the intent for ally tank i (in spawn order). Extra actions
    // are ignored; missing ones default to idle.
    // -----------------------------------------------------------------
    void step(const std::vector<TankAction>& actions) {
        if (gs.game_over) return;

        apply_actions(actions);

        // movement
        physics::move_all_tanks(gs);
        physics::move_all_bullets(gs);

        // collision resolution
        collision::resolve_all(gs);

        // timers
        physics::tick_all_timers(gs);

        // remove dead entities (swap-and-pop), then sync tank bullet counts
        gs.remove_dead();
        resync_bullet_counts();

        // terminal checks
        ++gs.frame;
        check_terminal();
    }

    bool done() const { return gs.game_over; }

private:
    // Map an action onto the i-th ALLY tank (player team), in vector order.
    void apply_actions(const std::vector<TankAction>& actions) {
        std::size_t ai = 0;
        for (auto& t : gs.tanks) {
            if (!t.is_player()) continue;
            if (ai < actions.size()) {
                const TankAction& a = actions[ai];
                t.direction = a.direction;
                t.moving = a.move;
                if (a.fire) try_fire(t);
            } else {
                t.moving = false;
            }
            ++ai;
        }
    }

    // Spawn a bullet for a tank if it has not hit its on-screen bullet cap.
    void try_fire(Tank& t) {
        if (!t.can_fire()) return;
        const BulletSpeed spd = t.is_player()
            ? t.bullet_speed()
            : BulletSpeed::SLOW;  // enemy speed refined by enemy AI later
        Bullet proto = make_bullet_from_tank(t, spd, t.can_destroy_steel());
        gs.spawn_bullet(proto);
        t.active_bullets += 1;
    }

    // Recompute each tank's active_bullets from the surviving bullet vector.
    // Simpler + always correct vs decrementing on every bullet death.
    void resync_bullet_counts() {
        for (auto& t : gs.tanks) t.active_bullets = 0;
        for (auto& b : gs.bullets) {
            for (auto& t : gs.tanks) {
                if (t.id == b.owner_id) { t.active_bullets += 1; break; }
            }
        }
    }

    // Count current live enemies; spawn from the 3 fixed spots up to the cap.
    void spawn_enemies_up_to_cap(const MapTemplate& tmpl) {
        int live_enemies = 0;
        for (auto& t : gs.tanks) if (t.is_enemy() && t.alive) ++live_enemies;

        std::size_t spot = 0;
        while (live_enemies < config::MAX_ENEMIES_ON_SCREEN &&
               spot < tmpl.enemy_spawns.size()) {
            const SpawnPoint& sp = tmpl.enemy_spawns[spot];
            // pick a simple enemy type for now; composition logic comes later
            gs.spawn_tank(sp.x, sp.y, TankType::BASIC, TankTeam::ENEMY, sp.direction);
            ++live_enemies;
            ++spot;
            gs.enemies_spawned += 1;
        }
    }

    void check_terminal() {
        // eagle already sets game_over in collision; also end if no allies left
        bool any_ally = false;
        for (auto& t : gs.tanks) if (t.is_player() && t.alive) { any_ally = true; break; }
        if (!any_ally) gs.game_over = true;
    }
};

}  // namespace bc