"""
Специализации тестов: все 11 роутеров.
"""
from .oupds import oupds_router
from .ispolniteli import ispolniteli_router
from .aliment import aliment_router
from .doznanie import doznanie_router
from .rozyisk import rozyisk_router
from .prof import prof_router
from .oko import oko_router
from .informatika import informatika_router
from .kadry import kadry_router
from .bezopasnost import bezopasnost_router
from .upravlenie import upravlenie_router

__all__ = [
    "oupds_router",
    "ispolniteli_router",
    "aliment_router",
    "doznanie_router",
    "rozyisk_router",
    "prof_router",
    "oko_router",
    "informatika_router",
    "kadry_router",
    "bezopasnost_router",
    "upravlenie_router",
]
