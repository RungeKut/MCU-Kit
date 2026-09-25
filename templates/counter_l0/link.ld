/* Карта памяти STM32L07x/L08x/L010 (Cortex-M0+, Device ID 0x447).
 *   флеш с 0x08000000, 128 КБ — прочитано STM32_Programmer_CLI по SWD
 *   (knowledge/40_СРЕДА/40-03), не из документации;
 *   ОЗУ с 0x20000000 — семейство даёт больше (RM0367), здесь занята
 *   заведомо безопасная нижняя часть: для счётчика и малого стека
 *   больше не нужно, а бо́льшая длина здесь не проверялась.
 */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 4K
}
_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
    .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
    .text : { *(.text*) *(.rodata*) . = ALIGN(4); } > FLASH
    _sidata = LOADADDR(.data);
    .data : { _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > RAM AT > FLASH
    .bss  : { _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > RAM
}
