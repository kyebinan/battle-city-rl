"""
battle_city/core/events.py

EventBus -- publish/subscribe communication between game systems.

Pattern: Observer (Design Patterns, Shvets)

Why:
    Game systems (CollisionSystem, ScoreSystem, RewardSystem, Renderer)
    must react to game events without knowing each other.
    EventBus decouples producers (CollisionSystem) from consumers
    (RewardSystem, ScoreSystem) -- neither side holds a reference to the other.

Usage:
    # Subscribe
    bus.subscribe(TankDestroyedEvent, my_callback)

    # Publish
    bus.publish(TankDestroyedEvent(tank_id=3, ...))

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type, TypeVar

from battle_city.core.config import TankType, TankTeam, PowerUpType, Direction


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

E = TypeVar("E", bound="GameEvent")
EventCallback = Callable[["GameEvent"], None]


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GameEvent:
    """Base class for all game events."""


# ---------------------------------------------------------------------------
# Tank events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TankDestroyedEvent(GameEvent):
    """
    Fired when a tank is destroyed.

    killed_by_id:    entity id of the bullet that caused destruction.
                     None if destroyed by CollisionSystem directly (e.g. grenade).
    killed_by_agent: RL agent index of the shooter. None for enemy/scripted tanks.
    """
    tank_id:         int
    tank_type:       TankType
    team:            TankTeam
    x:               int        # pixel position at time of destruction
    y:               int
    killed_by_id:    int | None
    killed_by_agent: int | None  # None for non-RL agents


@dataclass(frozen=True)
class TankSpawnedEvent(GameEvent):
    """Fired when a tank spawns (start of stage or respawn)."""
    tank_id:   int
    tank_type: TankType
    team:      TankTeam
    x:         int
    y:         int


@dataclass(frozen=True)
class TankHitEvent(GameEvent):
    """
    Fired when a tank takes a hit but is NOT destroyed.
    For player tanks: star level was downgraded.
    For armor tanks: HP decremented but still alive.
    """
    tank_id:    int
    tank_type:  TankType
    team:       TankTeam
    hp_after:   int
    star_after: int   # StarLevel value; -1 for enemy tanks


@dataclass(frozen=True)
class TankFrozenEvent(GameEvent):
    """
    Fired when a player tank is hit by a friendly bullet (2-player mode).
    The tank is frozen temporarily but not destroyed.
    """
    tank_id:        int
    frozen_frames:  int


# ---------------------------------------------------------------------------
# Bullet events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BulletFiredEvent(GameEvent):
    """Fired when a tank fires a bullet."""
    bullet_id:  int
    owner_id:   int         # tank entity id
    owner_team: TankTeam
    direction:  Direction
    x:          int
    y:          int


@dataclass(frozen=True)
class BulletHitWallEvent(GameEvent):
    """
    Fired when a bullet hits a wall tile.
    destroyed_tile: True if the wall was destroyed (brick hit).
    """
    bullet_id:      int
    tile_col:       int   # 8px block coordinate
    tile_row:       int
    destroyed_tile: bool


@dataclass(frozen=True)
class BulletHitTankEvent(GameEvent):
    """Fired when a bullet hits a tank (before tank destruction is resolved)."""
    bullet_id:  int
    target_id:  int
    owner_team: TankTeam


@dataclass(frozen=True)
class BulletExpiredEvent(GameEvent):
    """Fired when a bullet leaves the map or is cancelled."""
    bullet_id: int


# ---------------------------------------------------------------------------
# Eagle events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EagleDestroyedEvent(GameEvent):
    """
    Fired when the eagle is hit by any bullet.
    Terminal event -- World triggers game over after publishing this.
    friendly_fire: True if a player bullet hit the eagle.
    """
    bullet_id:     int
    friendly_fire: bool   # True if a player bullet destroyed the base


# ---------------------------------------------------------------------------
# Power-up events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PowerUpSpawnedEvent(GameEvent):
    """
    Fired when a flash tank is hit and a power-up appears.
    Only one power-up can exist on the map at a time.
    """
    powerup_type: PowerUpType
    x:            int
    y:            int


@dataclass(frozen=True)
class PowerUpCollectedEvent(GameEvent):
    """Fired when a player tank collects a power-up."""
    powerup_type:  PowerUpType
    collected_by:  int          # tank entity id
    agent_index:   int | None   # RL agent index; None for scripted players


@dataclass(frozen=True)
class PowerUpExpiredEvent(GameEvent):
    """
    Fired when a power-up disappears without being collected.
    This happens when a second flash tank is hit while a power-up
    is already on the field.
    """
    powerup_type: PowerUpType


# ---------------------------------------------------------------------------
# Stage events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StageStartEvent(GameEvent):
    """Fired at the beginning of a stage."""
    stage:    int | None
    scenario: int | None


@dataclass(frozen=True)
class StageCompleteEvent(GameEvent):
    """
    Fired when all enemies on a stage are destroyed.
    Terminal event -- triggers score screen and next stage load.
    """
    stage:          int | None
    total_score:    int
    enemies_killed: int


@dataclass(frozen=True)
class GameOverEvent(GameEvent):
    """
    Fired when the player loses all lives or the eagle is destroyed.
    reason: "eagle_destroyed" | "no_lives"
    """
    reason:      str
    final_score: int


# ---------------------------------------------------------------------------
# Shovel event (steel eagle protection)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShovelActivatedEvent(GameEvent):
    """Fired when the Shovel power-up replaces eagle bricks with steel."""
    duration_frames: int


@dataclass(frozen=True)
class ShovelExpiredEvent(GameEvent):
    """Fired when the Shovel protection reverts steel back to brick."""


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------

class EventBus:
    """
    Central publish/subscribe event bus.

    Producers call publish() without knowing who listens.
    Consumers call subscribe() without knowing who publishes.

    Thread safety: not thread-safe -- designed for single-threaded 60Hz loop.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[EventCallback]] = {}

    def subscribe(
        self,
        event_type: Type[E],
        callback:   Callable[[E], None],
    ) -> None:
        """
        Register a callback for a specific event type.
        The callback is called synchronously when publish() fires the event.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)  # type: ignore[arg-type]

    def unsubscribe(
        self,
        event_type: Type[E],
        callback:   Callable[[E], None],
    ) -> None:
        """Remove a previously registered callback."""
        listeners = self._subscribers.get(event_type, [])
        if callback in listeners:  # type: ignore[comparison-overlap]
            listeners.remove(callback)  # type: ignore[arg-type]

    def publish(self, event: GameEvent) -> None:
        """
        Dispatch an event to all registered callbacks synchronously.
        Callbacks are called in subscription order.
        """
        for callback in self._subscribers.get(type(event), []):
            callback(event)

    def clear(self) -> None:
        """Remove all subscriptions -- used between stages and in tests."""
        self._subscribers.clear()

    def subscriber_count(self, event_type: type) -> int:
        """Return the number of subscribers for a given event type."""
        return len(self._subscribers.get(event_type, []))