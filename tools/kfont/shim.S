/* 게임 EE ABI <-> o32 C 연결 */
.set noreorder
.set noat
.set hardfloat
.macro SAVE
    .word 0x7fb00040
    .word 0x7fb10050
    .word 0x7fb20060
    .word 0x7fb30070
    .word 0x7fb40080
    .word 0x7fb50090
    .word 0x7fb600a0
    .word 0x7fb700b0
    .word 0x7fbe00c0
    .word 0x7fbf00d0
.endm
.macro REST
    .word 0x7bb00040
    .word 0x7bb10050
    .word 0x7bb20060
    .word 0x7bb30070
    .word 0x7bb40080
    .word 0x7bb50090
    .word 0x7bb600a0
    .word 0x7bb700b0
    .word 0x7bbe00c0
    .word 0x7bbf00d0
.endm

.section .tdraw,"ax"
    j e_draw
    nop
    j e_measure
    nop
.globl e_draw
e_draw:                         /* a0=x a1=y a2=str a3=spacing t0=font t1=color t2=clip t3=noDraw */
    addiu $sp, $sp, -224
    SAVE
    sw $a2, 16($sp); sw $t0, 20($sp); sw $a3, 24($sp); sw $zero, 28($sp); sw $zero, 32($sp)
    sltiu $v0, $t3, 1
    sw $v0, 36($sp); sw $a0, 40($sp); sw $a1, 44($sp); sw $t1, 48($sp); sw $t2, 52($sp)
    jal kwalk
    addiu $a0, $sp, 16
    REST
    jr $ra
    addiu $sp, $sp, 224

.section .tmeas,"ax"
.globl e_measure
e_measure:                      /* a0=str a1=font a2=spacing a3=maxw t0=outcnt */
    addiu $sp, $sp, -224
    SAVE
    sw $a0, 16($sp); sw $a1, 20($sp); sw $a2, 24($sp); sw $a3, 28($sp); sw $t0, 32($sp)
    sw $zero, 36($sp); sw $zero, 40($sp); sw $zero, 44($sp); sw $zero, 48($sp); sw $zero, 52($sp)
    jal kwalk
    addiu $a0, $sp, 16
    REST
    jr $ra
    addiu $sp, $sp, 224

.globl g_setup
g_setup:
    move $t9, $sp
    addiu $sp, $sp, -32
    addiu $at, $zero, -16
    and $sp, $sp, $at
    sw $t9, 0($sp)
    sw $ra, 4($sp)
    jal 0x23e6f8
    nop
    lw $ra, 4($sp)
    jr $ra
    lw $sp, 0($sp)

.globl g_map
g_map:
    j 0x23fb40
    nop

.globl g_mul
g_mul:
    mtc1 $a0, $f0
    cvt.s.w $f0, $f0
    mtc1 $a1, $f1
    mul.s $f0, $f0, $f1
    cvt.w.s $f0, $f0
    jr $ra
    mfc1 $v0, $f0

.globl g_scale
g_scale:
    move $t9, $sp
    addiu $sp, $sp, -32
    addiu $at, $zero, -16
    and $sp, $sp, $at
    sw $t9, 0($sp)
    sw $ra, 4($sp)
    lui $t0, 0x39
    lw $a0, 0x2388($t0)
    lw $t1, 0x258($a0)
    lh $t2, 0x150($t1)
    lw $t1, 0x154($t1)
    jalr $t1
    addu $a0, $a0, $t2
    mfc1 $v0, $f0
    lw $ra, 4($sp)
    jr $ra
    lw $sp, 0($sp)

.globl g_fmul
g_fmul:
    mtc1 $a0, $f0
    mtc1 $a1, $f1
    mul.s $f0, $f0, $f1
    jr $ra
    mfc1 $v0, $f0

.globl g_draw                   /* o32: a0=tex a1=x a2=y a3=u, 16:v 20:w 24:h 28:ctx 32:xscale 36:yscale */
g_draw:
    lw $t0, 16($sp)
    lw $t1, 20($sp)
    lw $t2, 24($sp)
    lw $t4, 28($sp)
    lw $t5, 32($sp)
    lw $t8, 36($sp)
    lw $t3, 36($t4)
    lw $t6, 32($t4)
    move $t9, $sp
    addiu $sp, $sp, -48
    addiu $at, $zero, -16
    and $sp, $sp, $at
    sw $t9, 32($sp)
    sw $ra, 36($sp)
    sw $zero, 0($sp)
    sw $zero, 4($sp)
    sw $t6, 8($sp)
    sw $zero, 12($sp)
    mtc1 $t5, $f12
    mtc1 $t8, $f13
    lw $t7, 0x18($a0)
    lh $t8, 0xb8($t7)
    lw $t7, 0xbc($t7)
    jalr $t7
    addu $a0, $a0, $t8
    lw $ra, 36($sp)
    jr $ra
    lw $sp, 32($sp)


.section .kdata,"a"
.balign 128
.globl kpal
kpal:
    .incbin "kpal.bin"
.balign 128
.globl kmap
kmap:
    .incbin "kmap.bin"
.balign 128
.globl kpix
kpix:
    .incbin "kpix.bin"
