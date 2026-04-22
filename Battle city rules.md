# Battle City (JPN) — Complete Game Rules

> **Developer:** Tomcat System / Namco  
> **Platform:** Famicom (NES)  
> **Released:** September 9, 1985 (Japan only)  
> **Genre:** Multi-directional tank shooter  
> **Sequel to:** Tank Battalion (arcade, 1980)

---

## 1. Objective

Destroy all **20 enemy tanks** on each stage while **protecting your Eagle base** (the falcon emblem at the bottom of the screen). The game ends immediately if the Eagle is destroyed — even by your own bullet.

---

## 2. Players

| Mode | Description |
|------|-------------|
| Single-player | Player 1 controls a **yellow tank** |
| Co-op 2-player | Player 1 = yellow tank · Player 2 = green tank · simultaneous |

Both players share the same Eagle base and must cooperate to defend it.

---

## 3. Controls

| Input | Action |
|-------|--------|
| D-Pad | Move tank in 4 cardinal directions (UP / DOWN / LEFT / RIGHT) |
| A button | Fire bullet |
| Start | Pause |

- The tank always faces the direction it last moved.
- Movement snaps tile by tile despite appearing smooth.

---

## 4. Stage Structure

- The game has **35 built-in stages**, each with a unique map layout.
- After clearing stage 35, the game loops back to stage 1 with **harder enemy combinations**.
- Each stage contains exactly **20 enemy tanks** to destroy.
- At most **4 enemy tanks** can be on screen simultaneously.
- Remaining tanks are shown as icons on the right-side HUD.
- Enemy tanks **spawn from 3 fixed positions** at the top of the screen.
- There is **no time limit** per stage.

---

## 5. Player Tank

### Starting state
- 1 bullet on screen at a time (cannot fire again until bullet hits or disappears).
- Slow bullet speed.
- Destroyed by a single enemy bullet.
- Spawns with a brief **invincibility shield** (flashing) after each life lost.

### Upgrade levels (via Star power-up)

| Stars collected | Effect |
|-----------------|--------|
| 1 star | Bullet speed increased |
| 2 stars | Two bullets on screen simultaneously |
| 3 stars | Bullets can destroy **steel walls** |

Stars reset to 0 when the player tank is destroyed.

---

## 6. Enemy Tanks

There are **4 enemy tank types**, each with different speed, HP, and bullet properties.  
Every type also has a **flash variant** (see section 7).

| Type | Name | Speed | Bullet | HP | Points |
|------|------|-------|--------|----|--------|
| 1 | **Basic** | Slow | Slow | 1 hit | 100 |
| 2 | **Fast** | Fast | Slow | 1 hit | 200 |
| 3 | **Power** | Slow | Fast | 1 hit | 300 |
| 4 | **Armor** | Slow | Fast | **4 hits** | 400 |

### Armor tank color progression (damage states)
Each hit changes color: **green → light green → yellow → light grey → destroyed**

### Enemy behavior notes
- Enemy tanks can destroy brick walls with their own bullets.
- In later stages, some enemies act as **decoys** to lure the player away from the base while another tank sneaks through.
- Fast tanks are the most dangerous to the base — they can reach the Eagle before you react.

---

## 7. Flash Tanks (Power-up Carriers)

In each stage, exactly **3 enemy tanks** will flash red when they spawn:
- The **4th**, **11th**, and **18th** tank to appear on screen.

**Rules:**
- Hit a flashing tank (any type) **once** to trigger a power-up spawn at a random location.
- The tank stops flashing after being hit (or after the power-up is collected).
- If a **second** flashing tank spawns while a power-up is on the field, the existing power-up **disappears immediately**.
- Only **one power-up** can exist on the field at a time.
- Power-ups can spawn on water tiles (unreachable).

> **RL relevance:** Flash tanks must be prioritized — missing them means losing the power-up permanently.

---

## 8. Power-ups

Each power-up collected grants **+500 points**.

