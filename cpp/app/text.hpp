// cpp/app/text.hpp
//
// Tiny text helper for the menu. Prefers SDL2_ttf with a pixel font; if the
// font fails to load, falls back to a crude 5x7 bitmap so the menu is still
// readable (no crash, no blank screen).
//
// Usage:
//   TextRenderer text;
//   text.open(ren, "assets/fonts/PressStart2P.ttf", 16);  // size ignored by fallback
//   text.draw(ren, "BATTLE CITY", x, y, {255,255,255,255}, 3 /*scale*/, Align::CENTER);
//
// Coordinates are in WINDOW pixels (already scaled), unlike the game blit().

#pragma once

#include <SDL.h>
#include <SDL_ttf.h>

#include <cstdint>
#include <string>

namespace ui {

enum class Align { LEFT, CENTER, RIGHT };

class TextRenderer {
public:
    bool open(const std::string& font_path, int px) {
        if (!TTF_WasInit()) TTF_Init();
        font_ = TTF_OpenFont(font_path.c_str(), px);
        px_ = px;
        if (!font_) {
            std::fprintf(stderr,
                "font load failed (%s) -> using bitmap fallback: %s\n",
                font_path.c_str(), TTF_GetError());
        }
        return font_ != nullptr;
    }

    void close() {
        if (font_) { TTF_CloseFont(font_); font_ = nullptr; }
    }

    ~TextRenderer() { close(); }

    // Measure rendered width in pixels for layout/centering.
    int measure(const std::string& s, int scale) const {
        if (font_) {
            int w = 0, h = 0;
            TTF_SizeUTF8(font_, s.c_str(), &w, &h);
            return w;  // ttf already drawn at its native size; scale=1 path
        }
        return static_cast<int>(s.size()) * (GLYPH_W + 1) * scale;
    }

    int line_height(int scale) const {
        if (font_) return TTF_FontHeight(font_);
        return GLYPH_H * scale;
    }

    // Draw a string. With ttf, `scale` is ignored (font px sets the size).
    // With the bitmap fallback, `scale` multiplies the 5x7 cells.
    void draw(SDL_Renderer* ren, const std::string& s, int x, int y,
              SDL_Color col, int scale, Align align = Align::LEFT) const {
        if (font_) {
            SDL_Surface* surf = TTF_RenderUTF8_Blended(font_, s.c_str(), col);
            if (!surf) return;
            SDL_Texture* tex = SDL_CreateTextureFromSurface(ren, surf);
            int w = surf->w, h = surf->h;
            SDL_FreeSurface(surf);
            if (!tex) return;
            int dx = x;
            if (align == Align::CENTER) dx = x - w / 2;
            else if (align == Align::RIGHT) dx = x - w;
            SDL_Rect dst{ dx, y, w, h };
            SDL_RenderCopy(ren, tex, nullptr, &dst);
            SDL_DestroyTexture(tex);
            return;
        }
        draw_bitmap(ren, s, x, y, col, scale, align);
    }

private:
    // ----- bitmap fallback: 5x7 uppercase font, digits, and a few symbols -----
    static constexpr int GLYPH_W = 5;
    static constexpr int GLYPH_H = 7;

    void draw_bitmap(SDL_Renderer* ren, const std::string& s, int x, int y,
                     SDL_Color col, int scale, Align align) const {
        const int cell = (GLYPH_W + 1) * scale;
        const int total_w = static_cast<int>(s.size()) * cell;
        int dx = x;
        if (align == Align::CENTER) dx = x - total_w / 2;
        else if (align == Align::RIGHT) dx = x - total_w;

        SDL_SetRenderDrawColor(ren, col.r, col.g, col.b, col.a);
        for (char ch : s) {
            const std::uint8_t* g = glyph(ch);
            if (g) {
                for (int row = 0; row < GLYPH_H; ++row) {
                    std::uint8_t bits = g[row];
                    for (int cbit = 0; cbit < GLYPH_W; ++cbit) {
                        if (bits & (1 << (GLYPH_W - 1 - cbit))) {
                            SDL_Rect px{ dx + cbit * scale, y + row * scale,
                                         scale, scale };
                            SDL_RenderFillRect(ren, &px);
                        }
                    }
                }
            }
            dx += cell;
        }
    }

