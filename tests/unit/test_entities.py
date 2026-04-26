"""
tests/unit/test_entities.py

Unit tests for:
    - entity.py  : EntityID, BoundingBox, Entity lifecycle
    - tank.py    : Tank state, hit buffer, star level, bullets
    - bullet.py  : Bullet movement, from_tank factory
    - eagle.py   : Eagle static behaviour, on_hit
"""

import pytest

from battle_city.core.config import (
    Direction, TankType, TankTeam, BulletOwner, StarLevel,
    TANK_PX, TILE_PX, BULLET_W_PX, BULLET_H_PX,
    SPAWN_INVINCIBLE_FRAMES, ICE_SLIDE_FRAMES,
    BULLET_SPEED_PX,
)
from battle_city.core.entities.entity import Entity, EntityID, BoundingBox
from battle_city.core.entities.tank   import Tank
from battle_city.core.entities.bullet import Bullet
from battle_city.core.entities.eagle  import Eagle


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_entity_ids():
    """Reset the EntityID counter before each test."""
    EntityID.reset()
    yield


def make_player(x=0, y=0, direction=Direction.UP) -> Tank:
    return Tank(x=x, y=y, tank_type=TankType.PLAYER, team=TankTeam.PLAYER,
                direction=direction)


def make_enemy(tank_type=TankType.BASIC, x=0, y=0) -> Tank:
    return Tank(x=x, y=y, tank_type=tank_type, team=TankTeam.ENEMY,
                direction=Direction.DOWN)


def make_bullet(direction=Direction.UP, owner_id=1,
                team=BulletOwner.PLAYER) -> Bullet:
    return Bullet(x=100, y=100, direction=direction,
                  owner_id=owner_id, owner_team=team)


# ---------------------------------------------------------------------------
# EntityID
# ---------------------------------------------------------------------------

class TestEntityID:
    def test_starts_at_one(self):
        assert EntityID.next() == 1

    def test_increments(self):
        a = EntityID.next()
        b = EntityID.next()
        assert b == a + 1

    def test_reset(self):
        EntityID.next()
        EntityID.reset()
        assert EntityID.next() == 1


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_right_bottom(self):
        bb = BoundingBox(10, 20, 16, 16)
        assert bb.right  == 26
        assert bb.bottom == 36

    def test_centre(self):
        bb = BoundingBox(0, 0, 16, 16)
        assert bb.cx == 8 and bb.cy == 8

    def test_intersects_overlap(self):
        a = BoundingBox(0, 0, 16, 16)
        b = BoundingBox(8, 8, 16, 16)
        assert a.intersects(b) is True

    def test_intersects_adjacent_no_overlap(self):
        a = BoundingBox(0, 0, 16, 16)
        b = BoundingBox(16, 0, 16, 16)
        assert a.intersects(b) is False

    def test_intersects_no_overlap(self):
        a = BoundingBox(0,  0, 8, 8)
        b = BoundingBox(20, 0, 8, 8)
        assert a.intersects(b) is False

    def test_contains_point_inside(self):
        bb = BoundingBox(0, 0, 16, 16)
        assert bb.contains_point(8, 8)  is True
        assert bb.contains_point(0, 0)  is True
        assert bb.contains_point(15, 15) is True

    def test_contains_point_outside(self):
        bb = BoundingBox(0, 0, 16, 16)
        assert bb.contains_point(16, 0) is False
        assert bb.contains_point(-1, 0) is False

    def test_moved(self):
        bb = BoundingBox(0, 0, 16, 16)
        moved = bb.moved(10, 20)
        assert moved.x == 10 and moved.y == 20
        assert moved.w == 16 and moved.h == 16

    def test_equality(self):
        assert BoundingBox(1, 2, 3, 4) == BoundingBox(1, 2, 3, 4)
        assert BoundingBox(1, 2, 3, 4) != BoundingBox(0, 2, 3, 4)


# ---------------------------------------------------------------------------
# Entity (via Tank as concrete subclass)
# ---------------------------------------------------------------------------

