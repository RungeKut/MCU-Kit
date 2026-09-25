# -*- coding: utf-8 -*-
"""Сборка проекта make + arm-none-eabi-gcc в безопасной папке.

    r = mk.build(r"D:\\проект\\прошивка")      # копия -> make -> build\\ обратно
    print(r.size)                              # {'text': 292, 'data': 0, 'bss': 8}
    addr = mk.symbol(r.elf, "blink_count")

Проект копируется в рабочую папку без пробелов и кириллицы и собирается
там: make и gcc на таком пути работают предсказуемо, а папки проектов
часто лежат на путях с пробелами и кириллицей (knowledge/10_API/10-02).
Результат — папка build\\ — копируется обратно в проект.

Makefile проекта должен понимать переменную GCC_BIN (префикс пути к
утилитам) и класть результат в build\\ — как в templates/blink_f4.
"""
import os
import re
import shutil
import subprocess
import time

from . import env

_SKIP = ("build", ".git", "__pycache__", ".vs", ".vscode")


class BuildError(RuntimeError):
    pass


class BuildResult:
    def __init__(self):
        self.ok = False
        self.returncode = None
        self.output = ""
        self.elapsed = 0.0
        self.project = ""
        self.job_dir = ""
        self.build_dir = ""
        self.elf = None
        self.bin = None
        self.hex = None
        self.size = {}

    def explain(self):
        tail = "\n".join(self.output.splitlines()[-25:])
        return "сборка %s: %s, код %s\n%s" % (
            self.project, "OK" if self.ok else "ОШИБКА", self.returncode, tail)

    def check(self):
        if not self.ok:
            raise BuildError(self.explain())
        return self

    def __repr__(self):
        return "<BuildResult %s %s>" % ("OK" if self.ok else "ОШИБКА",
                                        self.size or "")


def _copy_project(src, dst):
    def ignore(_d, names):
        return [n for n in names if n in _SKIP]
    shutil.copytree(src, dst, ignore=ignore)


def build(project_dir, target="all", jobs=1, timeout=300, extra=()):
    """Собрать проект. Вернуть BuildResult (исключения нет — r.check())."""
    project_dir = os.path.abspath(project_dir)
    r = BuildResult()
    r.project = project_dir
    job = env.new_job_dir("build")
    work = os.path.join(job, "src")
    _copy_project(project_dir, work)
    r.job_dir = work
    args = [env.make_exe(), "-C", work, "GCC_BIN=" + env.gcc_bin().replace(
        "\\", "/"), "-j%d" % jobs, target] + list(extra)
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    r.elapsed = time.time() - t0
    r.returncode = p.returncode
    r.output = (p.stdout + p.stderr).decode("utf-8", "replace")
    built = os.path.join(work, "build")
    if p.returncode == 0 and os.path.isdir(built):
        dst = os.path.join(project_dir, "build")
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(built, dst)
        r.build_dir = dst
        for fn in sorted(os.listdir(dst)):
            full = os.path.join(dst, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext == ".elf":
                r.elf = full
            elif ext == ".bin":
                r.bin = full
            elif ext == ".hex":
                r.hex = full
        if r.elf:
            r.size = size(r.elf)
        r.ok = r.elf is not None
    return r


def _safe(path):
    """Путь, который откроют утилиты binutils.

    arm-none-eabi-nm и -size (GCC 10.3) не открывают файл по пути с
    кириллицей — код 1, «No such file» (knowledge/30_ГРАБЛИ/30-06). Такой
    файл копируется в рабочую папку.
    """
    if env.is_safe_path(os.path.abspath(path)):
        return path
    dst = os.path.join(env.new_job_dir("elf"), os.path.basename(path))
    if not env.is_safe_path(dst):
        dst = os.path.join(os.path.dirname(dst), "file.elf")
    shutil.copyfile(path, dst)
    return dst


def size(elf):
    """Размеры секций: {'text', 'data', 'bss'} в байтах."""
    out = subprocess.run([env.gcc_tool("size"), _safe(elf)],
                         capture_output=True,
                         timeout=30).stdout.decode("utf-8", "replace")
    lines = out.strip().splitlines()
    if len(lines) < 2:
        return {}
    vals = lines[1].split()
    return {"text": int(vals[0]), "data": int(vals[1]), "bss": int(vals[2])}


def symbol(elf, name):
    """Адрес символа из ELF (по nm) или исключение."""
    out = subprocess.run([env.gcc_tool("nm"), _safe(elf)],
                         capture_output=True,
                         timeout=30).stdout.decode("utf-8", "replace")
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == name:
            return int(parts[0], 16)
    raise BuildError("символ %s не найден в %s" % (name, elf))


def vectors(bin_path, count=2):
    """Первые слова образа: [начальный SP, адрес Reset_Handler, ...]."""
    with open(bin_path, "rb") as f:
        data = f.read(4 * count)
    return [int.from_bytes(data[i:i + 4], "little")
            for i in range(0, len(data) - 3, 4)]
