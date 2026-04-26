"""
battle_city/core/entities/eagle.py

Eagle -- the player base (falcon emblem).

The Eagle is a static entity -- it never moves.
If any bullet (player or enemy) hits the Eagle, the game ends immediately.

State:
    alive   -- True at the start of each stage.
    destroyed -- False until a bullet hits; then True and game over is triggered.

The Eagle is surrounded by BRICK on stage start.
The Shovel power-up temporarily replaces those bricks with STEEL.
"""

from __future__ import annotations

from battle_city.core.config import Direction, TILE_PX
from battle_city.core.entities.entity import Entity


class Eagle(Entity):
    """
    The player base (eagle / falcon emblem).

    Always 16x16 pixels (one logical tile).
    Static -- never moves, never fires.

    Destruction triggers an immediate game-over event via EventBus.
    """

    # Eagle sprite has two states: alive (0) and destroyed (1)
    SPRITE_ALIVE:     int = 0
    SPRITE_DESTROYED: int = 1

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x=x, y=y, w=TILE_PX, h=TILE_PX)
        self._destroyed: bool = False

    # ------------------------------------------------------------------
    # Direction -- required by Entity interface (eagle never moves)
    # ------------------------------------------------------------------

    @property
    def direction(self) -> Direction:
        """Eagle has no direction -- returns UP as a neutral default."""
        return Direction.UP

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def destroyed(self) -> bool:
        """True after the eagle has been hit by any bullet."""
        return self._destroyed

    @property
    def sprite_index(self) -> int:
        """0 = alive sprite, 1 = destroyed sprite."""
        return self.SPRITE_DESTROYED if self._destroyed else self.SPRITE_ALIVE

    def on_hit(self) -> None:
        """
        Called by CollisionSystem when any bullet reaches the eagle.
        Marks the eagle as destroyed -- World will fire EagleDestroyedEvent.
        """
        if not self._destroyed:
            self._destroyed = True
            self.destroy()

    # ------------------------------------------------------------------
    # Update -- eagle is static, nothing to do each frame
    # ------------------------------------------------------------------

    def _on_update(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        state = "destroyed" if self._destroyed else "alive"
        return f"Eagle(id={self.id}, x={self.x}, y={self.y}, {state})"