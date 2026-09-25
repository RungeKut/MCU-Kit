# -*- coding: utf-8 -*-
"""mcukit — сборка и прошивка микроконтроллеров Cortex-M из Python.

Проверенное поведение, ловушки и приёмы — в knowledge/ (начинать с
knowledge/INDEX.md).

Быстрый старт (GD32 — J-Link):

    import mcukit as mk

    mk.utf8_console()
    r = mk.build(r"D:\\проект\\прошивка").check()     # make + gcc над копией
    print(mk.probe())                                # зонд, VTref
    print(mk.info())                                 # ядро: только чтение
    mk.flash(r.bin, device="GD32F470VK", min_vtref=3.1)
    mk.watch(mk.symbol(r.elf, "blink_count"))        # код идёт?

Порядок подключения — knowledge/20_ПРИЁМЫ/20-01: сначала зонд и VTref,
потом ядро профилем Cortex-M4, и только потом профиль чипа.

Штатные чипы ST (не GD32) — вторым зондом, ST-Link, через
`mcukit.stlink` (см. его docstring и knowledge/40_СРЕДА/40-03):

    print(mk.stlink.probe())                        # зонды, к чипу не лезет
    print(mk.stlink.info())                         # connect: ID, флеш, В
    mk.stlink.flash(r.bin, addr=0x08000000)

Какой зонд для какого чипа — knowledge/20_ПРИЁМЫ/20-04.
"""

__version__ = "0.1.0"

from . import stlink
from .env import (gcc_bin, gcc_tool, gcc_version, is_safe_path, jlink_dir,
                  jlink_exe, jlink_version, kit_root, make_exe, stlink_cli,
                  stlink_version, utf8_console, work_root)
from .jlink import (GENERIC_CORE, JLinkError, NoTarget, Result, flash, info,
                    probe, read32, reset_run, run, sample, save, watch)
from .build import BuildError, BuildResult, build, size, symbol, vectors

__all__ = [
    # окружение
    "utf8_console", "jlink_dir", "jlink_exe", "jlink_version", "stlink_cli",
    "stlink_version", "gcc_bin", "gcc_tool", "gcc_version", "make_exe",
    "work_root", "is_safe_path", "kit_root",
    # J-Link (по умолчанию, плоские имена)
    "GENERIC_CORE", "run", "Result", "JLinkError", "NoTarget", "probe",
    "info", "read32", "watch", "sample", "save", "reset_run", "flash",
    # ST-Link — модуль mk.stlink.*, свой Result и свои ошибки
    "stlink",
    # сборка
    "build", "BuildResult", "BuildError", "size", "symbol", "vectors",
]