class TestEntityBase:
    def test_unique_ids(self):
        a = make_player()
        b = make_player()
        assert a.id != b.id

    def test_alive_on_creation(self):
        t = make_player()
        assert t.alive is True

    def test_destroy(self):
        t = make_player()
        t.destroy()
        assert t.alive is False

    def test_update_skips_when_dead(self):
        t = make_player()
        t.destroy()
        t.update()   # should not raise

    def test_bbox_position(self):
        t = make_player(x=32, y=64)
        assert t.bbox.x == 32
        assert t.bbox.y == 64
        assert t.bbox.w == TANK_PX
        assert t.bbox.h == TANK_PX

    def test_x_y_setters(self):
        t = make_player(x=0, y=0)
        t.x = 50
        t.y = 80
        assert t.x == 50 and t.y == 80


# ---------------------------------------------------------------------------
# Tank
# ---------------------------------------------------------------------------

class TestTankCreation:
    def test_player_fields(self):
        t = make_player(x=64, y=192)
        assert t.tank_type   == TankType.PLAYER
        assert t.team        == TankTeam.PLAYER
        assert t.is_player   is True
        assert t.is_enemy    is False
        assert t.direction   == Direction.UP
        assert t.x == 64 and t.y == 192

    def test_enemy_fields(self):
        t = make_enemy(TankType.FAST)
        assert t.tank_type == TankType.FAST
        assert t.team      == TankTeam.ENEMY
        assert t.is_enemy  is True

    def test_initial_star_level(self):
        t = make_player()
        assert t.star_level == StarLevel.BASE

    def test_spawns_invincible(self):
        t = make_player()
        assert t.invincible is True

    def test_no_bullets_on_creation(self):
        t = make_player()
        assert t.bullet_count == 0
        assert t.can_fire     is True


class TestTankHitBuffer:
    """
    Player tank hit buffer via star level:
        STAR_3 -> hit -> STAR_2 (survives)
        STAR_2 -> hit -> STAR_1 (survives)
        STAR_1 -> hit -> BASE   (survives)
        BASE   -> hit -> destroyed
    """

    def test_hit_at_star3_downgrades_to_star2(self):
        t = make_player()
        t._star_level = StarLevel.STAR_3
        destroyed = t.take_hit()
        assert destroyed          is False
        assert t.alive            is True
        assert t.star_level       == StarLevel.STAR_2

    def test_hit_at_star2_downgrades_to_star1(self):
        t = make_player()
        t._star_level = StarLevel.STAR_2
        destroyed = t.take_hit()
        assert destroyed    is False
        assert t.star_level == StarLevel.STAR_1

    def test_hit_at_star1_downgrades_to_base(self):
        t = make_player()
        t._star_level = StarLevel.STAR_1
        destroyed = t.take_hit()
        assert destroyed    is False
        assert t.star_level == StarLevel.BASE

    def test_hit_at_base_destroys_player(self):
        t = make_player()
        t._star_level = StarLevel.BASE
        destroyed = t.take_hit()
        assert destroyed is True
        assert t.alive   is False

    def test_three_hits_from_star3_destroy_at_fourth(self):
        t = make_player()
        t._star_level = StarLevel.STAR_3
        assert t.take_hit() is False   # -> STAR_2
        assert t.take_hit() is False   # -> STAR_1
        assert t.take_hit() is False   # -> BASE
        assert t.take_hit() is True    # destroyed


class TestTankEnemy:
    def test_basic_destroyed_in_one_hit(self):
        t = make_enemy(TankType.BASIC)
        assert t.take_hit() is True
        assert t.alive      is False

    def test_armor_survives_three_hits(self):
        t = make_enemy(TankType.ARMOR)
        assert t.take_hit() is False
        assert t.take_hit() is False
        assert t.take_hit() is False
        assert t.alive      is True

    def test_armor_destroyed_on_fourth_hit(self):
        t = make_enemy(TankType.ARMOR)
        for _ in range(3):
            t.take_hit()
        assert t.take_hit() is True
        assert t.alive      is False


