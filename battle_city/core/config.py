"""
battle_city/core/config.py

Global constants for the Battle City game engine.

All values are derived from the NES original (60Hz, 8px block grid).
Physics runs at 60Hz internally. The renderer can run at a lower rate.

No external dependencies.
"""

from __future__ import annotations

from enum import IntEnum


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

FPS:          int = 60   # physics / game loop tick rate (NES native)
BLOCK_PX:     int = 8    # one grid cell in pixels
TILE_PX:      int = 16   # one logical tile = 2x2 blocks
TANK_PX:      int = 16   # tank sprite size (always one logical tile)
BULLET_W_PX:  int = 4    # bullet width  in pixels
BULLET_H_PX:  int = 8    # bullet height in pixels (vertical orientation)


# ---------------------------------------------------------------------------
# Direction
# ---------------------------------------------------------------------------

class Direction(IntEnum):
    UP    = 0
    RIGHT = 1
    DOWN  = 2
    LEFT  = 3


# Direction -> (dcol, drow) movement delta in block units
DIRECTION_DELTA: dict[Direction, tuple[int, int]] = {
    Direction.UP:    ( 0, -1),
    Direction.RIGHT: ( 1,  0),
    Direction.DOWN:  ( 0,  1),
    Direction.LEFT:  (-1,  0),
}


# ---------------------------------------------------------------------------
# Tank types
# ---------------------------------------------------------------------------

class TankType(IntEnum):
    PLAYER = 0   # ally tank -- can receive Star upgrades and power-ups
    BASIC  = 1   # enemy -- slow speed, slow bullet, 1 HP
    FAST   = 2   # enemy -- fast speed, slow bullet, 1 HP
    POWER  = 3   # enemy -- slow speed, fast bullet, 1 HP
    ARMOR  = 4   # enemy -- slow speed, fast bullet, 4 HP


class TankTeam(IntEnum):
    PLAYER = 0
    ENEMY  = 1


# Tank movement speed in pixels per frame (at 60 FPS)
TANK_SPEED_PX: dict[TankType, int] = {
    TankType.PLAYER: 1,
    TankType.BASIC:  1,
    TankType.FAST:   2,
    TankType.POWER:  1,
    TankType.ARMOR:  1,
}

# Tank HP (armor changes colour each hit: green -> light green -> yellow -> grey)
TANK_HP: dict[TankType, int] = {
    TankType.PLAYER: 1,   
    TankType.BASIC:  1,
    TankType.FAST:   1,
    TankType.POWER:  1,
    TankType.ARMOR:  4,
}

# Points awarded when an enemy tank is destroyed
TANK_POINTS: dict[TankType, int] = {
    TankType.BASIC: 100,
    TankType.FAST:  200,
    TankType.POWER: 300,
    TankType.ARMOR: 400,
}

# Maximum enemies on screen simultaneously (NES rule)
MAX_ENEMIES_ON_SCREEN: int = 4

# Flash tank spawn indices -- 4th, 11th, 18th enemy carry a power-up (0-indexed)
FLASH_TANK_INDICES: tuple[int, ...] = (3, 10, 17)


# ---------------------------------------------------------------------------
# Bullet
# ---------------------------------------------------------------------------

class BulletOwner(IntEnum):
    PLAYER = 0
    ENEMY  = 1


# Bullet speed in pixels per frame
BULLET_SPEED_PX: dict[str, int] = {
    "slow": 4,   # basic / fast enemy tanks, player base bullet
    "fast": 8,   # power / armor enemy tanks, player 1-star+ bullet
}

MAX_BULLET_POWER:   int = 3   # maximum star level
MAX_BULLETS_SCREEN: int = 2   # max player bullets on screen at star level 2+


# ---------------------------------------------------------------------------
# Player upgrade levels (Star power-up)
# Star upgrades affect bullets only -- player movement speed never changes.
# ---------------------------------------------------------------------------

