// cpp/app/main.cpp
//
// Standalone SDL2 player for the Battle City engine. Now wrapped in a small
// app state machine:
//
//   MENU       pick a mode (CLASSIC / ADVERSARIAL / BIG BATTLE)
//   MAP_SELECT pick which map within that mode
//   PLAYING    CLASSIC: drive the engine (real game)
//   VISITING   ADVERSARIAL/BIG: load + render the map, engine FROZEN (look only)
//
// Esc: in game/visit -> back to MENU; in MENU -> quit.
//
// Controls (PLAYING): Arrows = move player 0, Space = fire, R = reset map.
//
// Build: links SDL2, SDL2_image, SDL2_mixer, SDL2_ttf.

#include "battle_city/world.hpp"
#include "battle_city/map_loader.hpp"
#include "sprite_paths.hpp"

#include "game_mode.hpp"
#include "text.hpp"
#include "menu.hpp"

#include <SDL.h>
#include <SDL_image.h>
#include <SDL_mixer.h>
#include <SDL_ttf.h>

#include <cstdio>
#include <string>
#include <unordered_map>

using namespace bc;

static const int   BLOCK   = config::BLOCK_PX;   // 8
static const int   SCALE   = 3;                  // window pixel scale
static const char* ASSETS  = "assets";
static const char* FONT    = "assets/fonts/PressStart2P-Regular.ttf";

// Fixed window for the menu screens (game window is sized per-map).
static const int MENU_W = 720;
static const int MENU_H = 720;

// --- texture cache: path -> SDL_Texture* (loaded once) ---
struct TexCache {
    SDL_Renderer* r = nullptr;
    std::unordered_map<std::string, SDL_Texture*> map;

    SDL_Texture* get(const std::string& path) {
        auto it = map.find(path);
        if (it != map.end()) return it->second;
        SDL_Texture* tex = IMG_LoadTexture(r, path.c_str());
        if (!tex) std::fprintf(stderr, "missing texture: %s (%s)\n", path.c_str(), IMG_GetError());
        map[path] = tex;
        return tex;
    }
    void clear() {
        for (auto& kv : map) if (kv.second) SDL_DestroyTexture(kv.second);
        map.clear();
    }
};

static void blit(SDL_Renderer* r, SDL_Texture* t, int px, int py, int w, int h) {
    if (!t) return;
    SDL_Rect dst{px * SCALE, py * SCALE, w * SCALE, h * SCALE};
    SDL_RenderCopy(r, t, nullptr, &dst);
}

// Draw the current world (tiles, eagle, tanks, bullets). Shared by play+visit.
static void render_world(SDL_Renderer* ren, TexCache& cache, World& w, int anim) {
    SDL_SetRenderDrawColor(ren, 0, 0, 0, 255);
    SDL_RenderClear(ren);

    for (int row = 0; row < w.gs.map.rows; ++row) {
        for (int col = 0; col < w.gs.map.cols; ++col) {
            TileType t = w.gs.map.get(Position{col, row});
            const char* name = app::tile_sprite_name(t);
            if (!name) continue;
            SDL_Texture* tex = cache.get(std::string(ASSETS) + "/tiles/" + name + ".png");
            blit(ren, tex, col*BLOCK, row*BLOCK, BLOCK, BLOCK);
        }
    }

    blit(ren, cache.get(app::eagle_sprite(w.gs.eagle, ASSETS)),
         w.gs.eagle.x, w.gs.eagle.y, w.gs.eagle.w, w.gs.eagle.h);

    for (auto& t : w.gs.tanks) {
        if (!t.alive) continue;
        if (t.invincible() && t.flashing()) continue;
        blit(ren, cache.get(app::tank_sprite(t, anim, ASSETS)), t.x, t.y, t.w, t.h);
    }

    for (auto& b : w.gs.bullets) {
        if (!b.alive) continue;
        blit(ren, cache.get(app::bullet_sprite(b, ASSETS)), b.x, b.y, b.w, b.h);
    }
}

enum class AppState { MENU, MAP_SELECT, PLAYING, VISITING };

