# -*- coding: utf-8 -*-
"""Окружение: где стоят J-Link, ST-Link/STM32CubeProgrammer, компилятор и
make, где работать.

Все пути ищутся, а не зашиваются: набор ходит по машинам с разными
установками. Порядок поиска:

    J-Link   MCUKIT_JLINK  -> C:\\Program Files\\SEGGER\\JLink* (свежая версия)
    ST-Link  MCUKIT_STLINK -> STM32CubeProgrammer отдельно -> внутри
                            STM32CubeIDE (плагин cubeprogrammer)
    GCC      MCUKIT_GCC   -> arm-none-eabi-gcc в PATH -> Arm GNU Toolchain
                          -> GCC из STM32CubeIDE
    make     MCUKIT_MAKE  -> make в PATH -> make из STM32CubeIDE

Рабочая папка заданий лежит на пути БЕЗ пробелов и кириллицы: проект
копируется туда и собирается там, результат копируется обратно
(knowledge/10_API/10-02).
"""
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import time


def utf8_console():
    """Перевести stdout/stderr в UTF-8, иначе print с кириллицей падает."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name)
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            setattr(sys, name, io.TextIOWrapper(s.buffer, encoding="utf-8",
                                                errors="replace"))


def _ver_key(path):
    """Ключ сортировки по числам в пути: V938a > V812."""
    return [int(x) for x in re.findall(r"\d+", path)] + [path]


def _pf():
    out = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        v = os.environ.get(var)
        if v and v not in out:
            out.append(v)
    return out or [r"C:\Program Files", r"C:\Program Files (x86)"]


# ---------------------------------------------------------------------------
# J-Link
# ---------------------------------------------------------------------------

def jlink_dir():
    """Папка установки SEGGER J-Link (в ней JLink.exe)."""
    v = os.environ.get("MCUKIT_JLINK")
    if v and os.path.exists(os.path.join(v, "JLink.exe")):
        return os.path.normpath(v)
    found = []
    for pf in _pf():
        found += glob.glob(os.path.join(pf, "SEGGER", "JLink*", "JLink.exe"))
    if found:
        return os.path.dirname(sorted(found, key=_ver_key)[-1])
    raise RuntimeError("SEGGER J-Link не найден. Установите J-Link Software "
                       "или задайте MCUKIT_JLINK — папку с JLink.exe.")


def jlink_exe():
    """Полный путь к JLink.exe (J-Link Commander)."""
    return os.path.join(jlink_dir(), "JLink.exe")


def jlink_version():
    """Версия ПО J-Link по имени папки, например 'V938a'."""
    m = re.search(r"JLink_?(V[\w.]+)", jlink_dir(), re.I)
    return m.group(1) if m else os.path.basename(jlink_dir())


# ---------------------------------------------------------------------------
# ST-Link / STM32CubeProgrammer
# ---------------------------------------------------------------------------

def stlink_cli():
    """Полный путь к STM32_Programmer_CLI.exe (STM32CubeProgrammer)."""
    v = os.environ.get("MCUKIT_STLINK")
    if v and os.path.exists(v):
        return v
    cands = []
    for pf in _pf():
        cands += glob.glob(os.path.join(
            pf, "STMicroelectronics", "STM32Cube", "STM32CubeProgrammer",
            "bin", "STM32_Programmer_CLI.exe"))
    cands += sorted(glob.glob(
        r"C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins"
        r"\*cubeprogrammer*\tools\bin\STM32_Programmer_CLI.exe"),
        key=_ver_key, reverse=True)
    for c in cands:
        if os.path.exists(c):
            return c
    raise RuntimeError("STM32CubeProgrammer не найден. Установите его "
                       "отдельно или через STM32CubeIDE, либо задайте "
                       "MCUKIT_STLINK — путь к STM32_Programmer_CLI.exe.")


def stlink_version():
    """Версия STM32CubeProgrammer, например '2.4.0'."""
    out = subprocess.run([stlink_cli(), "-version"], capture_output=True,
                         timeout=30).stdout.decode("utf-8", "replace")
    m = re.search(r"version:\s*([\d.]+)", out, re.I)
    return m.group(1) if m else out.strip()


# ---------------------------------------------------------------------------
# компилятор и make
# ---------------------------------------------------------------------------

def _which(name):
    p = shutil.which(name)
    return os.path.dirname(p) if p else None


def gcc_bin():
    """Папка с arm-none-eabi-gcc.exe (с завершающим разделителем)."""
    cands = []
    v = os.environ.get("MCUKIT_GCC")
    if v:
        cands.append(v)
    w = _which("arm-none-eabi-gcc")
    if w:
        cands.append(w)
    for pf in _pf():
        cands += sorted(glob.glob(os.path.join(
            pf, "Arm GNU Toolchain arm-none-eabi", "*", "bin")),
            key=_ver_key, reverse=True)
        cands += sorted(glob.glob(os.path.join(
            pf, "GNU Arm Embedded Toolchain", "*", "bin")),
            key=_ver_key, reverse=True)
    cands += sorted(glob.glob(
        r"C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins"
        r"\*gnu-tools-for-stm32*\tools\bin"), key=_ver_key, reverse=True)
    for c in cands:
        if os.path.exists(os.path.join(c, "arm-none-eabi-gcc.exe")):
            return os.path.normpath(c) + os.sep
    raise RuntimeError("arm-none-eabi-gcc не найден. Поставьте Arm GNU "
                       "Toolchain или задайте MCUKIT_GCC — папку bin.")


def gcc_tool(name):
    """Полный путь к утилите тулчейна: 'gcc', 'objcopy', 'nm', 'size'..."""
    return gcc_bin() + "arm-none-eabi-" + name + ".exe"


def gcc_version():
    """Версия GCC строкой, например '10.3.1'."""
    out = subprocess.run([gcc_tool("gcc"), "--version"], capture_output=True,
                         timeout=30).stdout.decode("utf-8", "replace")
    m = re.search(r"\)\s+(\d+\.\d+\.\d+)", out)
    return m.group(1) if m else out.splitlines()[0] if out else "?"


def make_exe():
    """Полный путь к make.exe."""
    v = os.environ.get("MCUKIT_MAKE")
    if v and os.path.exists(v):
        return v
    w = shutil.which("make")
    if w:
        return w
    found = sorted(glob.glob(
        r"C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins"
        r"\*externaltools.make*\tools\bin\make.exe"), key=_ver_key)
    if found:
        return found[-1]
    raise RuntimeError("make не найден. Задайте MCUKIT_MAKE — путь к make.exe.")


# ---------------------------------------------------------------------------
# рабочая папка
# ---------------------------------------------------------------------------

def is_safe_path(path):
    """Путь только из ASCII и без пробелов: на нём make и gcc не спотыкаются."""
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        return False
    return " " not in path


def work_root():
    """Корень рабочих папок заданий.

    MCUKIT_WORK, иначе %LOCALAPPDATA%\\Temp\\mcukit, если путь безопасен,
    иначе %SystemDrive%\\mcukit_work.
    """
    cands = []
    if os.environ.get("MCUKIT_WORK"):
        cands.append(os.environ["MCUKIT_WORK"])
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cands.append(os.path.join(la, "Temp", "mcukit"))
    cands.append(os.path.join(os.environ.get("SystemDrive", "C:") + "\\",
                              "mcukit_work"))
    for c in cands:
        c = os.path.normpath(c)
        if is_safe_path(c):
            os.makedirs(c, exist_ok=True)
            return c
    raise RuntimeError("не нашлось рабочей папки без пробелов и кириллицы; "
                       "задайте MCUKIT_WORK")


_JOB = re.compile(r"^[a-z]+-\d{8}-\d{6}-\d{3}$")


def new_job_dir(kind="job", keep=40):
    """Свежая папка задания. Старые папки заданий сверх keep удаляются —
    по времени изменения, только созданные этой функцией, и никогда
    только что созданная."""
    root = work_root()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for i in range(1000):
        d = os.path.join(root, "%s-%s-%03d" % (kind, stamp, i))
        if not os.path.exists(d):
            os.makedirs(d)
            break
    jobs = [os.path.join(root, x) for x in os.listdir(root) if _JOB.match(x)]
    jobs = [j for j in jobs if os.path.isdir(j) and
            os.path.normcase(j) != os.path.normcase(d)]
    jobs.sort(key=os.path.getmtime)
    for j in jobs[:max(0, len(jobs) - keep)]:
        shutil.rmtree(j, ignore_errors=True)
    return d


def kit_root():
    """Корень набора (папка, где лежат mcukit/, knowledge/, skill/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
