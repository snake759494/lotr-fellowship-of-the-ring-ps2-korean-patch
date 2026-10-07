MEMORY { K (rx) : ORIGIN = 0x466180, LENGTH = 0x1000000 }
SECTIONS {
  .k : { *(.tdraw) *(.tmeas) *(.text*) *(.rodata*) *(.sdata*) *(.data*) *(.kdata) } > K
  /DISCARD/ : { *(.MIPS.abiflags) *(.reginfo) *(.comment) *(.pdr) *(.gnu.attributes) *(.eh_frame*) *(.got) *(.bss*) }
}
