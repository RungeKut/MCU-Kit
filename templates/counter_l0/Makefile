# Сборка: make GCC_BIN=<папка с arm-none-eabi-gcc>/   (mcukit.build задаёт сам)
#
# cortex-m0plus: только Thumb, нет FPU — в отличие от blink_f4
# (cortex-m4, -mfloat-abi=soft) для этого ядра -mfloat-abi не нужен.
# -ffreestanding -fno-tree-loop-distribute-patterns: без них GCC с -Os
# превращает циклы копирования .data и обнуления .bss в вызовы memcpy и
# memset, которых при -nostdlib нет (knowledge/30_ГРАБЛИ/30-04).
TARGET  = app
GCC_BIN ?=
CC      = $(GCC_BIN)arm-none-eabi-gcc
OBJCOPY = $(GCC_BIN)arm-none-eabi-objcopy
SIZE    = $(GCC_BIN)arm-none-eabi-size

CFLAGS  = -mcpu=cortex-m0plus -mthumb -Os -g -Wall -Wextra \
          -ffunction-sections -fdata-sections \
          -ffreestanding -fno-tree-loop-distribute-patterns
LDFLAGS = -T link.ld -nostartfiles -nostdlib -Wl,--gc-sections \
          -Wl,-Map=build/$(TARGET).map

SRC = $(wildcard src/*.c)

all: build/$(TARGET).bin build/$(TARGET).hex

build/$(TARGET).elf: $(SRC) link.ld
	@mkdir -p build
	$(CC) $(CFLAGS) $(SRC) $(LDFLAGS) -o $@
	$(SIZE) $@

build/$(TARGET).bin: build/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

build/$(TARGET).hex: build/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

clean:
	rm -rf build

.PHONY: all clean
