"""
battle_city/core/entities/tank.py

Tank -- player or enemy tank entity.

Inherits from Entity and implements the full tank state:
    - position, direction, speed
    - team, type, HP
    - star level (player only -- also acts as hit buffer)
    - invincibility frames (post-spawn shield)
    - ice sliding state
    - active bullets tracking
"""

from __future__ import annotations

from battle_city.core.config import (
    Direction, TankType, TankTeam, StarLevel,
    TANK_PX, TANK_SPEED_PX, TANK_HP,
    SPAWN_INVINCIBLE_FRAMES, SPAWN_FLASH_INTERVAL,
    ICE_SLIDE_FRAMES,
    STAR_BULLET_SPEED, STAR_MAX_BULLETS, STAR_DESTROYS_STEEL,
)
from battle_city.core.entities.entity import Entity


class Tank(Entity):
    """
    Player or enemy tank.

    Star level (player only):
        Each Star power-up increments star_level (capped at STAR_3).
        When a player tank is hit:
            star_level > BASE  -> downgrade star_level by 1, tank survives
            star_level == BASE -> tank destroyed, player loses one life

    Invincibility:
        Spawns with a temporary shield (SPAWN_INVINCIBLE_FRAMES).
        Also granted by the Helmet power-up (handled by World).
    """

    def __init__(
        self,
        x:          int,
        y:          int,
        tank_type:  TankType,
        team:       TankTeam,
        direction:  Direction = Direction.UP,
    ) -> None:
        super().__init__(x=x, y=y, w=TANK_PX, h=TANK_PX)

        self._tank_type:  TankType  = tank_type
        self._team:       TankTeam  = team
        self._direction:  Direction = direction

        # HP -- decremented on hit (armor tanks take 4 hits)
        self._hp: int = TANK_HP[tank_type]

        # Star level -- player only; ignored for enemy tanks
        self._star_level: StarLevel = StarLevel.BASE

        # Movement
        self._speed_px: int  = TANK_SPEED_PX[tank_type]
        self._moving:   bool = False

        # Invincibility frames (spawn shield or Helmet power-up)
        self._invincible_frames: int = SPAWN_INVINCIBLE_FRAMES

        # Ice sliding
        self._slide_frames: int = 0

        # Active bullet IDs fired by this tank (for max-bullet-on-screen rule)
        self._bullet_ids: list[int] = []

    # ------------------------------------------------------------------
    # Identity / type
    # ------------------------------------------------------------------

    @property
    def tank_type(self) -> TankType:
        return self._tank_type

    @property
    def team(self) -> TankTeam:
        return self._team

    @property
    def is_player(self) -> bool:
        return self._team == TankTeam.PLAYER

    @property
    def is_enemy(self) -> bool:
        return self._team == TankTeam.ENEMY

    # ------------------------------------------------------------------
    # Direction & movement
    # ------------------------------------------------------------------

    @property
    def direction(self) -> Direction:
        return self._direction

    @direction.setter
    def direction(self, value: Direction) -> None:
        self._direction = value

    @property
    def moving(self) -> bool:
        return self._moving

    @moving.setter
    def moving(self, value: bool) -> None:
        self._moving = value

    @property
    def speed_px(self) -> int:
        return self._speed_px

    # ------------------------------------------------------------------
    # HP
    # ------------------------------------------------------------------

    @property
    def hp(self) -> int:
        return self._hp

    def take_hit(self) -> bool:
        """
        Apply one hit to this tank.

        For player tanks:
            - If star_level > BASE: downgrade star level, tank survives.
            - If star_level == BASE: decrement HP; tank dies when HP reaches 0.

        For enemy tanks:
            - Decrement HP directly; tank dies when HP reaches 0.

        Returns True if the tank was destroyed, False if it survived.
        """
        if self.is_player:
            if self._star_level > StarLevel.BASE:
                self._star_level = StarLevel(self._star_level - 1)
                return False
            # No star buffer left -- fall through to HP decrement
        self._hp -= 1
        if self._hp <= 0:
            self.destroy()
            return True
        return False

    # ------------------------------------------------------------------
    # Star level (player only)
    # ------------------------------------------------------------------

    @property
    def star_level(self) -> StarLevel:
        return self._star_level

    def add_star(self) -> None:
        """Increment star level, capped at STAR_3."""
        if self._star_level < StarLevel.STAR_3:
            self._star_level = StarLevel(self._star_level + 1)

    def reset_stars(self) -> None:
        """Reset to BASE -- called on death / respawn."""
        self._star_level = StarLevel.BASE

    @property
    def bullet_speed(self) -> str:
        """Current bullet speed key ("slow" | "fast")."""
        return STAR_BULLET_SPEED[self._star_level]

    @property
    def max_bullets(self) -> int:
        """Max simultaneous bullets this tank can have on screen."""
        if self.is_player:
            return STAR_MAX_BULLETS[self._star_level]
        return 1   # enemies always fire one bullet at a time

    @property
    def can_destroy_steel(self) -> bool:
        return self.is_player and STAR_DESTROYS_STEEL[self._star_level]

    # ------------------------------------------------------------------
    # Invincibility
    # ------------------------------------------------------------------

    @property
    def invincible(self) -> bool:
        return self._invincible_frames > 0

    @property
    def flashing(self) -> bool:
        """True on frames where the sprite should be hidden (visual flash)."""
        if not self.invincible:
            return False
        return (self._invincible_frames % (SPAWN_FLASH_INTERVAL * 2)
                < SPAWN_FLASH_INTERVAL)

    def grant_invincibility(self, frames: int) -> None:
        """Grant invincibility for the given number of frames."""
        self._invincible_frames = max(self._invincible_frames, frames)

    # ------------------------------------------------------------------
    # Ice sliding
    # ------------------------------------------------------------------

    @property
    def sliding(self) -> bool:
        return self._slide_frames > 0

    def start_slide(self) -> None:
        """Called by PhysicsSystem when the tank steps onto ice."""
        self._slide_frames = ICE_SLIDE_FRAMES

    # ------------------------------------------------------------------
    # Bullet tracking
    # ------------------------------------------------------------------

    def register_bullet(self, bullet_id: int) -> None:
        self._bullet_ids.append(bullet_id)

    def unregister_bullet(self, bullet_id: int) -> None:
        if bullet_id in self._bullet_ids:
            self._bullet_ids.remove(bullet_id)

    @property
    def bullet_count(self) -> int:
        return len(self._bullet_ids)

    @property
    def can_fire(self) -> bool:
        return self.bullet_count < self.max_bullets

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _on_update(self) -> None:
        if self._invincible_frames > 0:
            self._invincible_frames -= 1
        if self._slide_frames > 0:
            self._slide_frames -= 1

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "alive" if self.alive else "dead"
        return (
            f"Tank(id={self.id}, {self._team.name}, {self._tank_type.name}, "
            f"x={self.x}, y={self.y}, dir={self._direction.name}, "
            f"hp={self._hp}, star={self._star_level.name}, {status})"
        )