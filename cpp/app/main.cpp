// cpp/app/main.cpp
//
// Standalone SDL2 player for the Battle City engine. Lets a human watch/play
// the headless C++ engine with real sprites + sound. NOT used for RL training
// (that path is pybind11 -> Python). This is the visual validation front-end.
//
// Controls: Arrow keys = move player 0, Space = fire, R = reset, Esc = quit.
//
// Build: see cpp/app/CMakeLists.txt (links SDL2, SDL2_image, SDL2_mixer).

#include "battle_city/world.hpp"
#include "battle_city/map_loader.hpp"
#include "sprite_paths.hpp"

#include <SDL.h>
#include <SDL_image.h>
#include <SDL_mixer.h>

#include <cstdio>
#include <string>
#include <unordered_map>

using namespace bc;

static const int   BLOCK   = config::BLOCK_PX;   // 8
static const int   SCALE   = 3;                  // window pixel scale
static const char* ASSETS  = "assets";

// --- texture cache: path -> SDL_Texture* (loaded once) ---
struct TexCache {
    SDL_Renderer* r = nullptr;
    std::unordered_map<std::string, SDL_Texture*> map;

    SDL_Texture* get(const std::string& path) {
        auto it = map.find(path);
        if (it != map.end()) return it->second;
        SDL_Texture* tex = IMG_LoadTexture(r, path.c_str());
        if (!tex) std::fprintf(stderr, "missing texture: %s (%s)\n",
                               path.c_str(), IMG_GetError());
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

int main(int argc, char** argv) {
    (void)argc; (void)argv;

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) != 0) {
        std::fprintf(stderr, "SDL_Init: %s\n", SDL_GetError()); return 1;
    }
    IMG_Init(IMG_INIT_PNG);
    Mix_OpenAudio(44100, MIX_DEFAULT_FORMAT, 2, 2048);

    // --- load map + engine ---
    MapRegistry reg;
    const std::string map_path = std::string(ASSETS) + "/maps/classic/1.txt";
    try { reg.load("c1", map_path, 26, 26); }
    catch (const std::exception& e) {
        std::fprintf(stderr, "map load failed: %s\n", e.what()); return 1;
    }
    const MapTemplate& tmpl = reg.get("c1");

    const int win_w = tmpl.map.pixel_width()  * SCALE;
    const int win_h = tmpl.map.pixel_height() * SCALE;

    SDL_Window* win = SDL_CreateWindow("Battle City (engine preview)",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, win_w, win_h, 0);
    SDL_Renderer* ren = SDL_CreateRenderer(win, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);

    TexCache cache; cache.r = ren;

    // --- sounds ---
    Mix_Chunk* snd_fire  = Mix_LoadWAV((std::string(ASSETS)+"/sounds/fire.ogg").c_str());
    Mix_Chunk* snd_start = Mix_LoadWAV((std::string(ASSETS)+"/sounds/gamestart.ogg").c_str());
    Mix_Chunk* snd_over  = Mix_LoadWAV((std::string(ASSETS)+"/sounds/gameover.ogg").c_str());

    World w(42);
    w.reset(tmpl, 1);
    if (snd_start) Mix_PlayChannel(-1, snd_start, 0);

    bool running = true;
    bool was_over = false;
    int  anim = 0;           // toggles 0/1 for tank tread animation
    int  frame_count = 0;

    while (running) {
        // ---- input ----
        bool fire = false;
        TankAction act;  // default: idle, facing UP
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) running = false;
            if (ev.type == SDL_KEYDOWN) {
                switch (ev.key.keysym.sym) {
                    case SDLK_ESCAPE: running = false; break;
                    case SDLK_r:
                        w.reset(tmpl, 1);
                        if (snd_start) Mix_PlayChannel(-1, snd_start, 0);
                        was_over = false;
                        break;
                    case SDLK_SPACE: fire = true; break;
                    default: break;
                }
            }
        }
        // held arrow keys = movement (smooth, not event-based)
        const Uint8* ks = SDL_GetKeyboardState(nullptr);
        if (ks[SDL_SCANCODE_UP])    { act.direction = Direction::UP;    act.move = true; }
        else if (ks[SDL_SCANCODE_RIGHT]) { act.direction = Direction::RIGHT; act.move = true; }
        else if (ks[SDL_SCANCODE_DOWN])  { act.direction = Direction::DOWN;  act.move = true; }
        else if (ks[SDL_SCANCODE_LEFT])  { act.direction = Direction::LEFT;  act.move = true; }
        act.fire = fire;

        // ---- step engine ----
        std::size_t bullets_before = w.gs.bullets.size();
        if (!w.done()) w.step({act});
        if (w.gs.bullets.size() > bullets_before && snd_fire)
            Mix_PlayChannel(-1, snd_fire, 0);

        if (w.done() && !was_over) {
            if (snd_over) Mix_PlayChannel(-1, snd_over, 0);
            was_over = true;
        }

        // animation toggle every 8 frames
        if (++frame_count % 8 == 0) anim ^= 1;

        // ---- render ----
        SDL_SetRenderDrawColor(ren, 0, 0, 0, 255);
        SDL_RenderClear(ren);

        // tiles
        for (int row = 0; row < w.gs.map.rows; ++row) {
            for (int col = 0; col < w.gs.map.cols; ++col) {
                TileType t = w.gs.map.get(Position{col, row});
                const char* name = app::tile_sprite_name(t);
                if (!name) continue;
                SDL_Texture* tex = cache.get(
                    std::string(ASSETS) + "/tiles/" + name + ".png");
                blit(ren, tex, col*BLOCK, row*BLOCK, BLOCK, BLOCK);
            }
        }

        // eagle
        blit(ren, cache.get(app::eagle_sprite(w.gs.eagle, ASSETS)),
             w.gs.eagle.x, w.gs.eagle.y, w.gs.eagle.w, w.gs.eagle.h);

        // tanks (skip hidden-in-forest later; for now draw all)
        for (auto& t : w.gs.tanks) {
            if (!t.alive) continue;
            // flashing invincible tank: blink
            if (t.invincible() && t.flashing()) continue;
            blit(ren, cache.get(app::tank_sprite(t, anim, ASSETS)),
                 t.x, t.y, t.w, t.h);
        }

        // bullets
        for (auto& b : w.gs.bullets) {
            if (!b.alive) continue;
            blit(ren, cache.get(app::bullet_sprite(b, ASSETS)),
                 b.x, b.y, b.w, b.h);
        }

        SDL_RenderPresent(ren);
    }

    cache.clear();
    if (snd_fire)  Mix_FreeChunk(snd_fire);
    if (snd_start) Mix_FreeChunk(snd_start);
    if (snd_over)  Mix_FreeChunk(snd_over);
    Mix_CloseAudio();
    IMG_Quit();
    SDL_DestroyRenderer(ren);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}