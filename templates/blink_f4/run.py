# -*- coding: utf-8 -*-
"""Собрать, прошить, доказать, что код идёт.

Запуск:  python run.py            собрать, прошить, проверить
         python run.py --build    только собрать
"""
import os
import sys
import time


def kit_root():
    """Корень MCU-Kit: MCUKIT_HOME, иначе junction скилла."""
    env = os.environ.get("MCUKIT_HOME")
    if env and os.path.isdir(os.path.join(env, "mcukit")):
        return env
    link = os.path.join(os.path.expanduser("~"), ".claude", "skills", "mcu")
    root = os.path.dirname(os.path.realpath(link))
    if os.path.isdir(os.path.join(root, "mcukit")):
        return root
    raise RuntimeError("MCU-Kit не найден: запустите tools/setup.ps1")


sys.path.insert(0, kit_root())
import mcukit as mk         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import project as P         # noqa: E402


def main(argv):
    mk.utf8_console()
    b = mk.build(HERE).check()
    sp, reset = mk.vectors(b.bin)
    print("сборка:", b.size, "SP=0x%08X Reset=0x%08X" % (sp, reset))
    if "--build" in argv:
        return 0

    p = mk.probe(serial=P.PROBE_SERIAL)
    print("зонд:", p["product"], p["serial"], "VTref=%s В" % p["vtref"])

    if P.BACKUP:
        addr, size = P.BACKUP
        path = os.path.join(HERE, "backup_%s.bin" % time.strftime(
            "%Y%m%d_%H%M%S"))
        mk.save(path, addr, size, serial=P.PROBE_SERIAL)
        print("сохранено:", path)

    r = mk.flash(b.bin, device=P.DEVICE, min_vtref=P.MIN_VTREF,
                 serial=P.PROBE_SERIAL)
    print("прошито:", r, "сверка:", r.verified)

    addr = mk.symbol(b.elf, "blink_count")
    vals = mk.watch(addr, times=3, interval_ms=1000, serial=P.PROBE_SERIAL)
    print("blink_count:", vals)
    if not all(b2 > a for a, b2 in zip(vals, vals[1:])):
        print("СЧЁТЧИК НЕ РАСТЁТ — код не идёт")
        return 1
    print("Код идёт. Глазами: светодиоды должны мигать.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
