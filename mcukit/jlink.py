# -*- coding: utf-8 -*-
"""SEGGER J-Link из Python через J-Link Commander (JLink.exe) в пакетном режиме.

    import mcukit as mk
    print(mk.probe())                        # зонд и VTref, к чипу не лезет
    print(mk.info())                         # ядро через Cortex-M4: ничего не стирает
    mk.flash("build/app.bin", device="GD32F470VK", min_vtref=3.1)
    mk.watch(0x20000000, times=3)            # растёт ли счётчик в ОЗУ

Порядок и его причины — knowledge/20_ПРИЁМЫ/20-01:

  1. probe() — зонд на месте, VTref в норме. VTref без общей земли
     показывает правдоподобные 3.2 В (30-01), поэтому одного VTref мало;
  2. info() с профилем Cortex-M4 — ядро отвечает. Профиль ядра не выполняет
     скрипт производителя, а тот при потере связи решает, что чип
     защищён, и снимает защиту со стиранием флеша (30-02);
  3. только потом flash() с профилем чипа — он нужен ради загрузчика флеша.

JLink.exe выводит текст только при выходе: убитый по тайм-ауту процесс не
оставляет ничего в stdout. Поэтому каждый запуск пишет ещё и журнал
J-Link (-log), он виден и после тайм-аута (30-05).
"""
import os
import re
import shutil
import subprocess
import time

from . import env

GENERIC_CORE = "Cortex-M4"

# строки вывода, после которых сеанс считается неудачным
_ERR = re.compile(r"(Error occurred|^\s*ERROR\b|Could not connect|"
                  r"Verify failed|Download failed|failed to program|"
                  r"Cannot connect|Connection to target failed)", re.I)
_MEM = re.compile(r"^([0-9A-Fa-f]{8})\s*=\s*((?:[0-9A-Fa-f]{2,8}\s*)+)$")
_UNSECURE = re.compile(r"unsecured now|will be unsecured|Unsecure", re.I)


class JLinkError(RuntimeError):
    pass


class NoTarget(JLinkError):
    """Зонд есть, ядро не отвечает: питание, земля, проводка, сброс."""


class Result:
    """Итог сеанса J-Link Commander."""

    def __init__(self):
        self.commands = []
        self.device = ""
        self.returncode = None
        self.timed_out = False
        self.elapsed = 0.0
        self.output = ""
        self.log_path = ""
        self.job_dir = ""

    @property
    def lines(self):
        return self.output.splitlines()

    @property
    def executed(self):
        """Команды, до которых J-Link дошёл (эхо «J-Link>команда»)."""
        return [l.split(">", 1)[1].strip() for l in self.lines
                if l.startswith("J-Link>") and l[7:].strip()]

    @property
    def skipped(self):
        """Команды сценария, которых нет в эхе.

        J-Link Commander, спросив что-то с консоли (JTAGConf>, Device>) и
        получив конец ввода, молча заканчивает сценарий с кодом 0 и без
        строки ошибки (knowledge/30_ГРАБЛИ/30-05). Только по эху и видно.
        """
        done = [c.lower() for c in self.executed]
        return [c for c in self.commands
                if c.strip().lower() not in ("qc", "q", "exit")
                and c.strip().lower() not in done]

    @property
    def errors(self):
        out = [l.strip() for l in self.lines if _ERR.search(l)]
        if self.skipped:
            out.append("не выполнены команды: %s" % ", ".join(self.skipped))
        return out

    @property
    def unsecured(self):
        """Скрипт производителя снимал защиту (это стирает флеш)."""
        return any(_UNSECURE.search(l) for l in self.lines + self.log_tail(400))

    @property
    def ok(self):
        return not self.timed_out and not self.errors

    def mem(self):
        """Прочитанное командами mem8/16/32: список (адрес, [значения])."""
        out = []
        for l in self.lines:
            m = _MEM.match(l.strip())
            if m:
                out.append((int(m.group(1), 16),
                            [int(x, 16) for x in m.group(2).split()]))
        return out

    def log_tail(self, n=60):
        if not self.log_path or not os.path.exists(self.log_path):
            return []
        with open(self.log_path, encoding="cp1251", errors="replace") as f:
            return f.read().splitlines()[-n:]

    def explain(self):
        parts = ["J-Link, профиль %s: %s" % (self.device,
                 "OK" if self.ok else "ОШИБКА")]
        if self.timed_out:
            parts.append("тайм-аут через %.0f с; вывода нет — хвост журнала:"
                         % self.elapsed)
            parts += ["  " + l for l in self.log_tail(15)]
        parts += ["  " + e for e in self.errors]
        if self.unsecured:
            parts.append("  ВНИМАНИЕ: скрипт производителя снимал защиту — "
                         "флеш мог быть стёрт (30-02)")
        return "\n".join(parts)

    def check(self):
        if not self.ok:
            raise JLinkError(self.explain())
        return self

    def __repr__(self):
        return "<Result %s %s, %.1f с>" % (self.device,
                                          "OK" if self.ok else "ОШИБКА",
                                          self.elapsed)


