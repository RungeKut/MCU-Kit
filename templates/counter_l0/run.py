# -*- coding: utf-8 -*-
"""Собрать, сохранить флеш, прошить, доказать, что код идёт — ST-Link.

Запуск:  python run.py            собрать, сохранить, прошить, проверить
         python run.py --build    только собрать

Backup обязателен и не отключается флагом: этот шаблон предназначен для
первой проверки записи на плате, содержимое которой может быть боевым.
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

    i = mk.stlink.info(serial=P.PROBE_SERIAL)
    if not i["ok"]:
        print("ядро не отвечает:", i["result"].explain())
        return 1
    print("зонд/ядро:", i["device_name"], i["device_id"],
         "%.2f В" % i["voltage"])

    if not P.BACKUP:
        print("BACKUP не задан — на боевой плате так не делать")
        return 1
    addr, size = P.BACKUP
    path = os.path.join(HERE, "backup_%s.bin" % time.strftime(
        "%Y%m%d_%H%M%S"))
    mk.stlink.save(path, addr, size, serial=P.PROBE_SERIAL)
    print("сохранено:", path, os.path.getsize(path), "байт")

    r = mk.stlink.flash(b.bin, addr=P.FLASH_ADDR, min_voltage=P.MIN_VOLTAGE,
                        serial=P.PROBE_SERIAL)
    print("прошито:", r)

    addr = mk.symbol(b.elf, "loop_count")
    vals = mk.stlink.watch(addr, times=3, interval_ms=500,
                           serial=P.PROBE_SERIAL)
    print("loop_count:", vals)
    if not all(v2 > v1 for v1, v2 in zip(vals, vals[1:])):
        print("СЧЁТЧИК НЕ РАСТЁТ — код не идёт")
        return 1
    print("Код идёт. Восстановить прежнее содержимое:")
    print("  mk.stlink.flash(%r, addr=0x%08X)" % (path, P.FLASH_ADDR))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
