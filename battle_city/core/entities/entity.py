"""
battle_city/core/entities/entity.py

Entity -- abstract base class for all game objects.

Defines the common interface shared by Tank, Bullet, and Eagle.

Design:
    - Entity uses x,y pixel coordinates (top-left of sprite)
    - No pygame dependency -- rendering is handled by the renderer layer
    - Pattern: Template Method -- subclasses override _on_update()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from battle_city.core.config import Direction


# ---------------------------------------------------------------------------
# EntityID
# ---------------------------------------------------------------------------

class EntityID:
    """Auto-incrementing unique integer ID assigned to each entity."""
    _counter: ClassVar[int] = 0

    @classmethod
    def next(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def reset(cls) -> None:
        """Reset counter -- used in tests only."""
        cls._counter = 0


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------

class BoundingBox:
    """
    Axis-aligned bounding box in pixel coordinates.
    x, y: top-left corner.
    w, h: width and height in pixels.
    """

    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    def intersects(self, other: BoundingBox) -> bool:
        """Return True if this box overlaps with other (AABB test)."""
        return (
            self.x      < other.right  and
            self.right  > other.x      and
            self.y      < other.bottom and
            self.bottom > other.y
        )

    def contains_point(self, px: int, py: int) -> bool:
        return self.x <= px < self.right and self.y <= py < self.bottom

    def moved(self, dx: int, dy: int) -> BoundingBox:
        """Return a new BoundingBox translated by (dx, dy)."""
        return BoundingBox(self.x + dx, self.y + dy, self.w, self.h)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BoundingBox):
            return NotImplemented
        return (self.x, self.y, self.w, self.h) == (other.x, other.y, other.w, other.h)

    def __repr__(self) -> str:
        return f"BoundingBox(x={self.x}, y={self.y}, w={self.w}, h={self.h})"


# ---------------------------------------------------------------------------
# Entity -- abstract base
# ---------------------------------------------------------------------------

class Entity(ABC):
    """
    Abstract base class for all game objects (Tank, Bullet, Eagle).

    Coordinates:
        x, y -- top-left pixel position of the sprite.

    Lifecycle:
        alive   -- True while the entity is active in the world.
        update() -- advance one physics frame (called at 60Hz).
        destroy() -- mark as dead; World removes it on the next cleanup.

    Pattern -- Template Method:
        update() calls _on_update() which each subclass implements.
    """

    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self._id:    int  = EntityID.next()
        self._x:     int  = x
        self._y:     int  = y
        self._w:     int  = w
        self._h:     int  = h
        self._alive: bool = True

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def id(self) -> int:
        return self._id

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, value: int) -> None:
        self._x = value

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, value: int) -> None:
        self._y = value

    @property
    def w(self) -> int:
        return self._w

    @property
    def h(self) -> int:
        return self._h

    @property
    def bbox(self) -> BoundingBox:
        """Current axis-aligned bounding box."""
        return BoundingBox(self._x, self._y, self._w, self._h)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def alive(self) -> bool:
        return self._alive

    def destroy(self) -> None:
        """Mark this entity as dead. World removes it after the frame."""
        self._alive = False

    # ------------------------------------------------------------------
    # Update -- Template Method
    # ------------------------------------------------------------------

    def update(self) -> None:
        """
        Advance the entity by one physics frame (1/60s).
        Skips silently if already dead.
        """
        if not self._alive:
            return
        self._on_update()

    @abstractmethod
    def _on_update(self) -> None:
        """Subclass update logic -- called once per frame."""

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def direction(self) -> Direction:
        """Current facing direction."""

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "alive" if self._alive else "dead"
        return (
            f"{self.__class__.__name__}("
            f"id={self._id}, x={self._x}, y={self._y}, {status})"
        )