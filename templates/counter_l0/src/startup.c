/* Минимальный запуск Cortex-M0+ без библиотек производителя: таблица
 * векторов, копирование .data, обнуление .bss, вызов main.
 *
 * Таблица короче, чем у Cortex-M4 (templates/blink_f4/src/startup.c):
 * у M0+ нет MemManage/BusFault/UsageFault/DebugMon — это возможности
 * M3/M4/M7. Позиции 4-10 и 12 у M0+ зарезервированы (0).
 */
#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
int main(void);

void Reset_Handler(void);
void Default_Handler(void) { for (;;) { } }
void NMI_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void) __attribute__((weak, alias("Default_Handler")));

__attribute__((section(".isr_vector"), used))
void (* const vectors[16])(void) = {
    (void (*)(void))&_estack,
    Reset_Handler,
    NMI_Handler,
    HardFault_Handler,
    0, 0, 0, 0, 0, 0, 0,             /* зарезервировано у M0+ */
    SVC_Handler,
    0,                                /* зарезервировано у M0+ */
    0,                                /* зарезервировано у M0+ */
    PendSV_Handler,
    SysTick_Handler,
};

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata; )
        *dst++ = *src++;
    for (uint32_t *dst = &_sbss; dst < &_ebss; )
        *dst++ = 0;
    main();
    for (;;) { }
}
