# -*- coding: utf-8 -*-
"""Сборка шаблона без железа: make и gcc находятся, проект на пути с
пробелом и кириллицей собирается, векторы и символ на месте.

    python tests/test_build.py
"""
import sys
import time

from _common import mk, ok, template_copy


def main():
    print("GCC", mk.gcc_version(), "|", mk.gcc_bin())
    print("make", mk.make_exe())
    proj = template_copy()
    t0 = time.time()
    r = mk.build(proj)
    print(r, "%.1f с" % (time.time() - t0))
    good = ok(r.ok, "сборка")
    if not good:
        print(r.explain())
        return 1
    sp, reset = mk.vectors(r.bin)
    good &= ok(0x20000000 <= sp <= 0x20100000, "SP в ОЗУ: 0x%08X" % sp)
    good &= ok(0x08000000 <= reset < 0x08100000 and reset & 1,
               "Reset во флеше и Thumb: 0x%08X" % reset)
    good &= ok(r.size.get("text", 0) > 0, "size по пути с кириллицей: %s"
               % r.size)
    addr = mk.symbol(r.elf, "blink_count")
    good &= ok(0x20000000 <= addr < 0x20100000,
               "символ blink_count в ОЗУ: 0x%08X" % addr)
    good &= ok(r.hex is not None, "есть .hex")
    print("\nИТОГ:", "OK" if good else "ЕСТЬ ОШИБКИ")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
