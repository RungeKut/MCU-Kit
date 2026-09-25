/* Карта памяти. Размеры — под свой чип:
 *   флеш с 0x08000000 (у GD32F4 и STM32F4 одинаково);
 *   ОЗУ с 0x20000000 — здесь 112 КБ: столько есть в первом банке SRAM у
 *   старших GD32F4 и STM32F4; для blink больше не нужно.
 */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 112K
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
