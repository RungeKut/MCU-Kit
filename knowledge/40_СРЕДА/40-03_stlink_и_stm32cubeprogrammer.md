---
id: 40-03
title: STM32CubeProgrammer 2.4.0 найден внутри STM32CubeIDE 1.3.0 без отдельной установки; ST-LINK/V2 читает STM32L07x без проблем
tags: [установка, st-link, stm32cubeprogrammer, stm32cubeide, окружение]
applies_to: Windows 10, STM32CubeIDE 1.3.0, STM32CubeProgrammer 2.4.0, ST-LINK/V2 (FW V2J32S7), STM32L07x
status: проверено
verified: 2026-09-25 — mk.stlink нашёл CLI сам внутри STM32CubeIDE; probe/info/read32/save прошли на реальной плате
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

## Чем НЕ подтверждено

`-d`/`-v`/`-rst` (запись, сверка, сброс) не запускались на реальном
железе — на подключённой во время разработки плате запись и сброс
намеренно не выполнялись без согласия человека. `mk.stlink.flash()` и
`mk.stlink.reset_run()` реализованы по `--help` CLI и не имеют статуса
`проверено`. Перед тем как полагаться на них — тестовая запись на плате,
чьё содержимое не жалко, с предварительным `save()`, и обновление этой
записи.
