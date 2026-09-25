# -*- coding: utf-8 -*-
"""Проверка с платой: зонд, ядро, запись шаблона, сверка, счётчик.

ПИШЕТ ВО ФЛЕШ. Запускать только на плате, которую можно перешить, и
только с согласия её хозяина. Шаблон мигает выводом из
templates/blink_f4/src/config.h (по умолчанию PA5).

    set MCUKIT_TEST_DEVICE=GD32F470VK
    set MCUKIT_TEST_VTREF=3.1          (необязательно, по умолчанию 3.0)
    python tests/test_hw.py
"""
import os
import sys
import time

from _common import mk, ok, template_copy


def timed(what, f):
    t0 = time.time()
    v = f()
    print("      %-10s %.2f с" % (what, time.time() - t0))
    return v


def main():
    device = os.environ.get("MCUKIT_TEST_DEVICE")
    if not device:
        print("задайте MCUKIT_TEST_DEVICE — имя чипа для J-Link")
        return 2
    vmin = float(os.environ.get("MCUKIT_TEST_VTREF", "3.0"))
    print("J-Link", mk.jlink_version(), "| чип", device)

    p = timed("probe", mk.probe)
    good = ok(p["vtref"] and p["vtref"] >= vmin,
              "зонд %s %s, VTref %s В" % (p["product"], p["serial"],
                                          p["vtref"]))
    i = timed("info", lambda: mk.info(reads=["mem32 0x08000000 2"]))
    good &= ok(i["ok"], "ядро: %s, DPIDR %s" % (i["core"], i["dpidr"]))
    if not good:
        print(i["result"].explain())
        return 1

    r = timed("build", lambda: mk.build(template_copy("hw"))).check()
    f = timed("flash", lambda: mk.flash(r.bin, device=device,
                                         min_vtref=vmin))
    good &= ok(f.loaded and f.verified, "запись и сверка")
    good &= ok(not f.unsecured, "скрипт производителя защиту не снимал")

    out = os.path.join(os.path.dirname(r.bin), "readback.bin")
    n = os.path.getsize(r.bin)
    timed("save", lambda: mk.save(out, 0x08000000, (n + 3) & ~3))
    good &= ok(open(out, "rb").read()[:n] == open(r.bin, "rb").read(),
               "прочитанное совпало с образом")

    addr = mk.symbol(r.elf, "blink_count")
    mk.reset_run()
    vals = timed("watch", lambda: mk.watch(addr, times=3))
    good &= ok(all(b > a for a, b in zip(vals, vals[1:])),
               "счётчик растёт: %s" % vals)
    print("\nИТОГ:", "OK" if good else "ЕСТЬ ОШИБКИ")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
