/* Blink без библиотек производителя: один или два светодиода по очереди.
 * Настройки — config.h. Тактирование — внутренний RC после сброса.
 *
 * blink_count лежит в ОЗУ и растёт на 1 за цикл: по нему отладчик
 * доказывает, что код идёт, не глядя на светодиод (mcukit.watch).
 */
#include <stdint.h>
#include "config.h"

#define REG(a)          (*(volatile uint32_t *)(a))
#define AHB1EN          REG(0x40023830u)
#define GPIO(port)      (0x40020000u + 0x400u * (port))
#define GPIO_MODE(p)    REG(GPIO(p) + 0x00u)   /* по 2 бита на вывод */
#define GPIO_SPEED(p)   REG(GPIO(p) + 0x08u)
#define GPIO_BSR(p)     REG(GPIO(p) + 0x18u)   /* младшие 16 — в 1, старшие — в 0 */
#define SYST_CSR        REG(0xE000E010u)
#define SYST_RVR        REG(0xE000E014u)
#define SYST_CVR        REG(0xE000E018u)

static volatile uint32_t ticks;
volatile uint32_t blink_count;

void SysTick_Handler(void) { ticks++; }

static void delay_ms(uint32_t ms)
{
    uint32_t start = ticks;
    while ((uint32_t)(ticks - start) < ms) { }
}

static void pin_level(uint32_t port, uint32_t pin, int high)
{
    GPIO_BSR(port) = high ? (1u << pin) : (1u << (pin + 16u));
}

static void led(uint32_t port, uint32_t pin, int on)
{
    pin_level(port, pin, LED_ACTIVE_LOW ? !on : on);
}

static void led_init(uint32_t port, uint32_t pin)
{
    AHB1EN |= 1u << port;
    (void)AHB1EN;                       /* дождаться включения такта */
    led(port, pin, 0);                  /* сначала уровень, потом режим */
    GPIO_MODE(port) = (GPIO_MODE(port) & ~(3u << (pin * 2))) | (1u << (pin * 2));
    GPIO_SPEED(port) &= ~(3u << (pin * 2));
}

int main(void)
{
    led_init(LED1_PORT, LED1_PIN);
    if (LED2_PIN != 0xFFu)
        led_init(LED2_PORT, LED2_PIN);

    SYST_RVR = CORE_HZ / 1000u - 1u;    /* 1 мс */
    SYST_CVR = 0;
    SYST_CSR = 7;                       /* такт ядра, прерывание, пуск */

    for (;;) {
        led(LED1_PORT, LED1_PIN, 1); delay_ms(HALF_PERIOD_MS);
        led(LED1_PORT, LED1_PIN, 0);
        if (LED2_PIN != 0xFFu)
            led(LED2_PORT, LED2_PIN, 1);
        delay_ms(HALF_PERIOD_MS);
        if (LED2_PIN != 0xFFu)
            led(LED2_PORT, LED2_PIN, 0);
        blink_count++;
    }
}
