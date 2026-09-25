---
id: 10-05
title: OpenOCD работает с ST-Link на родном драйвере ST и читает чип, не останавливая прошивку; транспорт называется swd, а hla_swd в 0.12 уже не поддерживается
tags: [openocd, st-link, swd, чтение, идентификация, hla_swd]
applies_to: xPack OpenOCD 0.12.0+dev, ST-LINK/V2 (V2J32S7), STM32L07x
status: проверено
verified: 2026-09-26 — опознаны зонд, напряжение, ядро и чип; прочитаны IDCODE, объём флеша и начало флеша без остановки ядра
source: эксперимент
---

# OpenOCD вместо STM32CubeProgrammer

## Зачем

STM32CubeProgrammer берётся только с `st.com`, и бывает, что сайт
недоступен. OpenOCD ставится из winget
(`xpack-dev-tools.openocd-xpack`), открыт и работает с ST-Link **на родном
драйвере ST** — подменять его на WinUSB через Zadig не требуется
([30-10](../30_ГРАБЛИ/30-10_драйвер_stlink_без_сайта_st.md)).

## Что происходит

Транспорт в 0.12 называется **`swd`**. Старое имя `hla_swd` из множества
примеров даёт отказ ещё до обращения к железу:

```
Debug adapter doesn't support 'hla_swd' transport
```

Проверка одного лишь зонда, без цели:

```
openocd -f interface/stlink.cfg -c "transport select swd" -c "adapter speed 480" -c init -c exit
```

```
Info : STLINK V2J32S7 (API v2) VID:PID 0483:3748
Info : Target voltage: 3.269960
Warn : gdb services need one or more targets defined
```

Предупреждение про gdb — не ошибка: цели в этом вызове и не задавалось.
**Строка `Target voltage` — главное**, что тут нужно: она доказывает, что
зонд жив и что на цели есть питание, ещё до разговора с ядром
(ср. VTref у J-Link, [20-01](../20_ПРИЁМЫ/20-01_порядок_первого_подключения.md)).

## Как правильно: чтение, не тревожащее прошивку

`init` в OpenOCD ядро **не останавливает** — оно продолжает работать, а
память при этом читается. Это ровно то, что нужно для осмотра живой платы
(ср. `mode=HOTPLUG` у ST-Link CLI,
[30-08](../30_ГРАБЛИ/30-08_connect_normal_сбрасывает_ядро.md)).

```
openocd -f interface/stlink.cfg -c "transport select swd" -f target/stm32l0.cfg \
        -c "adapter speed 480" \
        -c "gdb port disabled" -c "tcl port disabled" -c "telnet port disabled" \
        -c init \
        -c "mdw 0x40015800 1"    # DBGMCU_IDCODE
        -c "mdh 0x1FF8007C 1"    # объём флеша, КБ
        -c "mdw 0x08000000 4"    # начало флеша: SP и вектор сброса
        -c exit
```

Порты gdb/tcl/telnet отключаются намеренно: иначе OpenOCD поднимает
серверы и печатает лишнее, а в пакетном чтении они не нужны.

Что дало на плате с Cortex-M0+:

```
Info : SWD DPIDR 0x0bc11477
Info : [stm32l0.cpu] Cortex-M0+ r0p1 processor detected
0x40015800: 20086447        DBGMCU_IDCODE: Device ID 0x447
0x1ff8007c: 0080            128 КБ флеша
0x08000000: 20000808 0800018d ...   SP в ОЗУ, Reset во флеше с битом Thumb
```

Прочитанные SP и вектор сброса — тот же способ убедиться, что во флеше
лежит осмысленный образ, что и в [20-02](../20_ПРИЁМЫ/20-02_доказать_что_код_идёт.md).

**Адрес IDCODE у разных семейств разный.** У STM32L0 это `0x40015800`;
`0xE0042000` из примеров для F1/F4 на L0 читается нулём и легко сойдёт за
«чип не отвечает».

## Как неправильно

`transport select hla_swd` — в 0.12 не поддерживается.

Считать `Warn: gdb services need one or more targets defined` ошибкой
подключения.

Читать `0xE0042000` на STM32L0 и делать вывод по нулю.

Передавать `-c "transport select swd"` одним элементом списка аргументов
PowerShell: `Start-Process -ArgumentList` разобьёт строку по пробелам, и
OpenOCD ответит `Unexpected command line argument: select`. Командную
строку собирать целиком одной строкой.

## Чего не проверено

**Запись во флеш через OpenOCD** (`program`, `flash write_image`) — не
проверялась. Всё выше — только чтение. Пока запись не подтверждена,
прошивать по-прежнему нечем: `mcukit.stlink` рассчитан на
`STM32_Programmer_CLI`, и OpenOCD он не использует.
