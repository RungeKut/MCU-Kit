---
id: 30-04
title: GCC с -Os превращает цикл копирования .data и обнуления .bss в memcpy/memset — при -nostdlib «undefined reference to memcpy»
tags: [gcc, startup, -nostdlib, memcpy, memset, оптимизация]
applies_to: arm-none-eabi-gcc 10.3.1 (GNU Tools for STM32)
status: проверено
verified: 2026-09-25 — ошибка компоновки воспроизведена на startup.c шаблона; с флагами ниже собирается
source: эксперимент
---

# -Os вставляет memcpy и memset в Reset_Handler

## Что происходит

```
ld.exe: ... in function `Reset_Handler':
startup.c:41: undefined reference to `memcpy'
startup.c:43: undefined reference to `memset'
```

хотя в `startup.c` нет ни одного вызова — только циклы:

```c
for (uint32_t *dst = &_sdata; dst < &_edata; ) *dst++ = *src++;
for (uint32_t *dst = &_sbss;  dst < &_ebss;  ) *dst++ = 0;
```

## Почему

Оптимизация распознаёт в цикле копирование и заполнение и заменяет его
вызовом библиотечной функции. С `-nostdlib` библиотеки нет.

## Как правильно

Флаги компиляции:

```
-ffreestanding -fno-tree-loop-distribute-patterns
```

(в `templates/blink_f4/Makefile` они уже есть).

## Как неправильно

Убирать `-Os` или дописывать свои `memcpy`/`memset` в startup: первое
раздувает код, второе прячет замену, и её следы вылезут в другом месте.

## Чем подтверждено

Без флагов — ошибка выше; с флагами — `text 292, bss 8`, прошивка
работает.
