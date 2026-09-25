---
id: 30-05
title: J-Link Commander, спросив что-то с консоли (JTAGConf>), при закрытом stdin молча обрывает сценарий с кодом 0 — успех проверять по эху команд
tags: [j-link, jtag, jtagconf, stdin, код возврата, пакетный режим]
applies_to: J-Link V9.38a
status: проверено
verified: 2026-09-25 — -if JTAG без -jtagconf: вывод кончается «JTAGConf>», код 0, connect и mem32 не выполнены; с -jtagconf -1,-1 — нормальная ошибка подключения, код 1
source: эксперимент
---

# Молчаливый обрыв сценария

## Что происходит

`JLink.exe -NoGui 1 -ExitOnError 1 -device Cortex-M4 -if JTAG ...
-CommandFile cmd.jlink`, stdin закрыт. Вывод:

```
J-Link>connect
...
VTref=3.335V
Device position in JTAG chain (IRPre,DRPre) <Default>: -1,-1 => Auto-detect
JTAGConf>
Script processing completed.
```

Код возврата 0, строки `Error` нет, а ни `connect`, ни следующая команда
не выполнены. Сеанс выглядит успешным.

## Почему

Для JTAG Commander спрашивает позицию устройства в цепочке. Ввода нет —
он бросает сценарий, не считая это ошибкой. Так же поведёт себя любой
другой вопрос с консоли.

## Как правильно

* Для JTAG передавать `-jtagconf -1,-1` (mcukit делает сам).
* Успех — по эху: каждая команда сценария должна встретиться как
  `J-Link>команда`. `Result.skipped` — список невыполненных, `Result.ok`
  без них ложен.

## Как неправильно

Судить по коду возврата или по отсутствию строк `Error`.

## Чем подтверждено

Тот же сценарий: без `-jtagconf` — код 0 и обрыв на `JTAGConf>`; с ним —
`Could not connect`, код 1 (переходник не разводит TDI, JTAG и не должен
был подключиться).