int main(int argc, char** argv) {
    (void)argc; (void)argv;

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) != 0) {
        std::fprintf(stderr, "SDL_Init: %s\n", SDL_GetError()); return 1;
    }
    IMG_Init(IMG_INIT_PNG);
    TTF_Init();
    Mix_OpenAudio(44100, MIX_DEFAULT_FORMAT, 2, 2048);

    // Single resizable window reused across states; size changes per map.
    SDL_Window* win = SDL_CreateWindow("Battle City",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, MENU_W, MENU_H, 0);
    SDL_Renderer* ren = SDL_CreateRenderer(win, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);

    TexCache cache; cache.r = ren;

    ui::TextRenderer text;
    text.open(FONT, 16);   // falls back to bitmap if missing

    // --- sounds ---
    Mix_Chunk* snd_fire  = Mix_LoadWAV((std::string(ASSETS)+"/sounds/fire.ogg").c_str());
    Mix_Chunk* snd_start = Mix_LoadWAV((std::string(ASSETS)+"/sounds/gamestart.ogg").c_str());
    Mix_Chunk* snd_over  = Mix_LoadWAV((std::string(ASSETS)+"/sounds/gameover.ogg").c_str());

    // --- app state ---
    AppState  state = AppState::MENU;
    ui::ModeMenu mode_menu;
    ui::MapMenu  map_menu;
    ui::GameMode chosen_mode = ui::GameMode::CLASSIC;

    MapRegistry reg;
    World w(42);
    bool world_ready = false;   // a map is loaded into w
    bool was_over    = false;

    int anim = 0, frame_count = 0;

    // Resize the window + (re)load a map into the world for the given entry.
    auto load_into_world = [&](const ui::ModeInfo& info, const ui::MapEntry& entry) -> bool {
        try {
            reg.load(entry.path, entry.path, info.cols, info.rows);  // key = path
        } catch (const std::exception& e) {
            std::fprintf(stderr, "map load failed (%s): %s\n", entry.path.c_str(), e.what());
            return false;
        }
        const MapTemplate& tmpl = reg.get(entry.path);
        const int ww = tmpl.map.pixel_width()  * SCALE;
        const int wh = tmpl.map.pixel_height() * SCALE;
        SDL_SetWindowSize(win, ww, wh);
        SDL_SetWindowPosition(win, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED);
        w.reset(tmpl, 1);
        world_ready = true;
        was_over = false;
        return true;
    };

    bool running = true;
    while (running) {
        // animation toggle every 8 frames (used by play + visit render)
        if (++frame_count % 8 == 0) anim ^= 1;
        const bool blink = (frame_count / 30) % 2 == 0;   // ~0.5s blink

        // ---------------- input ----------------
        bool fire = false;
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) { running = false; break; }
            if (ev.type != SDL_KEYDOWN) continue;
            const SDL_Keycode k = ev.key.keysym.sym;

            switch (state) {
            case AppState::MENU:
                if      (k == SDLK_UP)     mode_menu.up();
                else if (k == SDLK_DOWN)   mode_menu.down();
                else if (k == SDLK_ESCAPE) running = false;       // Esc in menu = quit
                else if (k == SDLK_RETURN || k == SDLK_KP_ENTER) {
                    chosen_mode = mode_menu.selected_mode();
                    const ui::ModeInfo& info = ui::mode_info(chosen_mode);
                    auto maps = ui::discover_maps(ASSETS, info);
                    if (maps.empty()) {
                        std::fprintf(stderr, "no maps found for mode %s\n", info.label);
                    } else {
                        map_menu.set(info, std::move(maps));
                        state = AppState::MAP_SELECT;
                    }
                }
                break;

            case AppState::MAP_SELECT:
                if      (k == SDLK_UP)     map_menu.up();
                else if (k == SDLK_DOWN)   map_menu.down();
                else if (k == SDLK_ESCAPE) state = AppState::MENU;  // back to mode list
                else if (k == SDLK_RETURN || k == SDLK_KP_ENTER) {
                    const ui::ModeInfo& info = ui::mode_info(chosen_mode);
                    if (load_into_world(info, map_menu.selected_map())) {
                        if (info.playable) {
                            state = AppState::PLAYING;
                            if (snd_start) Mix_PlayChannel(-1, snd_start, 0);
                        } else {
                            state = AppState::VISITING;   // frozen look-only
                        }
                    }
                }
                break;

            case AppState::PLAYING:
                if      (k == SDLK_ESCAPE) {                        // back to menu
                    state = AppState::MENU;
                    SDL_SetWindowSize(win, MENU_W, MENU_H);
                    SDL_SetWindowPosition(win, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED);
                }
                else if (k == SDLK_r) {
                    const MapTemplate& tmpl = reg.get(map_menu.selected_map().path);
                    w.reset(tmpl, 1);
                    was_over = false;
                    if (snd_start) Mix_PlayChannel(-1, snd_start, 0);
                }
                else if (k == SDLK_SPACE) fire = true;
                break;

            case AppState::VISITING:
                if (k == SDLK_ESCAPE) {                             // back to menu
                    state = AppState::MENU;
                    SDL_SetWindowSize(win, MENU_W, MENU_H);
                    SDL_SetWindowPosition(win, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED);
                }
                break;
            }
        }
        if (!running) break;

        // ---------------- update + render per state ----------------
        switch (state) {
        case AppState::MENU: {
            SDL_SetRenderDrawColor(ren, 0, 0, 0, 255);
            SDL_RenderClear(ren);
            int ww, wh; SDL_GetWindowSize(win, &ww, &wh);
            mode_menu.render(ren, text, ww, wh, blink);
            SDL_RenderPresent(ren);
            break;
        }

        case AppState::MAP_SELECT: {
            SDL_SetRenderDrawColor(ren, 0, 0, 0, 255);
            SDL_RenderClear(ren);
            int ww, wh; SDL_GetWindowSize(win, &ww, &wh);
            map_menu.render(ren, text, ww, wh, blink);
            SDL_RenderPresent(ren);
            break;
        }

        case AppState::PLAYING: {
            // build action from held arrow keys
            TankAction act;
            const Uint8* ks = SDL_GetKeyboardState(nullptr);
            if      (ks[SDL_SCANCODE_UP])    { act.direction = Direction::UP;    act.move = true; }
            else if (ks[SDL_SCANCODE_RIGHT]) { act.direction = Direction::RIGHT; act.move = true; }
            else if (ks[SDL_SCANCODE_DOWN])  { act.direction = Direction::DOWN;  act.move = true; }
            else if (ks[SDL_SCANCODE_LEFT])  { act.direction = Direction::LEFT;  act.move = true; }
            act.fire = fire;

            std::size_t bullets_before = w.gs.bullets.size();
            if (!w.done()) w.step({act});
            if (w.gs.bullets.size() > bullets_before && snd_fire)
                Mix_PlayChannel(-1, snd_fire, 0);
            if (w.done() && !was_over) {
                if (snd_over) Mix_PlayChannel(-1, snd_over, 0);
                was_over = true;
            }

            render_world(ren, cache, w, anim);
            SDL_RenderPresent(ren);
            break;
        }

        case AppState::VISITING: {
            // engine frozen: no step. Just draw the loaded map + entities.
            if (world_ready) render_world(ren, cache, w, anim);
            // small hint overlay
            int ww, wh; SDL_GetWindowSize(win, &ww, &wh);
            text.draw(ren, "VISIT  ESC BACK", ww / 2, 8, ui::COL_WHITE, 2,
                      ui::Align::CENTER);
            SDL_RenderPresent(ren);
            break;
        }
        }
    }

    cache.clear();
    if (snd_fire)  Mix_FreeChunk(snd_fire);
    if (snd_start) Mix_FreeChunk(snd_start);
    if (snd_over)  Mix_FreeChunk(snd_over);
    text.close();
    Mix_CloseAudio();
    TTF_Quit();
    IMG_Quit();
    SDL_DestroyRenderer(ren);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}