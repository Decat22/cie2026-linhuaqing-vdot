.section .text
.align 2

.globl vdot_i8
.type vdot_i8, @function

vdot_i8:
    # a0 = int8_t src1[16]
    # a1 = int8_t src2[16]
    # a2 = int32_t dst[4]

    # Enable vector state: mstatus.VS = Dirty
    li t1, 0x600
    csrs mstatus, t1

    # Load the complete 128-bit source registers.
    #
    # VL=16 is intentional for the TEST LOAD:
    # it gives us controlled values in all 16 source bytes so that
    # we can prove the custom VDOT ignores bytes 8..15.
    vsetivli t0, 16, e8, m1, ta, ma

    # v8 = src1[0..15]
    # v9 = src2[0..15]
    vle8.v v8, (a0)
    vle8.v v9, (a1)

    # CIE2026 custom instruction:
    # vdot.vv v10, v8, v9
    #
    # Official arithmetic semantics:
    #   result = sum(i=0..7) signed(v8[i]) * signed(v9[i])
    #   v10[31:0]   = signed INT32 result
    #   v10[127:32] = 0
    #   source bytes v8[127:64] and v9[127:64] are ignored
    #
    # funct7 = 0000001
    # vs2    = v9
    # vs1    = v8
    # funct3 = 000
    # vd     = v10
    # opcode = 0001011 (custom-0)
    #
    # encoding = 0x0294050b
    .word 0x0294050b

    # Store the complete 128-bit destination so tests can also verify
    # that vd[127:32] is zero.
    vsetivli t0, 4, e32, m1, ta, ma
    vse32.v v10, (a2)

    ret

.size vdot_i8, .-vdot_i8
