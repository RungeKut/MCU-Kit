# -*- coding: utf-8 -*-
"""ST-Link через STM32CubeProgrammer (STM32_Programmer_CLI.exe).

    import mcukit as mk
    print(mk.stlink.probe())                 # список зондов, к чипу не лезет
    print(mk.stlink.info())                  # connect: ID, флеш, напряжение
    mk.stlink.flash("build/app.bin", addr=0x08000000)
    mk.stlink.watch(0x20000000, times=3)     # растёт ли счётчик в ОЗУ

Второй зонд набора — рядом с J-Link (`mcukit.jlink`), не вместо него:
GD32 официально поддержан только J-Link (в этом наборе так и осталось,
знание — knowledge/40_СРЕДА/40-03), а штатные чипы ST — этим модулем.

В отличие от J-Link, `connect` штатным средством ST не выполняет скрипт
стороннего производителя, который у чужого кремния может по потере связи
решить, что чип защищён, и снять защиту стиранием (эта опасность описана
для J-Link/GD32 в knowledge/30_ГРАБЛИ/30-02). Поэтому здесь `info()` сразу
подключается по SWD без промежуточного «дженерик»-профиля — это
самостоятельная безопасная операция, а не обход угрозы.

Один вызов STM32_Programmer_CLI.exe — одно подключение: в отличие от
J-Link Commander, у него нет пакета команд с паузами внутри сеанса,
поэтому `watch()` и `sample()`-подобная выборка складываются из отдельных
запусков (дороже по времени, интервал не точен).

Код возврата ненадёжен так же, как у J-Link (30-05), но по другой причине:
параметр `sn=` в CLI 2.4.0 всегда выдаёт `Warning: Wrong connect
parameter`, а сам сеанс код 1, даже подключившись успешно к единственному
доступному зонду — knowledge/30_ГРАБЛИ/30-07. Успех проверяется по
наличию `Device ID` в выводе, а не по коду возврата и не по одному
отсутствию строк `Error`.
"""
import os
import re
import shutil
import subprocess
import time

from . import env

_ERR = re.compile(r"^\s*Error\b", re.I)
_CONNECTED = re.compile(r"Device ID\s*:")
_MEM = re.compile(r"^0x([0-9A-Fa-f]{8})\s*:\s*((?:[0-9A-Fa-f]{2,8}\s*)+)$")


class STLinkError(RuntimeError):
    pass


class NoTarget(STLinkError):
    """Зонд есть, ядро не отвечает: питание, земля, проводка, сброс."""


class Result:
    """Итог одного запуска STM32_Programmer_CLI.exe."""

    def __init__(self):
        self.args = []
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
    def errors(self):
        """Строки `Error:` — не `Warning:` (30-07 не в счёт)."""
        return [l.strip() for l in self.lines if _ERR.search(l)]

    @property
    def connected(self):
        """Подключение к ядру подтверждено строкой `Device ID`."""
        return any(_CONNECTED.search(l) for l in self.lines)

    @property
    def ok(self):
        return not self.timed_out and not self.errors

    def mem(self):
        """Прочитанное командами -r8/-r16/-r32: список (адрес, [значения])."""
        out = []
        for l in self.lines:
            m = _MEM.match(l.strip())
            if m:
                out.append((int(m.group(1), 16),
                            [int(x, 16) for x in m.group(2).split()]))
        return out

    def explain(self):
        parts = ["ST-Link: %s" % ("OK" if self.ok else "ОШИБКА")]
        if self.timed_out:
            parts.append("тайм-аут через %.0f с" % self.elapsed)
        parts += ["  " + e for e in self.errors]
        if not self.errors and not self.connected:
            parts.append("  нет строки 'Device ID' в выводе — подключение "
                         "не подтверждено")
        return "\n".join(parts)

    def check(self):
        if not self.ok:
            raise STLinkError(self.explain())
        return self

    def __repr__(self):
        return "<Result %s, %.1f с>" % ("OK" if self.ok else "ОШИБКА",
                                        self.elapsed)


