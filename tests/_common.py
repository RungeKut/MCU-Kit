# -*- coding: utf-8 -*-
"""Общее для проверок: путь к набору, копия шаблона, вывод."""
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import mcukit as mk          # noqa: E402

mk.utf8_console()
TEMPLATE = os.path.join(ROOT, "templates", "blink_f4")
OUT = os.path.join(ROOT, "tests", "vyvod")


def template_copy(name="проект с пробелом"):
    """Копия шаблона в папке с пробелом и кириллицей — как у людей."""
    dst = os.path.join(OUT, name + time.strftime("_%H%M%S"))
    shutil.copytree(TEMPLATE, dst, ignore=shutil.ignore_patterns("build"))
    return dst


def ok(cond, what):
    print(("OK    " if cond else "ОШИБКА") + "  " + what)
    return bool(cond)
