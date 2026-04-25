"""
battle_city/render/sprite_loader.py

SpriteLoader -- Singleton asset cache for all terrain tile sprites.

Must be initialised AFTER pygame.display.set_mode().
"""

from __future__ import annotations
from pathlib import Path
import pygame


class SpriteLoader:
    """
    Singleton sprite cache.

    First call:   SpriteLoader.instance(assets_dir)
    Later calls:  SpriteLoader.instance()
    """

    _instance: "SpriteLoader | None" = None

    _assets: Path
    _cache:  dict   # dict[str, pygame.Surface]

    def __new__(cls) -> "SpriteLoader":
        raise TypeError("Use SpriteLoader.instance(assets_dir).")

    def _init(self, assets_dir: Path) -> None:
        self._assets = assets_dir
        self._cache  = {}
        self._load_all()

    @classmethod
    def instance(cls, assets_dir: "Path | None" = None) -> "SpriteLoader":
        """
        Return the singleton.
        Must be called AFTER pygame.display.set_mode() on first use.
        """
        if cls._instance is None:
            if assets_dir is None:
                raise ValueError("assets_dir required on first call.")
            obj = object.__new__(cls)
            obj._init(Path(assets_dir))
            cls._instance = obj
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Clear singleton -- for tests and hot-reload."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def get(self, key: str) -> pygame.Surface:
        if key not in self._cache:
            raise KeyError(f"Unknown sprite key: '{key}'")
        return self._cache[key]

    def has(self, key: str) -> bool:
        return key in self._cache

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        d = self._assets
        self._load("brick",  d / "tiles/bricks/brick_0.png")
        self._load("steel",  d / "tiles/steel/steel_0.png")
        self._load("water",  d / "tiles/water/water_0.png")
        self._load("forest", d / "tiles/others/grass_0.png")
        self._load("ice",    d / "tiles/others/ice_0.png")
        self._load("eagle",           d / "sprites/eagle/0.png")
        self._load("eagle_destroyed", d / "sprites/eagle/1.png")

        empty = pygame.Surface((8, 8))
        empty.fill((0, 0, 0))
        self._cache["empty"] = empty

    def _load(self, key: str, path: Path) -> None:
        if not path.exists():
            print(f"[SpriteLoader] WARNING missing: {path}")
            fb = pygame.Surface((16, 16))
            fb.fill((255, 0, 255))   # magenta = missing asset
            self._cache[key] = fb
            return
        self._cache[key] = pygame.image.load(str(path)).convert_alpha()


# TileType int -> sprite key
TILE_SPRITE_KEY: dict[int, str] = {
    0: "empty",
    1: "brick",
    2: "steel",
    3: "water",
    4: "forest",
    5: "ice",
}