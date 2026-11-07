    .section .text
    .balign 4

    .globl vdot_e16_expect_illegal
    .type  vdot_e16_expect_illegal, @function

vdot_e16_expect_illegal:
    addi sp, sp, -16
    sd   s0, 0(sp)
    sd   ra, 8(sp)

    /* Preserve the original machine trap vector. */
    csrr s0, mtvec

    /* Install our local direct-mode trap handler. */
    la   t0, .Ltrap_handler
    csrw mtvec, t0

    /* Enable vector state: mstatus.VS = Dirty. */
    li   t0, 0x600
    csrs mstatus, t0

    /*
     * vsetivli t0, 8, e16, m1, ta, ma
     *
     * Raw encoding is used so this test does not depend on the
     * assembler being invoked with the V extension enabled.
     */
    .word 0xcc8472d7

    /*
     * The CIE2026 custom vdot.vv instruction MUST be illegal
     * when vsew != e8.
     */
    .globl cie_vdot_e16_fault_pc
cie_vdot_e16_fault_pc:
    .word 0x0294050b

    /*
     * Reaching here directly means the custom instruction did
     * not raise the required exception.
     */
    li   a0, 0
    j    .Ldone

    .balign 4
.Ltrap_handler:
    csrr t0, mcause
    la   t1, cie_mcause
    sd   t0, 0(t1)

    csrr t2, mepc
    la   t1, cie_mepc
    sd   t2, 0(t1)

    csrr t3, mtval
    la   t1, cie_mtval
    sd   t3, 0(t1)

    /*
     * Required architectural checks:
     *   mcause == 2
     *   mepc   == address of the custom VDOT instruction
     */
    li   t1, 2
    bne  t0, t1, .Ltrap_fail

    la   t1, cie_vdot_e16_fault_pc
    bne  t2, t1, .Ltrap_fail

    li   a0, 1
    j    .Ltrap_resume

.Ltrap_fail:
    li   a0, 0

.Ltrap_resume:
    /*
     * Skip the faulting instruction and return from the trap.
     */
    la   t0, .Lresume
    csrw mepc, t0
    mret

.Lresume:
.Ldone:
    csrw mtvec, s0

    ld   s0, 0(sp)
    ld   ra, 8(sp)
    addi sp, sp, 16
    ret

    .size vdot_e16_expect_illegal, .-vdot_e16_expect_illegal
