---
id: 40-03
title: STM32CubeProgrammer 2.4.0 найден внутри STM32CubeIDE 1.3.0 без отдельной установки; ST-LINK/V2 читает STM32L07x без проблем
tags: [установка, st-link, stm32cubeprogrammer, stm32cubeide, окружение]
applies_to: Windows 10, STM32CubeIDE 1.3.0, STM32CubeProgrammer 2.4.0, ST-LINK/V2 (FW V2J32S7), STM32L07x
status: проверено
verified: 2026-09-25 — probe/info/read32/watch/save прошли на реальной плате; flash() и reset_run() тоже — тестовая запись 148 байт поверх рабочей прошивки, восстановление из бэкапа, сверка байт в байт
source: практика
---

# ST-Link и STM32CubeProgrammer

## Что нужно

| Что | Где берётся | Как находит mcukit |
|---|---|---|
| STM32CubeProgrammer | st.com отдельно, или входит в STM32CubeIDE | `MCUKIT_STLINK` → `Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin` → `C:\ST\STM32CubeIDE_*\...\cubeprogrammer*\tools\bin` |
| Драйвер ST-LINK USB | ставится вместе со STM32CubeIDE/CubeProgrammer | — |

Отдельный `STM32CubeProgrammer` в `Program Files` может отсутствовать —
экземпляр CLI внутри плагина STM32CubeIDE (`...cubeprogrammer.win32_*
\tools\bin\STM32_Programmer_CLI.exe`) работает без него.

Рядом стоит `STLinkServer` (`Program Files (x86)\STMicroelectronics
\stlink_server`) — для CLI не требуется, нужен для одновременного
подключения нескольких инструментов к одному зонду (`shared`-режим
connect, не проверялось).

Проверка:

```python
import mcukit as mk
mk.stlink_version()             # '2.4.0'
mk.stlink.probe()                # зонд(ы) — к чипу не лезет
```

## Зонд ST-LINK/V2

`-l st-link` показывает `ST-LINK FW: V2J32S7` — родной ST-LINK/V2, не
перешитый и не китайский клон. `connect` читает `Device ID`, `Device
name`, размер флеша и напряжение без ограничений на плате с STM32L07x.
Другой экземпляр или клон может вести себя иначе — проверять по 10-04 и
30-07.

## GD32 — по-прежнему J-Link

Официально GD32 через ST-Link не поддержан; попытки перепрошить ST-Link
в J-Link для GD32 в опыте набора не подтверждались (см. 20-04). Модуль
`mcukit.stlink` не тестировался на GD32 и не предполагается для него.

## Время операций

Замер вручную, SWD по умолчанию (4 МГц):

| Операция | Время |
|---|---|
| `probe()` (`-l st-link`) | ~0,5 с |
| `info()` (`-c port=SWD`) | ~0,5 с |
| `read32()` 8 слов | ~0,5 с |
| `save()` 64 байт | ~0,6 с |

Каждая операция — отдельный запуск процесса (10-04): заметно дороже по
накладным расходам, чем J-Link Commander в пакетном сценарии (40-01), но
для разовых чтений и записи это не критично.

## Запись и сброс — проверены с бэкапом и восстановлением

`mk.stlink.flash()`/`mk.stlink.reset_run()` (`-d`/`-v`/`-rst`) обкатаны
на плате с рабочей (не тестовой) прошивкой, по согласованному с человеком
плану:

1. `save()` всего флеша (128 КБ) в файл — до какой-либо записи.
2. `flash()` тестовым образом без единого обращения к периферии
   (`templates/counter_l0` — только счётчик в ОЗУ, `20-02`), сверка
   (`-v`) и сброс (`-rst`) как часть той же команды: вывод CLI дал
   `File download complete`, `Download verified successfully`, `MCU
   Reset`, `Software reset is performed`.
3. `watch()` подтвердил, что счётчик растёт после записи (с
   `mode=HOTPLUG` — без него сам `watch()` вводит в заблуждение, `30-08`).
4. Тем же `flash()` немедленно записан обратно сохранённый на шаге 1
   дамп; повторный `save()` совпал с ним побайтово.

`min_voltage` в `flash()` и связка `info()`-перед-записью работают как
задумано. Успешные строки CLI, на которые ориентируется `r.loaded`:
`File download complete`, `Download verified successfully`.

## Не проверено

* Другие образы, кроме .bin (`.hex`/`.elf`/`.srec` через `-d`).
* Запись на чип с включённой защитой чтения.
* Несколько зондов одновременно; выбор по `sn=` (`30-07`).
* Путь к образу с кириллицей у `-d`/`-u` (в отличие от J-Link/binutils,
  `30-06`, для STM32CubeProgrammer не проверялось).