def run(commands, device=GENERIC_CORE, iface="SWD", speed=4000, timeout=60,
        serial=None, exit_on_error=True, kind="jlink"):
    """Выполнить команды J-Link Commander. Вернуть Result.

    commands — список строк ("connect", "mem32 0x20000000 4", "r", "g"...).
    В конец дописывается "qc", если там нет выхода. Файлы, которые называют
    команды, должны лежать на безопасном пути — flash() и save() копируют
    сами.
    """
    job = env.new_job_dir(kind)
    cmds = list(commands)
    if not cmds or cmds[-1].strip().lower() not in ("qc", "q", "exit"):
        cmds.append("qc")
    cmd_path = os.path.join(job, "cmd.jlink")
    with open(cmd_path, "w", encoding="ascii", newline="\r\n") as f:
        f.write("\n".join(cmds) + "\n")
    log = os.path.join(job, "jlink.log")
    args = [env.jlink_exe(), "-NoGui", "1",
            "-ExitOnError", "1" if exit_on_error else "0",
            "-device", device, "-if", iface, "-speed", str(speed),
            "-log", log, "-CommandFile", cmd_path]
    if iface.upper() == "JTAG":
        # без этого J-Link спрашивает позицию в цепочке с консоли (30-05)
        args[-2:-2] = ["-jtagconf", "-1,-1"]
    if serial:
        args[1:1] = ["-USB", str(serial)]
    r = Result()
    r.commands, r.device, r.log_path, r.job_dir = cmds, device, log, job
    t0 = time.time()
    # stdin закрыт: J-Link, если чего-то ждёт с консоли, получит EOF, а не
    # повиснет до тайм-аута
    p = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=job)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        r.timed_out = True
    r.elapsed = time.time() - t0
    r.returncode = p.returncode
    r.output = (out or b"").decode("cp1251", "replace")
    with open(os.path.join(job, "stdout.txt"), "w", encoding="utf-8") as f:
        f.write(r.output)
    return r


def _field(text, pattern, cast=str):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None


def probe(serial=None, timeout=30):
    """Зонд и напряжение на VTref — без подключения к чипу.

    {"product", "serial", "firmware", "hardware", "licenses", "vtref",
     "result"}. Нормальный VTref ещё не значит, что есть общая земля (30-01).
    """
    r = run(["ShowEmuList", "usb", "st"], serial=serial, timeout=timeout,
            kind="probe", exit_on_error=False)
    t = r.output
    return {
        "product": _field(t, r"ProductName:\s*([^,\r\n]+)"),
        "serial": _field(t, r"S/N:\s*(\d+)"),
        "firmware": _field(t, r"Firmware:\s*(.+)"),
        "hardware": _field(t, r"Hardware version:\s*(\S+)"),
        "licenses": _field(t, r"License\(s\):\s*(.+)"),
        "vtref": _field(t, r"VTref=([\d.]+)V", float),
        "result": r,
    }


def info(device=GENERIC_CORE, reads=(), serial=None, speed=1000, timeout=40):
    """Подключиться к ядру и прочитать его данные. Ничего не пишет.

    reads — дополнительные команды чтения, например ["mem32 0xE0042000 1"].
    Возвращает {"ok", "dpidr", "cpuid", "core", "mem", "result"}; ok — ядро
    опознано. С профилем GENERIC_CORE скрипт производителя не выполняется.
    """
    r = run(["connect", "mem32 0xE000ED00 1"] + list(reads), device=device,
            serial=serial, speed=speed, timeout=timeout, kind="info")
    t = r.output
    core = _field(t, r"Found (Cortex-M\S+ r\dp\d)")
    return {
        "ok": r.ok and core is not None,
        "dpidr": _field(t, r"DPIDR:\s*(0x[0-9A-Fa-f]+)"),
        "cpuid": _field(t, r"CPUID register:\s*(0x[0-9A-Fa-f]+)"),
        "core": core,
        "mem": r.mem(),
        "result": r,
    }


def read32(addr, count=1, device=GENERIC_CORE, serial=None):
    """Прочитать count слов по 32 бита. Ядро не останавливается."""
    r = run(["connect", "mem32 0x%08X %d" % (addr, count)], device=device,
            serial=serial, kind="read").check()
    words = []
    for _a, vals in r.mem():
        words += vals
    if len(words) < count:
        raise JLinkError("прочитано %d слов из %d\n%s"
                         % (len(words), count, r.explain()))
    return words[:count]


