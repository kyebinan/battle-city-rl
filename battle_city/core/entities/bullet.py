"""
battle_city/core/entities/bullet.py

Bullet -- projectile fired by a tank.

A bullet travels in a fixed direction at a fixed speed until it:
    - hits a BRICK wall  -> destroyed (may also destroy the brick)
    - hits a STEEL wall  -> destroyed (only if owner has 3-star)
    - hits a tank        -> both bullet and tank take damage
    - hits the Eagle     -> bullet destroyed, game over
    - reaches map edge   -> destroyed

The owner tank tracks active bullet IDs to enforce the max-bullets rule.
"""

from __future__ import annotations

from battle_city.core.config import (
    Direction, BulletOwner,
    BULLET_W_PX, BULLET_H_PX,
    BULLET_SPEED_PX,
    DIRECTION_DELTA,
)
from battle_city.core.entities.entity import Entity


class Bullet(Entity):
    """
    Projectile fired by a player or enemy tank.

    Size:
        Vertical travel   (UP / DOWN):  w=BULLET_W_PX, h=BULLET_H_PX
        Horizontal travel (LEFT / RIGHT): w=BULLET_H_PX, h=BULLET_W_PX
        (the longer dimension is always along the travel axis)

    Pixel position:
        x, y = top-left of the bullet sprite.
        Initialised so the bullet is centred on the tank barrel tip.
    """

    def __init__(
        self,
        x:              int,
        y:              int,
        direction:      Direction,
        owner_id:       int,
        owner_team:     BulletOwner,
        speed_key:      str  = "slow",      # "slow" | "fast"
        destroys_steel: bool = False,
    ) -> None:
        # Swap w/h so the bullet is longer along its travel axis
        if direction in (Direction.UP, Direction.DOWN):
            w, h = BULLET_W_PX, BULLET_H_PX
        else:
            w, h = BULLET_H_PX, BULLET_W_PX

        super().__init__(x=x, y=y, w=w, h=h)

        self._direction:      Direction   = direction
        self._owner_id:       int         = owner_id
        self._owner_team:     BulletOwner = owner_team
        self._speed_px:       int         = BULLET_SPEED_PX[speed_key]
        self._destroys_steel: bool        = destroys_steel

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def owner_id(self) -> int:
        """ID of the tank that fired this bullet."""
        return self._owner_id

    @property
    def owner_team(self) -> BulletOwner:
        return self._owner_team

    @property
    def speed_px(self) -> int:
        return self._speed_px

    @property
    def destroys_steel(self) -> bool:
        """True if this bullet can destroy steel walls (player 3-star)."""
        return self._destroys_steel

    @property
    def is_player_bullet(self) -> bool:
        return self._owner_team == BulletOwner.PLAYER

    @property
    def is_enemy_bullet(self) -> bool:
        return self._owner_team == BulletOwner.ENEMY

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _on_update(self) -> None:
        """Move the bullet by speed_px pixels in its direction."""
        dcol, drow = DIRECTION_DELTA[self._direction]
        self._x += dcol * self._speed_px
        self._y += drow * self._speed_px

    # ------------------------------------------------------------------
    # Factory -- spawn centred on the tank barrel tip
    # ------------------------------------------------------------------

    @classmethod
    def from_tank(
        cls,
        tank_x:         int,
        tank_y:         int,
        tank_w:         int,
        tank_h:         int,
        direction:      Direction,
        owner_id:       int,
        owner_team:     BulletOwner,
        speed_key:      str  = "slow",
        destroys_steel: bool = False,
    ) -> Bullet:
        """
        Spawn a bullet centred on the barrel tip of the tank.

        The bullet is offset so its centre aligns with the tank centre
        and its leading edge starts at the tank edge facing the direction.
        """
        if direction in (Direction.UP, Direction.DOWN):
            bw, bh = BULLET_W_PX, BULLET_H_PX
        else:
            bw, bh = BULLET_H_PX, BULLET_W_PX

        # Centre the bullet on the tank horizontally/vertically
        cx = tank_x + tank_w // 2
        cy = tank_y + tank_h // 2

        if direction == Direction.UP:
            x = cx - bw // 2
            y = tank_y - bh
        elif direction == Direction.DOWN:
            x = cx - bw // 2
            y = tank_y + tank_h
        elif direction == Direction.LEFT:
            x = tank_x - bw
            y = cy - bh // 2
        else:  # RIGHT
            x = tank_x + tank_w
            y = cy - bh // 2

        return cls(
            x=x, y=y,
            direction=direction,
            owner_id=owner_id,
            owner_team=owner_team,
            speed_key=speed_key,
            destroys_steel=destroys_steel,
        )

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "alive" if self.alive else "dead"
        return (
            f"Bullet(id={self.id}, owner={self._owner_id}, "
            f"dir={self._direction.name}, "
            f"x={self.x}, y={self.y}, {status})"
        )