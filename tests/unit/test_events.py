"""
tests/unit/test_events.py

Unit tests for battle_city/core/events.py

Coverage:
    - All event dataclasses: frozen, correct fields
    - EventBus: subscribe, publish, unsubscribe, clear
    - EventBus: multiple subscribers per event type
    - EventBus: unknown event type publishes silently
    - EventBus: subscriber_count
    - RewardSystem integration sketch: events drive reward accumulation
"""

import pytest

from battle_city.core.config import (
    TankType, TankTeam, PowerUpType, Direction,
)
from battle_city.core.events import (
    EventBus, GameEvent,
    TankDestroyedEvent, TankSpawnedEvent, TankHitEvent, TankFrozenEvent,
    BulletFiredEvent, BulletHitWallEvent, BulletHitTankEvent, BulletExpiredEvent,
    EagleDestroyedEvent,
    PowerUpSpawnedEvent, PowerUpCollectedEvent, PowerUpExpiredEvent,
    StageStartEvent, StageCompleteEvent, GameOverEvent,
    ShovelActivatedEvent, ShovelExpiredEvent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus() -> EventBus:
    return EventBus()


def make_tank_destroyed(**kwargs) -> TankDestroyedEvent:
    defaults = dict(
        tank_id=1, tank_type=TankType.BASIC, team=TankTeam.ENEMY,
        x=64, y=0, killed_by_id=10, killed_by_agent=0,
    )
    return TankDestroyedEvent(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Event dataclasses -- frozen and correct fields
# ---------------------------------------------------------------------------

class TestEventDataclasses:

    def test_tank_destroyed_frozen(self):
        e = make_tank_destroyed()
        with pytest.raises(Exception):
            e.tank_id = 99  # type: ignore

    def test_tank_destroyed_fields(self):
        e = make_tank_destroyed(tank_id=5, team=TankTeam.PLAYER,
                                killed_by_agent=None)
        assert e.tank_id         == 5
        assert e.team            == TankTeam.PLAYER
        assert e.killed_by_agent is None

    def test_tank_spawned(self):
        e = TankSpawnedEvent(tank_id=1, tank_type=TankType.FAST,
                             team=TankTeam.ENEMY, x=0, y=0)
        assert e.tank_type == TankType.FAST

    def test_tank_hit(self):
        e = TankHitEvent(tank_id=1, tank_type=TankType.ARMOR,
                         team=TankTeam.ENEMY, hp_after=3, star_after=-1)
        assert e.hp_after == 3

    def test_tank_frozen(self):
        e = TankFrozenEvent(tank_id=2, frozen_frames=30)
        assert e.frozen_frames == 30

    def test_bullet_fired(self):
        e = BulletFiredEvent(bullet_id=1, owner_id=2,
                             owner_team=TankTeam.PLAYER,
                             direction=Direction.UP, x=64, y=192)
        assert e.direction == Direction.UP

    def test_bullet_hit_wall(self):
        e = BulletHitWallEvent(bullet_id=1, tile_col=3, tile_row=5,
                               destroyed_tile=True)
        assert e.destroyed_tile is True

    def test_bullet_hit_tank(self):
        e = BulletHitTankEvent(bullet_id=1, target_id=2,
                               owner_team=TankTeam.PLAYER)
        assert e.target_id == 2

    def test_bullet_expired(self):
        e = BulletExpiredEvent(bullet_id=7)
        assert e.bullet_id == 7

    def test_eagle_destroyed(self):
        e = EagleDestroyedEvent(bullet_id=3, friendly_fire=True)
        assert e.friendly_fire is True

    def test_eagle_destroyed_enemy(self):
        e = EagleDestroyedEvent(bullet_id=3, friendly_fire=False)
        assert e.friendly_fire is False

    def test_powerup_spawned(self):
        e = PowerUpSpawnedEvent(powerup_type=PowerUpType.STAR, x=96, y=64)
        assert e.powerup_type == PowerUpType.STAR

    def test_powerup_collected(self):
        e = PowerUpCollectedEvent(powerup_type=PowerUpType.TANK,
                                  collected_by=1, agent_index=0)
        assert e.agent_index == 0

    def test_powerup_collected_no_agent(self):
        e = PowerUpCollectedEvent(powerup_type=PowerUpType.HELMET,
                                  collected_by=1, agent_index=None)
        assert e.agent_index is None

    def test_powerup_expired(self):
        e = PowerUpExpiredEvent(powerup_type=PowerUpType.CLOCK)
        assert e.powerup_type == PowerUpType.CLOCK

    def test_stage_start(self):
        e = StageStartEvent(stage=1, scenario=None)
        assert e.stage == 1 and e.scenario is None

    def test_stage_complete(self):
        e = StageCompleteEvent(stage=1, total_score=2400, enemies_killed=20)
        assert e.enemies_killed == 20

    def test_game_over(self):
        e = GameOverEvent(reason="eagle_destroyed", final_score=1500)
        assert e.reason == "eagle_destroyed"

    def test_shovel_activated(self):
        e = ShovelActivatedEvent(duration_frames=1200)
        assert e.duration_frames == 1200

    def test_shovel_expired(self):
        e = ShovelExpiredEvent()
        assert isinstance(e, GameEvent)


# ---------------------------------------------------------------------------
# EventBus -- subscribe / publish
# ---------------------------------------------------------------------------

class TestEventBusSubscribe:

    def test_subscriber_receives_event(self, bus: EventBus):
        received = []
        bus.subscribe(TankDestroyedEvent, received.append)
        event = make_tank_destroyed()
        bus.publish(event)
        assert len(received) == 1
        assert received[0] is event

    def test_multiple_subscribers_all_called(self, bus: EventBus):
        results_a: list[GameEvent] = []
        results_b: list[GameEvent] = []
        bus.subscribe(TankDestroyedEvent, results_a.append)
        bus.subscribe(TankDestroyedEvent, results_b.append)
        bus.publish(make_tank_destroyed())
        assert len(results_a) == 1
        assert len(results_b) == 1

    def test_subscriber_only_receives_its_type(self, bus: EventBus):
        tank_events:   list[GameEvent] = []
        bullet_events: list[GameEvent] = []
        bus.subscribe(TankDestroyedEvent, tank_events.append)
        bus.subscribe(BulletFiredEvent,   bullet_events.append)

        bus.publish(make_tank_destroyed())
        assert len(tank_events)   == 1
        assert len(bullet_events) == 0

        bus.publish(BulletFiredEvent(
            bullet_id=1, owner_id=2, owner_team=TankTeam.PLAYER,
            direction=Direction.UP, x=0, y=0,
        ))
        assert len(bullet_events) == 1
        assert len(tank_events)   == 1   # unchanged

    def test_unknown_event_type_no_crash(self, bus: EventBus):
        """Publishing an event with no subscribers must not raise."""
        bus.publish(make_tank_destroyed())   # no subscribers registered

    def test_publish_calls_in_subscription_order(self, bus: EventBus):
        order: list[str] = []
        bus.subscribe(TankDestroyedEvent, lambda e: order.append("first"))
        bus.subscribe(TankDestroyedEvent, lambda e: order.append("second"))
        bus.publish(make_tank_destroyed())
        assert order == ["first", "second"]

    def test_multiple_publishes_accumulate(self, bus: EventBus):
        received: list[GameEvent] = []
        bus.subscribe(TankDestroyedEvent, received.append)
        bus.publish(make_tank_destroyed())
        bus.publish(make_tank_destroyed())
        bus.publish(make_tank_destroyed())
        assert len(received) == 3


# ---------------------------------------------------------------------------
# EventBus -- unsubscribe
# ---------------------------------------------------------------------------

class TestEventBusUnsubscribe:

    def test_unsubscribe_stops_delivery(self, bus: EventBus):
        received: list[GameEvent] = []
        bus.subscribe(TankDestroyedEvent, received.append)
        bus.publish(make_tank_destroyed())
        assert len(received) == 1

        bus.unsubscribe(TankDestroyedEvent, received.append)
        bus.publish(make_tank_destroyed())
        assert len(received) == 1   # no new event

    def test_unsubscribe_unknown_callback_no_crash(self, bus: EventBus):
        """Unsubscribing a callback that was never registered must not raise."""
        bus.unsubscribe(TankDestroyedEvent, lambda e: None)

    def test_unsubscribe_one_of_two(self, bus: EventBus):
        results_a: list[GameEvent] = []
        results_b: list[GameEvent] = []

        cb_a = results_a.append
        cb_b = results_b.append

        bus.subscribe(TankDestroyedEvent, cb_a)
        bus.subscribe(TankDestroyedEvent, cb_b)
        bus.unsubscribe(TankDestroyedEvent, cb_a)
        bus.publish(make_tank_destroyed())

        assert len(results_a) == 0
        assert len(results_b) == 1


# ---------------------------------------------------------------------------
# EventBus -- clear
# ---------------------------------------------------------------------------

class TestEventBusClear:

    def test_clear_removes_all_subscribers(self, bus: EventBus):
        received: list[GameEvent] = []
        bus.subscribe(TankDestroyedEvent, received.append)
        bus.subscribe(BulletFiredEvent,   received.append)
        bus.clear()
        bus.publish(make_tank_destroyed())
        assert len(received) == 0

    def test_clear_then_resubscribe(self, bus: EventBus):
        received: list[GameEvent] = []
        bus.subscribe(TankDestroyedEvent, received.append)
        bus.clear()
        bus.subscribe(TankDestroyedEvent, received.append)
        bus.publish(make_tank_destroyed())
        assert len(received) == 1


# ---------------------------------------------------------------------------
# EventBus -- subscriber_count
# ---------------------------------------------------------------------------

class TestEventBusSubscriberCount:

    def test_zero_before_subscribe(self, bus: EventBus):
        assert bus.subscriber_count(TankDestroyedEvent) == 0

    def test_one_after_subscribe(self, bus: EventBus):
        bus.subscribe(TankDestroyedEvent, lambda e: None)
        assert bus.subscriber_count(TankDestroyedEvent) == 1

    def test_two_after_two_subscribes(self, bus: EventBus):
        bus.subscribe(TankDestroyedEvent, lambda e: None)
        bus.subscribe(TankDestroyedEvent, lambda e: None)
        assert bus.subscriber_count(TankDestroyedEvent) == 2

    def test_count_per_type_independent(self, bus: EventBus):
        bus.subscribe(TankDestroyedEvent, lambda e: None)
        bus.subscribe(BulletFiredEvent,   lambda e: None)
        bus.subscribe(BulletFiredEvent,   lambda e: None)
        assert bus.subscriber_count(TankDestroyedEvent) == 1
        assert bus.subscriber_count(BulletFiredEvent)   == 2

    def test_count_decrements_on_unsubscribe(self, bus: EventBus):
        cb = lambda e: None
        bus.subscribe(TankDestroyedEvent, cb)
        bus.unsubscribe(TankDestroyedEvent, cb)
        assert bus.subscriber_count(TankDestroyedEvent) == 0


# ---------------------------------------------------------------------------
# Reward system integration sketch
# ---------------------------------------------------------------------------

class TestRewardSystemIntegration:
    """
    Verify that a minimal RewardSystem driven by EventBus events
    accumulates rewards correctly.
    This is a sketch -- the real RewardSystem lives in the RL layer.
    """

    def test_enemy_kill_gives_positive_reward(self, bus: EventBus):
        rewards = [0.0]

        def on_tank_destroyed(event: TankDestroyedEvent):
            if event.team == TankTeam.ENEMY:
                rewards[0] += 1.0

        bus.subscribe(TankDestroyedEvent, on_tank_destroyed)
        bus.publish(make_tank_destroyed(team=TankTeam.ENEMY))
        assert rewards[0] > 0.0

    def test_ally_killed_gives_negative_reward(self, bus: EventBus):
        rewards = [0.0]

        def on_tank_destroyed(event: TankDestroyedEvent):
            if event.team == TankTeam.PLAYER:
                rewards[0] -= 2.0

        bus.subscribe(TankDestroyedEvent, on_tank_destroyed)
        bus.publish(make_tank_destroyed(team=TankTeam.PLAYER))
        assert rewards[0] < 0.0

    def test_eagle_destroyed_large_negative_reward(self, bus: EventBus):
        rewards = [0.0]

        def on_eagle(event: EagleDestroyedEvent):
            rewards[0] -= 5.0

        bus.subscribe(EagleDestroyedEvent, on_eagle)
        bus.publish(EagleDestroyedEvent(bullet_id=1, friendly_fire=False))
        assert rewards[0] == -5.0

    def test_stage_complete_positive_reward(self, bus: EventBus):
        rewards = [0.0]

        def on_stage(event: StageCompleteEvent):
            rewards[0] += 5.0

        bus.subscribe(StageCompleteEvent, on_stage)
        bus.publish(StageCompleteEvent(stage=1, total_score=2400,
                                       enemies_killed=20))
        assert rewards[0] == 5.0

    def test_multiple_events_accumulate(self, bus: EventBus):
        rewards = [0.0]

        def on_tank(e: TankDestroyedEvent):
            if e.team == TankTeam.ENEMY:
                rewards[0] += 1.0

        bus.subscribe(TankDestroyedEvent, on_tank)
        for _ in range(5):
            bus.publish(make_tank_destroyed(team=TankTeam.ENEMY))
        assert rewards[0] == 5.0