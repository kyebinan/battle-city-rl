// cpp/app/menu.hpp
//
// Front-end screens: the mode menu and the per-mode map picker. Pure UI +
// input state; it does NOT touch the engine. main.cpp owns the transitions.
//
// Visual style: black background, big centered title, a vertical list with a
// blinking ">" selector on the active row (classic NES menu feel).
//
// Navigation: Up/Down move, Enter confirms, Esc backs out (handled by caller).

#pragma once

#include "game_mode.hpp"
#include "text.hpp"

#include <SDL.h>
#include <string>
#include <vector>

namespace ui {

// NES palette-ish colors.
inline constexpr SDL_Color COL_WHITE  {236, 236, 236, 255};
inline constexpr SDL_Color COL_GREY   {120, 120, 120, 255};
inline constexpr SDL_Color COL_YELLOW {228, 196,  48, 255};
inline constexpr SDL_Color COL_RED    {200,  40,  40, 255};

// A generic vertical list selector with a blinking arrow.
class ListMenu {
public:
    void set_items(std::vector<std::string> items) {
        items_ = std::move(items);
        if (selected_ >= (int)items_.size()) selected_ = 0;
    }
    int  size()     const { return (int)items_.size(); }
    int  selected() const { return selected_; }
    bool empty()    const { return items_.empty(); }

    void move_up()   { if (!items_.empty()) selected_ = (selected_ + size() - 1) % size(); }
    void move_down() { if (!items_.empty()) selected_ = (selected_ + 1) % size(); }

    // Render the list centered horizontally at center_x, starting at top_y.
    // `blink` toggles the selector visibility (caller passes a frame-based bool).
    void render(SDL_Renderer* ren, const TextRenderer& text,
                int center_x, int top_y, int row_h, int scale, bool blink) const {
        for (int i = 0; i < size(); ++i) {
            const bool sel = (i == selected_);
            const SDL_Color col = sel ? COL_YELLOW : COL_GREY;
            const int y = top_y + i * row_h;
            text.draw(ren, items_[i], center_x, y, col, scale, Align::CENTER);
            if (sel && blink) {
                // selector arrow to the left of the (centered) row
                const int half = text.measure(items_[i], scale) / 2;
                text.draw(ren, ">", center_x - half - 6 * scale, y,
                          COL_WHITE, scale, Align::RIGHT);
            }
        }
    }

private:
    std::vector<std::string> items_;
    int selected_ = 0;
};

// The top-level mode menu. Items are the mode labels in enum order.
class ModeMenu {
public:
    ModeMenu() {
        std::vector<std::string> labels;
        for (int i = 0; i < (int)GameMode::COUNT; ++i)
            labels.push_back(mode_info(i).label);
        list_.set_items(std::move(labels));
    }

    void up()   { list_.move_up(); }
    void down() { list_.move_down(); }
    GameMode selected_mode() const { return static_cast<GameMode>(list_.selected()); }

    void render(SDL_Renderer* ren, const TextRenderer& text,
                int win_w, int win_h, bool blink) const {
        const int cx = win_w / 2;
        text.draw(ren, "BATTLE CITY", cx, win_h / 6, COL_RED, 4, Align::CENTER);
        list_.render(ren, text, cx, win_h / 2 - 40, 48, 3, blink);
        text.draw(ren, "ARROWS MOVE   ENTER SELECT", cx, win_h - 60,
                  COL_GREY, 2, Align::CENTER);
    }

private:
    ListMenu list_;
};

// The map picker for a chosen mode.
class MapMenu {
public:
    void set(const ModeInfo& info, std::vector<MapEntry> maps) {
        info_  = &info;
        maps_  = std::move(maps);
        std::vector<std::string> labels;
        for (const auto& m : maps_) labels.push_back(m.display);
        list_.set_items(std::move(labels));
    }

    bool empty() const { return maps_.empty(); }
    void up()   { list_.move_up(); }
    void down() { list_.move_down(); }
    const MapEntry& selected_map() const { return maps_[list_.selected()]; }

    void render(SDL_Renderer* ren, const TextRenderer& text,
                int win_w, int win_h, bool blink) const {
        const int cx = win_w / 2;
        const std::string head = info_ ? std::string(info_->label) + " MAPS" : "MAPS";
        text.draw(ren, head, cx, win_h / 8, COL_WHITE, 3, Align::CENTER);

        // Show a windowed slice if the list is long, so it never overflows.
        const int row_h = 28;
        const int max_rows = (win_h * 3 / 5) / row_h;
        const int sel = list_.selected();
        int start = 0;
        if (list_.size() > max_rows) {
            start = sel - max_rows / 2;
            if (start < 0) start = 0;
            if (start > list_.size() - max_rows) start = list_.size() - max_rows;
        }
        const int top_y = win_h / 4;
        for (int i = start; i < list_.size() && i < start + max_rows; ++i) {
            const bool s = (i == sel);
            const SDL_Color col = s ? COL_YELLOW : COL_GREY;
            const int y = top_y + (i - start) * row_h;
            text.draw(ren, maps_[i].display, cx, y, col, 2, Align::CENTER);
            if (s && blink) {
                const int half = text.measure(maps_[i].display, 2) / 2;
                text.draw(ren, ">", cx - half - 12, y, COL_WHITE, 2, Align::RIGHT);
            }
        }
        text.draw(ren, "ENTER LOAD   ESC BACK", cx, win_h - 50,
                  COL_GREY, 2, Align::CENTER);
    }

private:
    const ModeInfo* info_ = nullptr;
    std::vector<MapEntry> maps_;
    ListMenu list_;
};

}  // namespace ui