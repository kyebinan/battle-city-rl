// battle_city/cpp/include/battle_city/geometry.hpp


#pragma once

#include "battle_city/config.hpp"

namespace bc {

// ---------------------------------------------------------------------------
// BoundingBox -- axis-aligned box in pixel coordinates.
// x, y = top-left corner. w, h = size in pixels.
// ---------------------------------------------------------------------------

struct BoundingBox {
    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;

    constexpr int right()  const { return x + w; }
    constexpr int bottom() const { return y + h; }
    constexpr int cx()     const { return x + w / 2; }
    constexpr int cy()     const { return y + h / 2; }

    // AABB overlap test (matches Python BoundingBox.intersects).
    constexpr bool intersects(const BoundingBox& o) const {
        return x < o.right() && right() > o.x &&
               y < o.bottom() && bottom() > o.y;
    }

    constexpr bool contains_point(int px, int py) const {
        return x <= px && px < right() && y <= py && py < bottom();
    }

    constexpr BoundingBox moved(int dx, int dy) const {
        return BoundingBox{x + dx, y + dy, w, h};
    }

    constexpr bool operator==(const BoundingBox&) const = default;
};

// ---------------------------------------------------------------------------
// Position -- grid coordinate in 8px block units (col, row).
// ---------------------------------------------------------------------------

struct Position {
    int col = 0;
    int row = 0;

    constexpr Position operator+(const Position& o) const {
        return Position{col + o.col, row + o.row};
    }

    constexpr bool operator==(const Position&) const = default;

    // Top-left pixel coordinate of this block.
    constexpr int to_pixel_x(int block_px = config::BLOCK_PX) const {
        return col * block_px;
    }
    constexpr int to_pixel_y(int block_px = config::BLOCK_PX) const {
        return row * block_px;
    }

    static constexpr Position from_pixel(int x, int y,
                                         int block_px = config::BLOCK_PX) {
        return Position{x / block_px, y / block_px};
    }
};

}  // namespace bc