def run(args, timeout=60, kind="stlink"):
    """Выполнить STM32_Programmer_CLI.exe с args (без имени программы и
    без -q/-log — их добавляет run сама). Вернуть Result.

    Журнал CLI (-log) пишется в job_dir и виден после тайм-аута, как у
    J-Link (knowledge/10_API/10-01).
    """
    job = env.new_job_dir(kind)
    log = os.path.join(job, "cubeprog.log")
    full = [env.stlink_cli(), "-q", "-log", log] + list(args)
    r = Result()
    r.args, r.log_path, r.job_dir = full, log, job
    t0 = time.time()
    p = subprocess.Popen(full, stdin=subprocess.DEVNULL,
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
    r.output = (out or b"").decode("utf-8", "replace")
    with open(os.path.join(job, "stdout.txt"), "w", encoding="utf-8") as f:
        f.write(r.output)
    return r


def _connect_args(serial=None, freq=None, mode=None, iface="SWD"):
    """Аргументы -c для connect. serial — см. 30-07: на CLI 2.4.0
    ненадёжен, пригоден только когда зонд ровно один."""
    args = ["-c", "port=%s" % iface]
    if freq:
        args.append("freq=%d" % freq)
    if mode:
        args.append("mode=%s" % mode)
    if serial:
        args.append("sn=%s" % serial)
    return args


def _field(text, pattern, cast=str):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None


def probe(timeout=20):
    """Список подключённых ST-Link зондов — к чипу не обращается.

    {"count", "serial", "firmware", "result"}.
    """
    r = run(["-l", "st-link"], timeout=timeout, kind="probe")
    t = r.output
    serials = re.findall(r"ST-LINK SN\s*:\s*(\S+)", t)
    fws = re.findall(r"ST-LINK FW\s*:\s*(\S+)", t)
    return {
        "count": len(serials),
        "serial": serials[0] if serials else None,
        "firmware": fws[0] if fws else None,
        "result": r,
    }


def info(serial=None, freq=None, mode=None, iface="SWD", timeout=30):
    """Подключиться к ядру по SWD и прочитать его данные. Ничего не пишет.

    Возвращает {"ok", "voltage", "device_id", "device_name", "flash_size",
    "cpu", "result"}; ok — есть строка Device ID.
    """
    r = run(_connect_args(serial, freq, mode, iface), timeout=timeout,
            kind="info")
    t = r.output
    return {
        "ok": r.connected,
        "voltage": _field(t, r"Voltage\s*:\s*([\d.]+)V", float),
        "device_id": _field(t, r"Device ID\s*:\s*(0x[0-9A-Fa-f]+)"),
        "device_name": _field(t, r"Device name\s*:\s*([^\r\n]+)"),
        "flash_size": _field(t, r"Flash size\s*:\s*([^\r\n]+)"),
        "cpu": _field(t, r"Device CPU\s*:\s*([^\r\n]+)"),
        "result": r,
    }


def read32(addr, count=1, serial=None, freq=None, mode=None, iface="SWD"):
    """Прочитать count слов по 32 бита. Ядро не останавливается."""
    args = _connect_args(serial, freq, mode, iface) + \
        ["-r32", "0x%08X" % addr, str(count * 4)]
    r = run(args, kind="read")
    if not r.connected:
        raise NoTarget("ядро не отвечает\n" + r.explain())
    words = []
    for _a, vals in r.mem():
        words += vals
    if len(words) < count:
        raise STLinkError("прочитано %d слов из %d\n%s"
                          % (len(words), count, r.explain()))
    return words[:count]


def watch(addr, times=3, interval_ms=1000, serial=None, freq=None,
          mode=None, iface="SWD"):
    """Прочитать слово times раз — доказательство, что код идёт.

    В отличие от J-Link (один сеанс со sleep внутри, 20-02),
    STM32_Programmer_CLI не умеет пакет команд с паузой: каждое чтение —
    отдельный запуск CLI, интервал приблизителен (не проверено на
    точность).
    """
    vals = []
    for i in range(times):
        vals.append(read32(addr, 1, serial, freq, mode, iface)[0])
        if i + 1 < times:
            time.sleep(interval_ms / 1000)
    return vals


def save(path, addr, size, serial=None, freq=None, mode=None, iface="SWD",
         timeout=600):
    """Сохранить область памяти в файл (upload).

    Ядро не останавливается — upload не требует halt (проверено
    экспериментом 25.09.2026, knowledge/40_СРЕДА/40-03).
    """
    job = env.new_job_dir("save")
    dst = os.path.join(job, "dump.bin")
    args = _connect_args(serial, freq, mode, iface) + \
        ["-u", "0x%08X" % addr, str(size), dst]
    r = run(args, timeout=timeout, kind="save")
    if not r.ok or "Data read successfully" not in r.output \
            or not os.path.exists(dst):
        raise STLinkError("upload не подтверждён\n" + r.explain())
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    shutil.copyfile(dst, path)
    return r


def reset_run(serial=None, freq=None, mode=None, iface="SWD"):
    """Сбросить и запустить.

    НЕ ПРОВЕРЕНО на реальном железе: синтаксис (`-rst`) взят из --help
    STM32CubeProgrammer 2.4.0, действием не обкатан — на подключённой
    во время разработки плате сброс намеренно не запускался, чтобы не
    прерывать её работу без согласия человека. Перед тем как полагаться,
    прогнать на безопасной плате и перенести результат в
    knowledge/40_СРЕДА/40-03 (00_ПРАВИЛА.md, правило 6).
    """
    args = _connect_args(serial, freq, mode, iface) + ["-rst"]
    return run(args, kind="reset").check()


def flash(image, addr=0x08000000, verify=True, start=True, min_voltage=3.0,
          serial=None, freq=None, mode=None, iface="SWD", timeout=300):
    """Записать образ во флеш. Вернуть Result.

    image — .bin (пишется с addr) или .hex/.elf/.srec (адреса внутри).
    Перед записью проверяет ответ ядра и напряжение через info().

    НЕ ПРОВЕРЕНО записью на реальном железе: команда (`-d`/`-v`/`-rst`) и
    строки успеха взяты из --help STM32CubeProgrammer 2.4.0, а не из
    удачной записи — на подключённой во время разработки плате запись
    намеренно не запускалась (риск для чужой рабочей прошивки без
    согласия человека). Перед первым использованием — тестовая запись на
    безопасной плате с сохранением прежнего содержимого (`save()`) и
    перенос результата в knowledge/40_СРЕДА/40-03, статус с `не
    проверено` на `проверено` (00_ПРАВИЛА.md, правило 6).
    """
    i = info(serial, freq, mode, iface)
    if not i["ok"]:
        raise NoTarget("ядро не отвечает\n" + i["result"].explain())
    if i["voltage"] is not None and i["voltage"] < min_voltage:
        raise NoTarget("напряжение %.2f В ниже %.2f В"
                       % (i["voltage"], min_voltage))
    ext = os.path.splitext(image)[1].lower()
    args = _connect_args(serial, freq, mode, iface) + ["-d", image]
    if ext == ".bin":
        args.append("0x%08X" % addr)
    if verify:
        args.append("-v")
    if start:
        args.append("-rst")
    r = run(args, timeout=timeout, kind="flash")
    r.loaded = "Download verified successfully" in r.output or \
        "File download complete" in r.output
    if not r.ok or not r.loaded:
        raise STLinkError("запись не подтверждена\n" + r.explain())
    return r
