// battle_city/cpp/include/battle_city/physics.hpp


#pragma once

#include "battle_city/config.hpp"
#include "battle_city/entities.hpp"
#include "battle_city/game_state.hpp"
#include "battle_city/geometry.hpp"
#include "battle_city/tilemap.hpp"

namespace bc::physics {

// ---------------------------------------------------------------------------
// Tile coverage: does a pixel bbox have all covered blocks passable for a tank?
// A 16px tank at an unaligned pixel offset straddles up to 4 blocks (8px each).
// We test EVERY block the bbox overlaps. Block move if any is non-passable.
// ---------------------------------------------------------------------------

inline bool tank_bbox_passable(const TileMap& map, const BoundingBox& box) {
    const int s = map.block_px;
    // Blocks overlapped by [x, right) x [y, bottom). right/bottom exclusive,
    // so subtract 1 px to get the last inside block.
    const int c0 = box.x / s;
    const int r0 = box.y / s;
    const int c1 = (box.right()  - 1) / s;
    const int r1 = (box.bottom() - 1) / s;
    for (int r = r0; r <= r1; ++r)
        for (int c = c0; c <= c1; ++c)
            if (!map.is_passable_for_tank(Position{c, r}))
                return false;
    return true;
}

// Any block under the bbox slippery? (tank standing on ice)
inline bool tank_on_ice(const TileMap& map, const BoundingBox& box) {
    const int s = map.block_px;
    const int c0 = box.x / s;
    const int r0 = box.y / s;
    const int c1 = (box.right()  - 1) / s;
    const int r1 = (box.bottom() - 1) / s;
    for (int r = r0; r <= r1; ++r)
        for (int c = c0; c <= c1; ++c)
            if (map.is_slippery(Position{c, r}))
                return true;
    return false;
}

// ---------------------------------------------------------------------------
// Tank-vs-tank: would moved-box overlap any OTHER live tank?
// ---------------------------------------------------------------------------

inline bool overlaps_other_tank(const GameState& gs, std::size_t self_idx,
                                const BoundingBox& box) {
    for (std::size_t i = 0; i < gs.tanks.size(); ++i) {
        if (i == self_idx) continue;
        if (!gs.tanks[i].alive) continue;
        if (box.intersects(gs.tanks[i].bbox()))
            return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// Move one tank one frame. Returns true if it actually moved.
// Rules:
//   - tank moves speed_px in its direction when intending to move OR sliding.
//   - movement blocked if target overlaps non-passable terrain or another tank.
//   - stepping onto ice arms the slide timer.
//   - while sliding (timer > 0) the tank keeps moving even without intent.
// ---------------------------------------------------------------------------

inline bool move_tank(GameState& gs, std::size_t idx) {
    Tank& t = gs.tanks[idx];
    if (!t.alive) return false;

    const bool wants_move = t.moving || t.sliding();
    if (!wants_move) return false;

    const config::Delta d = config::direction_delta(t.direction);
    const int dx = d.dcol * t.speed_px();
    const int dy = d.drow * t.speed_px();
    if (dx == 0 && dy == 0) return false;

    const BoundingBox target = t.bbox().moved(dx, dy);

    // Bounds: target must stay fully inside the map (right/bottom exclusive).
    if (target.x < 0 || target.y < 0 ||
        target.right()  > gs.map.pixel_width() ||
        target.bottom() > gs.map.pixel_height())
        return false;

    if (!tank_bbox_passable(gs.map, target)) return false;
    if (overlaps_other_tank(gs, idx, target)) return false;

    t.x += dx;
    t.y += dy;

    // Arm slide if the tank now stands on ice.
    if (tank_on_ice(gs.map, t.bbox()))
        t.slide_frames = config::ICE_SLIDE_FRAMES;

    return true;
}

// ---------------------------------------------------------------------------
// Move one bullet one frame. Bullets travel straight; collision resolution
// (wall/tank/eagle) is a SEPARATE system (collision.hpp), run after movement.
// ---------------------------------------------------------------------------

inline void move_bullet(Bullet& b) {
    if (!b.alive) return;
    const config::Delta d = config::direction_delta(b.direction);
    b.x += d.dcol * b.speed_px;
    b.y += d.drow * b.speed_px;
}

// ---------------------------------------------------------------------------
// Per-frame timer tick for one tank (invincibility + slide countdown).
// Port of Tank._on_update.
// ---------------------------------------------------------------------------

inline void tick_tank_timers(Tank& t) {
    if (t.invincible_frames > 0) --t.invincible_frames;
    if (t.slide_frames > 0)      --t.slide_frames;
}

// ---------------------------------------------------------------------------
// System sweeps: apply to whole vectors. These are the parallel-friendly loops.
// ---------------------------------------------------------------------------

inline void move_all_tanks(GameState& gs) {
    for (std::size_t i = 0; i < gs.tanks.size(); ++i)
        move_tank(gs, i);
}

inline void move_all_bullets(GameState& gs) {
    for (auto& b : gs.bullets)
        move_bullet(b);
}

inline void tick_all_timers(GameState& gs) {
    for (auto& t : gs.tanks)
        tick_tank_timers(t);
}

}  // namespace bc::physics