| Icon | Name | Effect |
|------|------|--------|
| ⭐ Star | **Star** | Upgrades player tank (up to 3 stars, resets on death) |
| 🪖 Helmet | **Helmet / Shield** | Temporary invulnerability for the player tank |
| 💣 Grenade | **Grenade** | Destroys **all enemy tanks** currently on screen instantly (no points awarded for those kills) |
| 🕐 Clock | **Clock / Stop Watch** | Freezes all enemy tanks for several seconds (including new spawns during the freeze) |
| 🪚 Shovel | **Shovel / Fortification** | Replaces the brick walls surrounding the Eagle with **steel walls** for a limited time, then reverts to brick |
| 🚗 Tank | **1-UP** | Grants **one extra life** |

---

## 9. Terrain / Tile Types

| Tile | Appearance | Properties |
|------|-----------|------------|
| **Brick wall** | Red/brown blocks | Destructible by any bullet · 4 shots to clear a full width · Both player and enemy can destroy |
| **Steel wall** | Grey metal blocks | Indestructible by default · Can only be destroyed with **3-star** player bullets |
| **Water** | Blue tiles | **Impassable** for all tanks · Bullets pass through freely |
| **Ice** | Light blue/white | Tanks slide uncontrollably after stopping · Hard to steer precisely |
| **Bush / Forest** | Green tiles | Tanks and bullets **pass through freely** · Tanks are **hidden** under bushes |
| **Eagle (base)** | Falcon emblem | Surrounded by brick on game start · **Instant game over** if destroyed by any bullet |

---

## 10. Bullets

- Each player tank can have **1 active bullet** on screen at a time (2 with 2-star upgrade).
- Bullets travel in the direction the tank was facing when fired.
- Bullets are destroyed on impact with walls, enemies, or the screen edge.
- **Friendly fire:** If Player 1 hits Player 2, the hit player is **frozen** (cannot move) for a few seconds but can still turn and fire. No life is lost.
- Player bullets **can destroy the Eagle** — this causes instant game over.
- Enemy bullets **cannot** damage other enemy tanks.

---

## 11. Scoring

| Action | Points |
|--------|--------|
| Destroy Basic tank | 100 |
| Destroy Fast tank | 200 |
| Destroy Power tank | 300 |
| Destroy Armor tank | 400 |
| Collect any power-up | 500 |
| Extra life awarded at | **20,000 points** |

> Tanks destroyed by the **Grenade** power-up do **not** award kill points.

---

## 12. Lives & Game Over

- Players start with **3 lives** (default).
- An extra life is awarded at **20,000 points**.
- The game ends (**Game Over**) when:
  - All player lives are exhausted, **OR**
  - The Eagle base is hit by **any bullet** (player or enemy)

---

## 13. Stage Completion

A stage is complete when all **20 enemy tanks** are destroyed.  
A **post-stage score screen** appears showing kills per tank type for each player.

---

## 14. Looping & Difficulty

- After stage 35, the game loops to stage 1 with **reinforced enemy tank compositions**.
- From stage 36 onward, enemy patterns are harder and remain so for the rest of the loop.
- Completing 70 stages loops back to stage 1 again, accumulating score.

---

## 15. Construction Mode (Level Editor)

Battle City includes a **built-in map editor** — one of the earliest on NES.

- Accessible from the title screen.
- Supports all 5 terrain types (brick, steel, water, ice, bush).
- Base defense tiles can be modified.
- Custom maps can be played in co-op immediately.
- **Limitation:** Custom levels **cannot be saved** to cartridge.
- After completing a custom map, the game continues with the built-in stages.

---

## 16. Key Rules Summary for RL Environment

| Rule | Implementation note |
|------|-------------------|
| Eagle destroyed → instant game over | Terminal state, large negative reward |
| Player bullet hits Eagle → game over | Friendly-fire penalty on base |
| Flash tank hit → power-up spawns | Sparse reward signal, requires prioritization |
| New flash tank spawns → old power-up removed | Time-sensitive collection |
| 4 enemies max on screen simultaneously | Controlled enemy pressure |
| Grenade kills no points | Tradeoff: safety vs score optimization |
| Star resets on death | Inventory state must persist in observation |
| Ice tiles → sliding physics | Requires anticipatory movement |
| Bush tiles → hidden tanks | Partial observability — tanks invisible under forest |
| Friendly fire freezes ally | Negative coordination signal in 2-player mode |

---

*Sources: StrategyWiki, GameFAQs FAQ by brian_sulpher, Grokipedia, NamuWiki, The Cutting Room Floor*