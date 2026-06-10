// battle_city/cpp/include/battle_city/collision.hpp
//
// Collision resolution systems -- free functions on GameState&.
// Run AFTER movement each frame. Port of the rules in "Battle city rules.md"
// + take_hit logic from tank.py.
//
// Resolves, per live bullet:
//   1. out of bounds        -> bullet dies
//   2. bullet vs bullet     -> mutual cancel
//   3. bullet vs eagle      -> eagle destroyed, game over
//   4. bullet vs wall       -> brick destroyed (multi-block), steel if 3-star
//   5. bullet vs tank       -> take_hit (star downgrade vs death), scoring
//
// NOT here (clean hooks left): power-up spawn on flash-tank hit, friendly-fire
// freeze timer, helmet/clock/grenade effects. Those belong to a power-up system.

#pragma once

#include "battle_city/config.hpp"
#include "battle_city/entities.hpp"
#include "battle_city/game_state.hpp"
#include "battle_city/geometry.hpp"
#include "battle_city/tilemap.hpp"

namespace bc::collision {

// ---------------------------------------------------------------------------
// take_hit -- apply one hit to a tank. Returns true if destroyed.
// Player: star_level > BASE downgrades (survives); else HP-- then maybe die.
// Enemy: HP-- then maybe die. (Port of Tank.take_hit.)
// ---------------------------------------------------------------------------
inline bool take_hit(Tank& t) {
    if (t.is_player() && t.star_level > config::StarLevel::BASE) {
        t.star_level = static_cast<config::StarLevel>(
            static_cast<int>(t.star_level) - 1);
        return false;
    }
    --t.hp;
    if (t.hp <= 0) {
        t.alive = false;
        return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// Brick impact: a bullet hitting brick destroys 1 or 2 blocks depending on the
// sub-pixel offset perpendicular to travel (NES "4 shots to clear a width").
// We destroy the block(s) the bullet front overlaps, using the config zone.
// ---------------------------------------------------------------------------
inline void resolve_bullet_vs_wall(GameState& gs, Bullet& b) {
    const TileMap& cmap = gs.map;
    const int s = cmap.block_px;

    // The leading point of the bullet in its travel direction.
    const config::Delta d = config::direction_delta(b.direction);
    int front_x = b.x;
    int front_y = b.y;
    if (d.dcol > 0) front_x = b.bbox().right() - 1;
    if (d.dcol < 0) front_x = b.x;
    if (d.drow > 0) front_y = b.bbox().bottom() - 1;
    if (d.drow < 0) front_y = b.y;

    const Position hit = cmap.position_from_pixel(front_x, front_y);

    if (!gs.map.in_bounds(hit)) { b.alive = false; return; }
    const TileType tile = gs.map.get(hit);

    // Bullets pass through tiles that are bullet-passable (empty/water/forest).
    if (tile_properties(tile).passable_bullet) return;

    // Steel: only a 3-star (destroys_steel) bullet breaks it; else just stops.
    if (tile == TileType::STEEL) {
        if (b.destroys_steel) gs.map.set(hit, TileType::EMPTY);
        b.alive = false;
        return;
    }

    // Brick: destroy the hit block, plus a neighbour if the bullet straddles
    // the boundary (multi-block zone). Perpendicular axis = across travel.
    if (tile == TileType::BRICK) {
        gs.map.destroy(hit);

        // Sub-pixel offset within the 8px block, perpendicular to travel.
        const bool vertical = (d.drow != 0);
        const int perp = vertical ? (b.x % s) : (b.y % s);
        if (perp >= config::IMPACT_MULTI_BLOCK_LOW &&
            perp <= config::IMPACT_MULTI_BLOCK_HIGH) {
            // straddles -> also destroy the adjacent block along perp axis
            Position adj = vertical ? Position{hit.col + 1, hit.row}
                                    : Position{hit.col, hit.row + 1};
            gs.map.destroy(adj);
        }
        b.alive = false;
        return;
    }

    // Any other non-passable tile: stop the bullet.
    b.alive = false;
}

// ---------------------------------------------------------------------------
// Eagle: any bullet reaching the eagle ends the game.
// ---------------------------------------------------------------------------
inline bool resolve_bullet_vs_eagle(GameState& gs, Bullet& b) {
    if (gs.eagle.destroyed) return false;
    if (!b.bbox().intersects(gs.eagle.bbox())) return false;
    gs.eagle.destroyed = true;
    b.alive = false;
    gs.game_over = true;
    return true;
}

// ---------------------------------------------------------------------------
// Tank: a bullet hits a tank if bboxes overlap, with the rule filters:
//   - a bullet never hits its own owner
//   - enemy bullets cannot damage other enemy tanks
//   - invincible tanks ignore hits (bullet still dies)
//   - friendly fire (player bullet vs player tank) -> NO damage (freeze hook)
// Returns index of a destroyed tank, or -1.
// ---------------------------------------------------------------------------
inline void resolve_bullet_vs_tanks(GameState& gs, Bullet& b) {
    for (auto& t : gs.tanks) {
        if (!t.alive) continue;
        if (t.id == b.owner_id) continue;                 // never self-hit
        if (!b.bbox().intersects(t.bbox())) continue;

        const bool bullet_is_player = (b.owner_team == config::BulletOwner::PLAYER);

        // Enemy bullet cannot damage enemy tank.
        if (!bullet_is_player && t.is_enemy()) continue;

        // Friendly fire: player bullet vs player tank -> no kill (freeze hook).
        if (bullet_is_player && t.is_player()) {
            b.alive = false;                              // bullet still spent
            // TODO(powerups): apply freeze timer to t here.
            return;
        }

        // Invincible target: bullet is spent, no damage.
        if (t.invincible()) {
            b.alive = false;
            return;
        }

        // Valid damaging hit.
        const bool destroyed = take_hit(t);
        b.alive = false;

        if (destroyed && t.is_enemy()) {
            gs.score += config::tank_points(t.type);
            gs.enemies_killed += 1;
            // TODO(powerups): if this was a flash tank, spawn a power-up.
        }
        return;
    }
}

// ---------------------------------------------------------------------------
// Bullet vs bullet: opposing bullets that overlap cancel each other.
// ---------------------------------------------------------------------------
inline void resolve_bullet_vs_bullets(GameState& gs) {
    const std::size_t n = gs.bullets.size();
    for (std::size_t i = 0; i < n; ++i) {
        if (!gs.bullets[i].alive) continue;
        for (std::size_t j = i + 1; j < n; ++j) {
            if (!gs.bullets[j].alive) continue;
            if (gs.bullets[i].bbox().intersects(gs.bullets[j].bbox())) {
                gs.bullets[i].alive = false;
                gs.bullets[j].alive = false;
                break;  // i is dead; move on
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Full collision pass for one frame. Order: bullet-bullet, then per bullet
// eagle -> wall -> tanks. Eagle first so a game-over bullet can't be "absorbed"
// by a wall in the same frame.
// ---------------------------------------------------------------------------
inline void resolve_all(GameState& gs) {
    resolve_bullet_vs_bullets(gs);

    for (auto& b : gs.bullets) {
        if (!b.alive) continue;

        // out of bounds
        if (b.bbox().right() <= 0 || b.x >= gs.map.pixel_width() ||
            b.bbox().bottom() <= 0 || b.y >= gs.map.pixel_height()) {
            b.alive = false;
            continue;
        }

        if (resolve_bullet_vs_eagle(gs, b)) continue;
        resolve_bullet_vs_wall(gs, b);
        if (!b.alive) continue;
        resolve_bullet_vs_tanks(gs, b);
    }
}

}  // namespace bc::collision