---
id: 30-10
title: Без драйвера ST-Link зонд стоит с кодом 28 и его не видит никто; драйвер лежит внутри установщика Keil MDK, и ставится он pnputil, а не dpinst
tags: [st-link, драйвер, winusb, pnputil, dpinst, код 28, mdk]
applies_to: Windows 10 x64, ST-LINK/V2 (VID_0483 PID_3748), Keil MDK 5.39
status: проверено
verified: 2026-09-26 — драйвер извлечён из установщика MDK и установлен; зонд перешёл из CM_PROB_FAILED_INSTALL в CM_PROB_NONE, OpenOCD получил связь с чипом
source: эксперимент
---

# Драйвер ST-Link, когда сайт ST недоступен

## Что происходит

Свежеподключённый ST-LINK/V2 на машине без драйвера выглядит так:

```
Status       : Error
Problem      : CM_PROB_FAILED_INSTALL      (код 28)
Class        :                              (пусто)
FriendlyName : STM32 STLink
CompatibleIds: USB\Class_FF&SubClass_FF&Prot_FF
```

Класс устройства вендорский (`FF/FF/FF`), поэтому **встроенного драйвера у
Windows для него нет и не будет**. Пока драйвера нет, зонд недоступен
никому: ни STM32CubeProgrammer, ни OpenOCD, ни uVision.

Штатный источник драйвера — `st.com` (пакет STSW-LINK009). Если сайт
недоступен, положение кажется безвыходным.

## Почему это важно знать

Тот же самый подписанный драйвер **входит в установщик Keil MDK**. Внутри
`MDK<версия>.EXE` (обычный zip) лежит готовый пакет:

```
ARM\STLink\USBDriver\
    stlink_dbg_winusb.inf        <- в нём перечислен VID_0483&PID_3748
    stlinkdbgwinusb_x64.cat      <- каталог, подписанный STMicroelectronics
    stlink_bridge_winusb.inf, stlink_VCP.inf
    amd64\winusbcoinstaller2.dll, amd64\WdfCoInstaller01009.dll
    dpinst_amd64.exe, stlink_winusb_install_quiet.bat
```

Извлекается любым 7-Zip без установки MDK:

```powershell
& 7za.exe x "MDK539.EXE" -o"<куда>" "ARM\STLink\USBDriver\*" -y
```

Драйвер этот — **WinUSB** (служба `WinUSB`, «STMicroelectronics STLink
dongle»), и с ним работают и STM32CubeProgrammer, и OpenOCD.

## Как правильно

Ставить **`pnputil`**, а не приложенным `dpinst`:

```powershell
$d = "<папка>\ARM\STLink\USBDriver"
Start-Process cmd -Verb RunAs -Wait -ArgumentList `
  "/c pnputil /add-driver `"$d\stlink_dbg_winusb.inf`" /install"
```

Успех:

```
Пакет драйвера успешно добавлен.
Опубликованное имя:  oem7.inf
Пакет драйвера установлен на устройстве: USB\VID_0483&PID_3748\...
```

Проверка — устройство должно перейти в `CM_PROB_NONE`:

```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_0483' } |
    Select-Object Status, Problem, FriendlyName
```

Установка требует прав администратора. Перепрошивать драйвер на WinUSB
через Zadig **не нужно** и вредно: после Zadig зонд перестаёт видеть
STM32CubeProgrammer, а родной драйвер ST устраивает и его, и OpenOCD.

## Как неправильно

`dpinst_amd64.exe /q` (и `stlink_winusb_install_quiet.bat`, который его и
зовёт) на Windows 10 x64 **молча не ставит драйвер**: возвращает
`0x80030000`, а в `%SystemRoot%\DPINST.LOG` на каждый inf стоит
`DriverPackagePreinstallW (0xE0000242)`. Устройство остаётся с кодом 28.
Судить по тому, что «установщик отработал», нельзя — проверять состояние
устройства.

Ставить WinUSB через Zadig, не разобравшись: это закрывает дорогу
STM32CubeProgrammer, а вернуть родной драйвер потом — отдельная возня.

## Чем подтверждено

На машине без всякого ST-софта: зонд в `CM_PROB_FAILED_INSTALL` (28).
`dpinst_amd64.exe /q /sa /sw` — код `0x80030000`, состояние не изменилось.
`pnputil /add-driver ... /install` — «Пакет драйвера установлен на
устройстве», после чего `Status=OK`, `Service=WinUSB`, `DriverProvider=
STMicroelectronics`, версия 2.2.0.0. Следом OpenOCD увидел зонд
(`STLINK V2J32S7 (API v2)`), напряжение на цели и опознал ядро.