class StarLevel(IntEnum):
    BASE   = 0   # slow bullet, 1 bullet max
    STAR_1 = 1   # fast bullet, 1 bullet max
    STAR_2 = 2   # fast bullet, 2 bullets on screen
    STAR_3 = 3   # fast bullet, 2 bullets, destroys steel


STAR_BULLET_SPEED: dict[StarLevel, str] = {
    StarLevel.BASE:   "slow",
    StarLevel.STAR_1: "fast",
    StarLevel.STAR_2: "fast",
    StarLevel.STAR_3: "fast",
}

STAR_MAX_BULLETS: dict[StarLevel, int] = {
    StarLevel.BASE:   1,
    StarLevel.STAR_1: 1,
    StarLevel.STAR_2: 2,
    StarLevel.STAR_3: 2,
}

STAR_DESTROYS_STEEL: dict[StarLevel, bool] = {
    StarLevel.BASE:   False,
    StarLevel.STAR_1: False,
    StarLevel.STAR_2: False,
    StarLevel.STAR_3: True,
}


# ---------------------------------------------------------------------------
# Power-ups
# ---------------------------------------------------------------------------

class PowerUpType(IntEnum):
    STAR    = 0   # upgrade player bullet
    HELMET  = 1   # temporary invincibility
    GRENADE = 2   # destroy all enemies on screen (no points awarded)
    CLOCK   = 3   # freeze all enemies
    SHOVEL  = 4   # fortify eagle with steel (temporary)
    TANK    = 5   # extra life (1-UP)


POWERUP_POINTS: int = 500   # collecting any power-up = +500 pts

# Duration of timed power-ups in frames (at 60 FPS)
POWERUP_DURATION_FRAMES: dict[PowerUpType, int] = {
    PowerUpType.HELMET: 60 * 10,   # 10 seconds invincibility
    PowerUpType.CLOCK:  60 * 10,   # 10 seconds freeze
    PowerUpType.SHOVEL: 60 * 20,   # 20 seconds steel eagle protection
}


# ---------------------------------------------------------------------------
# Scoring / lives
# ---------------------------------------------------------------------------

EXTRA_LIFE_SCORE: int = 20_000   # score threshold for an extra life
STARTING_LIVES:   int = 3


# ---------------------------------------------------------------------------
# Spawn invincibility
# ---------------------------------------------------------------------------

SPAWN_INVINCIBLE_FRAMES: int = 60 * 3   # 3 seconds after respawn
SPAWN_FLASH_INTERVAL:    int = 4        # flash every N frames during shield


# ---------------------------------------------------------------------------
# Ice physics
# ---------------------------------------------------------------------------

# Frames a tank continues sliding after releasing a direction key on ice
ICE_SLIDE_FRAMES: int = 16


# ---------------------------------------------------------------------------
# Bullet impact zones (sub-pixel offset thresholds)
# ---------------------------------------------------------------------------

# When a bullet hits a BRICK, the sub-pixel offset within the 8px block
# (0-7, perpendicular to bullet travel) determines how many blocks are hit:
#   offset 0 .. LOW-1          -> 1 block
#   offset LOW .. HIGH         -> 2 blocks (straddles boundary)
#   offset HIGH+1 .. 7         -> 1 block
IMPACT_MULTI_BLOCK_LOW:  int = 3
IMPACT_MULTI_BLOCK_HIGH: int = 5


# ---------------------------------------------------------------------------
# Scenario agent / enemy counts
# ---------------------------------------------------------------------------

PLAYER_AGENT_COUNT: dict[str, int] = {
    "classic": 1,   # 1 RL agent vs bots
    "coop":    2,   # 2 RL agents cooperative
    "medium":  2,   # medium maps: 2 RL cooperative
    "xlarge":  5,   # xlarge maps: 5 RL vs 100 enemies
}

ENEMY_COUNT: dict[str, int] = {
    "classic": 20,
    "medium":  20,
    "xlarge":  100,
}