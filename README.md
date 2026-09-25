# MCU-Kit

Инструмент для сборки и прошивки микроконтроллеров Cortex-M скриптами:
библиотека на Python поверх SEGGER J-Link Commander (или ST-Link через
STM32CubeProgrammer) и arm-none-eabi-gcc, база проверенного знания и
правила её ведения. Подключается к Claude Code как скилл `/mcu`.

Соседние наборы с теми же правилами ведения:
[Allegro-Kit](https://github.com/RungeKut/Allegro-Kit) (платы и схемы
Cadence) и [SolidWorks-Kit](https://github.com/RungeKut/SolidWorks-Kit).

```
MCU-Kit/
├── skill/SKILL.md          точка входа для ИИ (подключён как скилл)
├── mcukit/                 библиотека Python
│   ├── env.py              поиск J-Link, ST-Link, GCC, make; рабочие папки
│   ├── jlink.py            probe, info, read32, watch, save, flash (GD32)
│   ├── stlink.py           то же через ST-Link/STM32CubeProgrammer (STM32)
│   └── build.py            сборка копией, size, symbol, vectors
├── knowledge/              база знаний
│   ├── 00_ПРАВИЛА.md       правила ведения базы
│   ├── INDEX.md            карта базы и поиск по симптому
│   ├── 10_API/  20_ПРИЁМЫ/  30_ГРАБЛИ/  40_СРЕДА/
├── templates/blink_f4/     blink без библиотек для GD32F4 / STM32F4
├── tests/                  проверки: сборка — без железа, остальное — с платой
├── tools/setup.ps1         установка на машине
├── tools/check_docs.py     проверка целостности базы и стоп-слов
└── CHANGELOG.md
```

---

## Что умеет

Два независимых зонда: **J-Link** (`mk.*`, для GD32) и **ST-Link**
(`mk.stlink.*`, для штатных чипов ST) — см. `knowledge/20_ПРИЁМЫ/20-04`,
какой для какого чипа.

| Задача | J-Link | ST-Link | Пишет в чип? |
|---|---|---|---|
| Найти зонд | `mk.probe()` (+ VTref) | `mk.stlink.probe()` | нет, к чипу не подключается |
| Подключиться к ядру, прочитать ID, защиту, флеш | `mk.info(reads=[...])` | `mk.stlink.info()` | нет |
| Прочитать слова памяти, следить за переменной | `mk.read32`, `mk.watch` | `mk.stlink.read32`, `mk.stlink.watch` | нет |
| Сохранить флеш в файл | `mk.save(path, addr, size)` | `mk.stlink.save(...)` | нет |
| Собрать проект make + gcc | `mk.build(папка)` | `mk.build(папка)` | — |
| Записать .bin/.hex/.elf и сверить | `mk.flash(image, device=...)` | `mk.stlink.flash(image, addr=...)` **не проверено записью** | **да** |
| Сбросить и пустить | `mk.reset_run()` | `mk.stlink.reset_run()` **не проверено** | нет |
| Любой сценарий/вызов пакетом | `mk.run([...])` | `mk.stlink.run([...])` | как напишете |

`flash()` перед записью сам проверяет VTref/напряжение (порог задаётся) и
ответ ядра. У J-Link — обязательно профилем `Cortex-M4` сначала: без
ответа профиль чипа не запускается, скрипт производителя без связи
начинает снимать защиту, а это стирание флеша (`30-02`). У ST-Link этого
риска нет (`mcukit.stlink` docstring), но `flash()`/`reset_run()` там пока
не обкатаны реальной записью — см. таблицу и `knowledge/40_СРЕДА/40-03`.

## Установка на новой машине

```powershell
git clone https://github.com/RungeKut/MCU-Kit.git
cd MCU-Kit
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

Либо двойной щелчок по `Install-skill.bat`. После установки —
**перезапустить Claude Code**.

Нужны: SEGGER J-Link Software и/или STM32CubeProgrammer (можно только
что-то одно — набор находит то, что есть), arm-none-eabi-gcc и make
(подойдут и те, что внутри STM32CubeIDE, — набор найдёт их сам, вместе с
STM32CubeProgrammer, если он тоже её часть), Python 3.11+.

## Быстрый старт

```python
import os, sys
sys.path.insert(0, os.environ["MCUKIT_HOME"])   # ставит tools/setup.ps1
import mcukit as mk

mk.utf8_console()

# GD32 — через J-Link
print(mk.probe())                                # зонд, VTref
print(mk.info())                                 # ядро: только чтение
r = mk.build(r"D:\проект\прошивка").check()
mk.flash(r.bin, device="GD32F470VK", min_vtref=3.1)
print(mk.watch(mk.symbol(r.elf, "blink_count"))) # растёт — код идёт

# STM32 — через ST-Link
print(mk.stlink.probe())                         # зонд(ы)
print(mk.stlink.info())                          # ID, флеш, напряжение
```

Новый проект: скопировать `templates/blink_f4`, поправить
`src/config.h`, `link.ld`, `project.py`, запустить `python run.py`.

## Как обратиться к набору

```
/mcu подключись к плате через ST-Link, проверь связь и прошей blink
```

Без команды набор подключается сам, когда в запросе есть J-Link, ST-Link,
STM32CubeProgrammer, SWD, прошивка, GD32, STM32, Cortex-M,
arm-none-eabi-gcc — или ошибки вида «Could not connect to the target
device», «Device will be unsecured now».

---

## Как это устроено

* **J-Link** — `JLink.exe -NoGui 1 -ExitOnError 1 -CommandFile ...` с
  закрытым stdin и журналом `-log`. Успех определяется по эху команд и
  строкам ошибок: код возврата бывает 0, когда сценарий молча оборван.
* **ST-Link** — `STM32_Programmer_CLI.exe -c port=SWD ... -r32/-u/-d ...`,
  один запуск процесса на одну команду (нет пакета команд, как у J-Link).
  Успех — по строке `Device ID` в выводе: код возврата ненадёжен и здесь,
  но по другой причине (`30-07`).
* **Порядок подключения (J-Link)**: зонд и VTref → ядро профилем
  `Cortex-M4` → состояние чипа → запись профилем чипа → доказательство,
  что код идёт, по счётчику в ОЗУ. У ST-Link на штатных чипах ST
  промежуточного профиля не требуется (`20-04`).
* **Сборка** — копией проекта в папке без пробелов и кириллицы; binutils
  (`nm`, `size`) на путях с кириллицей не открывают файлы.

## Что проверено, а что нет

J-Link — проверено 25.09.2026 на J-Link Software V9.38a (зонд J-Link V9),
arm-none-eabi-gcc 10.3.1 из STM32CubeIDE 1.12.1, GD32F470 по SWD, Windows
10, Python 3.13: всё из таблицы «Что умеет».

ST-Link — проверено 25.09.2026 на STM32CubeProgrammer 2.4.0 (внутри
STM32CubeIDE 1.3.0), зонд ST-LINK/V2, STM32L07x по SWD, Windows 10,
Python 3.12: `probe`, `info`, `read32`, `watch`, `save`. **`flash` и
`reset_run` — не проверены записью на железе**, только по `--help` CLI
(`knowledge/40_СРЕДА/40-03`).

**Не проверено (J-Link):** JTAG на переходнике с полным набором линий;
`loadfile` для .hex и .elf (проверен `loadbin`); чип с включённой
защитой; несколько зондов одновременно; другие версии J-Link и GCC.

**Не проверено (ST-Link):** запись и сброс (см. выше); выбор зонда по
`sn=` среди нескольких (`30-07`); GD32 через ST-Link — не предполагается
(`20-04`); другие версии STM32CubeProgrammer.

Записи базы помечены статусом; записи без `verified` силы не имеют.

## Проверки

```
python tests\test_build.py       сборка шаблона — без железа
python tests\test_hw.py          зонд, ядро, запись, сверка, счётчик — нужна плата
python tools\check_docs.py       целостность базы знаний
```

## Работа с нескольких машин

В начале — `git pull --rebase`; после каждой правки набора — `git diff`,
`python tools/check_docs.py --project "<папка проекта>"`, коммит, `git
push`. **В набор не попадает ничего о проектируемом изделии** — ни в
файлы, ни в текст коммита. Приметы изделия — в `tools/stoplist.txt`: он
локальный (`.gitignore`), его заводит `setup.ps1`. Автор коммитов
задаётся для клона публичным именем. Подробности —
`knowledge/40_СРЕДА/40-02`.

---

## Лицензия

MIT — см. [LICENSE](LICENSE).

SEGGER и J-Link — торговые марки SEGGER Microcontroller GmbH; GigaDevice
и GD32 — GigaDevice Semiconductor Inc.; STM32 — STMicroelectronics; Arm и
Cortex — Arm Limited. Проект с ними не связан: это независимый инструмент,
который управляет легально установленными программами через их штатные
интерфейсы командной строки.