class TestTankStarUpgrade:
    def test_add_star_increments(self):
        t = make_player()
        t.add_star()
        assert t.star_level == StarLevel.STAR_1

    def test_add_star_capped_at_star3(self):
        t = make_player()
        t._star_level = StarLevel.STAR_3
        t.add_star()
        assert t.star_level == StarLevel.STAR_3

    def test_reset_stars(self):
        t = make_player()
        t._star_level = StarLevel.STAR_3
        t.reset_stars()
        assert t.star_level == StarLevel.BASE

    def test_base_bullet_is_slow(self):
        t = make_player()
        assert t.bullet_speed == "slow"

    def test_star1_bullet_is_fast(self):
        t = make_player()
        t.add_star()
        assert t.bullet_speed == "fast"

    def test_base_max_one_bullet(self):
        t = make_player()
        assert t.max_bullets == 1

    def test_star2_max_two_bullets(self):
        t = make_player()
        t._star_level = StarLevel.STAR_2
        assert t.max_bullets == 2

    def test_only_star3_destroys_steel(self):
        t = make_player()
        for lv in (StarLevel.BASE, StarLevel.STAR_1, StarLevel.STAR_2):
            t._star_level = lv
            assert t.can_destroy_steel is False
        t._star_level = StarLevel.STAR_3
        assert t.can_destroy_steel is True

    def test_enemy_cannot_destroy_steel(self):
        t = make_enemy()
        assert t.can_destroy_steel is False

    def test_enemy_max_one_bullet(self):
        t = make_enemy()
        assert t.max_bullets == 1


class TestTankBulletTracking:
    def test_register_bullet(self):
        t = make_player()
        t.register_bullet(42)
        assert t.bullet_count == 1
        assert t.can_fire is False   # max=1 à BASE, déjà 1 balle on screen

    def test_can_fire_false_when_at_max(self):
        t = make_player()
        t.register_bullet(1)
        assert t.can_fire is False

    def test_unregister_bullet(self):
        t = make_player()
        t.register_bullet(1)
        t.unregister_bullet(1)
        assert t.bullet_count == 0
        assert t.can_fire     is True

    def test_star2_can_have_two_bullets(self):
        t = make_player()
        t._star_level = StarLevel.STAR_2
        t.register_bullet(1)
        assert t.can_fire is True
        t.register_bullet(2)
        assert t.can_fire is False


class TestTankInvincibility:
    def test_invincible_on_spawn(self):
        t = make_player()
        assert t.invincible is True

    def test_invincibility_expires(self):
        t = make_player()
        for _ in range(SPAWN_INVINCIBLE_FRAMES):
            t.update()
        assert t.invincible is False

    def test_grant_invincibility(self):
        t = make_player()
        t._invincible_frames = 0
        t.grant_invincibility(120)
        assert t.invincible is True


class TestTankIce:
    def test_not_sliding_initially(self):
        t = make_player()
        assert t.sliding is False

    def test_start_slide(self):
        t = make_player()
        t.start_slide()
        assert t.sliding is True

    def test_slide_expires(self):
        t = make_player()
        t.start_slide()
        for _ in range(ICE_SLIDE_FRAMES):
            t.update()
        assert t.sliding is False


# ---------------------------------------------------------------------------
# Bullet
# ---------------------------------------------------------------------------

class TestBulletCreation:
    def test_vertical_bullet_dimensions(self):
        b = Bullet(x=0, y=0, direction=Direction.UP,
                   owner_id=1, owner_team=BulletOwner.PLAYER)
        assert b.w == BULLET_W_PX
        assert b.h == BULLET_H_PX

    def test_horizontal_bullet_dimensions(self):
        b = Bullet(x=0, y=0, direction=Direction.RIGHT,
                   owner_id=1, owner_team=BulletOwner.PLAYER)
        assert b.w == BULLET_H_PX   # swapped
        assert b.h == BULLET_W_PX

    def test_owner_fields(self):
        b = make_bullet(owner_id=7, team=BulletOwner.ENEMY)
        assert b.owner_id   == 7
        assert b.owner_team == BulletOwner.ENEMY
        assert b.is_enemy_bullet  is True
        assert b.is_player_bullet is False

    def test_slow_speed(self):
        b = Bullet(x=0, y=0, direction=Direction.UP,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   speed_key="slow")
        assert b.speed_px == BULLET_SPEED_PX["slow"]

    def test_fast_speed(self):
        b = Bullet(x=0, y=0, direction=Direction.UP,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   speed_key="fast")
        assert b.speed_px == BULLET_SPEED_PX["fast"]

    def test_destroys_steel_false_by_default(self):
        b = make_bullet()
        assert b.destroys_steel is False

    def test_destroys_steel_true(self):
        b = Bullet(x=0, y=0, direction=Direction.UP,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   destroys_steel=True)
        assert b.destroys_steel is True