    // Each glyph: 7 bytes, low 5 bits used. Minimal A-Z, 0-9, space, a few marks.
    static const std::uint8_t* glyph(char ch) {
        // Returns nullptr for unknown chars (drawn as a gap).
        static const std::uint8_t SPACE[7] = {0,0,0,0,0,0,0};
        if (ch == ' ') return SPACE;

        // Only the characters the menu actually needs are defined; others -> gap.
        // Bit pattern (MSB-left of 5): see comments.
        static const std::uint8_t A[7]={0b01110,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001};
        static const std::uint8_t B[7]={0b11110,0b10001,0b11110,0b10001,0b10001,0b10001,0b11110};
        static const std::uint8_t C[7]={0b01110,0b10001,0b10000,0b10000,0b10000,0b10001,0b01110};
        static const std::uint8_t D[7]={0b11110,0b10001,0b10001,0b10001,0b10001,0b10001,0b11110};
        static const std::uint8_t E[7]={0b11111,0b10000,0b11110,0b10000,0b10000,0b10000,0b11111};
        static const std::uint8_t F[7]={0b11111,0b10000,0b11110,0b10000,0b10000,0b10000,0b10000};
        static const std::uint8_t G[7]={0b01110,0b10001,0b10000,0b10111,0b10001,0b10001,0b01110};
        static const std::uint8_t I[7]={0b11111,0b00100,0b00100,0b00100,0b00100,0b00100,0b11111};
        static const std::uint8_t L[7]={0b10000,0b10000,0b10000,0b10000,0b10000,0b10000,0b11111};
        static const std::uint8_t M[7]={0b10001,0b11011,0b10101,0b10101,0b10001,0b10001,0b10001};
        static const std::uint8_t N[7]={0b10001,0b11001,0b10101,0b10011,0b10001,0b10001,0b10001};
        static const std::uint8_t O[7]={0b01110,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110};
        static const std::uint8_t R[7]={0b11110,0b10001,0b10001,0b11110,0b10100,0b10010,0b10001};
        static const std::uint8_t S[7]={0b01111,0b10000,0b10000,0b01110,0b00001,0b00001,0b11110};
        static const std::uint8_t T[7]={0b11111,0b00100,0b00100,0b00100,0b00100,0b00100,0b00100};
        static const std::uint8_t U[7]={0b10001,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110};
        static const std::uint8_t V[7]={0b10001,0b10001,0b10001,0b10001,0b10001,0b01010,0b00100};
        static const std::uint8_t Y[7]={0b10001,0b10001,0b01010,0b00100,0b00100,0b00100,0b00100};
        static const std::uint8_t DGT[10][7]={
            {0b01110,0b10001,0b10011,0b10101,0b11001,0b10001,0b01110}, //0
            {0b00100,0b01100,0b00100,0b00100,0b00100,0b00100,0b01110}, //1
            {0b01110,0b10001,0b00001,0b00110,0b01000,0b10000,0b11111}, //2
            {0b11111,0b00010,0b00100,0b00010,0b00001,0b10001,0b01110}, //3
            {0b00010,0b00110,0b01010,0b10010,0b11111,0b00010,0b00010}, //4
            {0b11111,0b10000,0b11110,0b00001,0b00001,0b10001,0b01110}, //5
            {0b00110,0b01000,0b10000,0b11110,0b10001,0b10001,0b01110}, //6
            {0b11111,0b00001,0b00010,0b00100,0b01000,0b01000,0b01000}, //7
            {0b01110,0b10001,0b10001,0b01110,0b10001,0b10001,0b01110}, //8
            {0b01110,0b10001,0b10001,0b01111,0b00001,0b00010,0b01100}, //9
        };
        if (ch >= '0' && ch <= '9') return DGT[ch - '0'];
        switch (ch) {
            case 'A': return A; case 'B': return B; case 'C': return C;
            case 'D': return D; case 'E': return E; case 'F': return F;
            case 'G': return G; case 'I': return I; case 'L': return L;
            case 'M': return M; case 'N': return N; case 'O': return O;
            case 'R': return R; case 'S': return S; case 'T': return T;
            case 'U': return U; case 'V': return V; case 'Y': return Y;
            default:  return nullptr;
        }
    }

    TTF_Font* font_ = nullptr;
    int px_ = 16;
};

}  // namespace ui