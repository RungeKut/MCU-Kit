# -*- coding: utf-8 -*-
"""mcukit — сборка и прошивка микроконтроллеров Cortex-M из Python.

Проверенное поведение, ловушки и приёмы — в knowledge/ (начинать с
knowledge/INDEX.md).

Быстрый старт:

    import mcukit as mk

    mk.utf8_console()
    r = mk.build(r"D:\\проект\\прошивка").check()     # make + gcc над копией
    print(mk.probe())                                # зонд, VTref
    print(mk.info())                                 # ядро: только чтение
    mk.flash(r.bin, device="GD32F470VK", min_vtref=3.1)
    mk.watch(mk.symbol(r.elf, "blink_count"))        # код идёт?

Порядок подключения — knowledge/20_ПРИЁМЫ/20-01: сначала зонд и VTref,
потом ядро профилем Cortex-M4, и только потом профиль чипа.
"""

__version__ = "0.1.0"

from .env import (gcc_bin, gcc_tool, gcc_version, is_safe_path, jlink_dir,
                  jlink_exe, jlink_version, kit_root, make_exe, utf8_console,
                  work_root)
from .jlink import (GENERIC_CORE, JLinkError, NoTarget, Result, flash, info,
                    probe, read32, reset_run, run, save, watch)
from .build import BuildError, BuildResult, build, size, symbol, vectors

__all__ = [
    # окружение
    "utf8_console", "jlink_dir", "jlink_exe", "jlink_version", "gcc_bin",
    "gcc_tool", "gcc_version", "make_exe", "work_root", "is_safe_path",
    "kit_root",
    # J-Link
    "GENERIC_CORE", "run", "Result", "JLinkError", "NoTarget", "probe",
    "info", "read32", "watch", "save", "reset_run", "flash",
    # сборка
    "build", "BuildResult", "BuildError", "size", "symbol", "vectors",
]