class TestBulletMovement:
    def test_moves_up(self):
        b = Bullet(x=100, y=100, direction=Direction.UP,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   speed_key="slow")
        b.update()
        assert b.y < 100
        assert b.x == 100

    def test_moves_down(self):
        b = Bullet(x=100, y=100, direction=Direction.DOWN,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   speed_key="slow")
        b.update()
        assert b.y > 100

    def test_moves_left(self):
        b = Bullet(x=100, y=100, direction=Direction.LEFT,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   speed_key="slow")
        b.update()
        assert b.x < 100

    def test_moves_right(self):
        b = Bullet(x=100, y=100, direction=Direction.RIGHT,
                   owner_id=1, owner_team=BulletOwner.PLAYER,
                   speed_key="slow")
        b.update()
        assert b.x > 100

    def test_speed_affects_distance(self):
        slow = Bullet(x=0, y=200, direction=Direction.UP,
                      owner_id=1, owner_team=BulletOwner.PLAYER,
                      speed_key="slow")
        fast = Bullet(x=0, y=200, direction=Direction.UP,
                      owner_id=1, owner_team=BulletOwner.PLAYER,
                      speed_key="fast")
        slow.update()
        fast.update()
        assert fast.y < slow.y   # fast moved further up

    def test_no_movement_when_dead(self):
        b = make_bullet()
        b.destroy()
        y_before = b.y
        b.update()
        assert b.y == y_before


class TestBulletFromTank:
    def test_up_bullet_spawns_above_tank(self):
        b = Bullet.from_tank(
            tank_x=64, tank_y=192, tank_w=TANK_PX, tank_h=TANK_PX,
            direction=Direction.UP,
            owner_id=1, owner_team=BulletOwner.PLAYER,
        )
        assert b.y < 192

    def test_down_bullet_spawns_below_tank(self):
        b = Bullet.from_tank(
            tank_x=64, tank_y=192, tank_w=TANK_PX, tank_h=TANK_PX,
            direction=Direction.DOWN,
            owner_id=1, owner_team=BulletOwner.PLAYER,
        )
        assert b.y > 192

    def test_left_bullet_spawns_left_of_tank(self):
        b = Bullet.from_tank(
            tank_x=64, tank_y=192, tank_w=TANK_PX, tank_h=TANK_PX,
            direction=Direction.LEFT,
            owner_id=1, owner_team=BulletOwner.PLAYER,
        )
        assert b.x < 64

    def test_right_bullet_spawns_right_of_tank(self):
        b = Bullet.from_tank(
            tank_x=64, tank_y=192, tank_w=TANK_PX, tank_h=TANK_PX,
            direction=Direction.RIGHT,
            owner_id=1, owner_team=BulletOwner.PLAYER,
        )
        assert b.x > 64


# ---------------------------------------------------------------------------
# Eagle
# ---------------------------------------------------------------------------

class TestEagle:
    def test_size(self):
        e = Eagle(x=96, y=192)
        assert e.w == TILE_PX and e.h == TILE_PX

    def test_alive_on_creation(self):
        e = Eagle(x=96, y=192)
        assert e.alive     is True
        assert e.destroyed is False

    def test_direction_is_up(self):
        e = Eagle(x=96, y=192)
        assert e.direction == Direction.UP

    def test_sprite_index_alive(self):
        e = Eagle(x=96, y=192)
        assert e.sprite_index == Eagle.SPRITE_ALIVE

    def test_on_hit_destroys(self):
        e = Eagle(x=96, y=192)
        e.on_hit()
        assert e.destroyed    is True
        assert e.alive        is False
        assert e.sprite_index == Eagle.SPRITE_DESTROYED

    def test_on_hit_idempotent(self):
        e = Eagle(x=96, y=192)
        e.on_hit()
        e.on_hit()   # second call must not raise
        assert e.destroyed is True

    def test_update_does_nothing(self):
        e = Eagle(x=96, y=192)
        e.update()
        assert e.alive is True