def watch(addr, times=3, interval_ms=1000, device=GENERIC_CORE, serial=None):
    """Прочитать слово times раз с паузой — доказательство, что код идёт.

    Счётчик в ОЗУ, который растёт между чтениями, говорит больше, чем
    «прошивка записалась» (knowledge/20_ПРИЁМЫ/20-02).
    """
    cmds = ["connect"]
    for i in range(times):
        cmds.append("mem32 0x%08X 1" % addr)
        if i + 1 < times:
            cmds.append("sleep %d" % interval_ms)
    r = run(cmds, device=device, serial=serial, kind="watch",
            timeout=30 + times * interval_ms / 1000).check()
    return [vals[0] for _a, vals in r.mem()]


def sample(addr, count=100, interval_ms=50, device=GENERIC_CORE,
           serial=None):
    """Прочитать слово count раз с шагом interval_ms за ОДИН сеанс J-Link.

    Для «живых» сигналов: регистр входов порта (GPIOx_IDR/ISTAT, смещение
    0x10), пока человек жмёт кнопку или крутит энкодер. Отдельный сеанс на
    каждое чтение стоит ~0,1 с на запуск J-Link; здесь 300 отсчётов по
    40 мс заняли ~15 с (knowledge/20_ПРИЁМЫ/20-03). Ядро не
    останавливается. Возвращает список значений.
    """
    cmds = ["connect"]
    for i in range(count):
        cmds.append("mem32 0x%08X 1" % addr)
        if i + 1 < count:
            cmds.append("sleep %d" % interval_ms)
    r = run(cmds, device=device, serial=serial, kind="sample",
            timeout=30 + count * (interval_ms + 20) / 1000).check()
    return [vals[0] for _a, vals in r.mem()]


def save(path, addr, size, device=GENERIC_CORE, serial=None, timeout=600):
    """Сохранить область памяти в файл (savebin).

    На время чтения ядро стоит (h); после выхода J-Link Commander оно бежит
    снова — проверено по счётчику (knowledge/20_ПРИЁМЫ/20-02).
    """
    job_file = "dump.bin"
    r = run(["connect", "h", "savebin %s 0x%08X 0x%X" % (job_file, addr, size)],
            device=device, serial=serial, kind="save", timeout=timeout)
    src = os.path.join(r.job_dir, job_file)
    if not r.ok or not os.path.exists(src) or os.path.getsize(src) != size:
        raise JLinkError("savebin не дал файл нужного размера\n" + r.explain())
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    shutil.copyfile(src, path)
    return r


def reset_run(device=GENERIC_CORE, serial=None):
    """Сбросить и запустить."""
    return run(["connect", "r", "g"], device=device, serial=serial,
               kind="reset").check()


def flash(image, device, addr=0x08000000, min_vtref=3.0, verify=True,
          start=True, serial=None, speed=4000, timeout=300):
    """Записать образ во флеш профилем чипа device. Вернуть Result.

    image — .bin (пишется с addr) или .hex/.elf/.srec (адреса внутри).
    Перед записью: probe() с порогом VTref и info() профилем ядра — без
    ответа ядра профиль чипа не запускается (30-02). После записи .bin
    сверяется verifybin; start=True — сброс и пуск.
    """
    p = probe(serial=serial)
    vt = p["vtref"]
    if vt is None:
        raise JLinkError("зонд не отвечает\n" + p["result"].explain())
    if vt < min_vtref:
        raise NoTarget(
            "VTref %.2f В ниже %.2f В: плата не запитана или питание "
            "просело; при напряжении ниже порога супервизора ядро в сбросе "
            "(knowledge/30_ГРАБЛИ/30-03)" % (vt, min_vtref))
    i = info(serial=serial)
    if not i["ok"]:
        raise NoTarget(
            "ядро не отвечает профилю %s — профиль чипа не запускаю: его "
            "скрипт без связи снимает защиту со стиранием (30-02). Проверить "
            "общую землю (30-01), питание, SWDIO/SWCLK.\n%s"
            % (GENERIC_CORE, i["result"].explain()))

    job = env.new_job_dir("image")
    ext = os.path.splitext(image)[1].lower()
    local = os.path.join(job, "image" + ext)
    shutil.copyfile(image, local)
    cmds = ["connect", "r", "h"]
    if ext == ".bin":
        cmds.append("loadbin %s 0x%08X" % (local, addr))
        if verify:
            cmds.append("verifybin %s 0x%08X" % (local, addr))
    else:
        cmds.append("loadfile %s" % local)
    if start:
        cmds += ["r", "g"]
    r = run(cmds, device=device, serial=serial, speed=speed,
            timeout=timeout, kind="flash")
    r.loaded = "O.K." in r.output
    r.verified = ("Verify successful" in r.output) if (ext == ".bin" and
                                                        verify) else None
    if not r.ok or not r.loaded or r.verified is False:
        raise JLinkError("запись не подтверждена\n" + r.explain())
    return r
