.section .text
.align 2

.globl vector_add_i32
.type vector_add_i32, @function

vector_add_i32:
    # a0 = src1
    # a1 = src2
    # a2 = dst
    # a3 = element count

    # Enable RISC-V Vector state.
    # mstatus.VS = 11 (Dirty), bits [10:9].
    li t1, 0x600
    csrs mstatus, t1

    vsetvli t0, a3, e32, m1, ta, ma

    vle32.v v1, (a0)
    vle32.v v2, (a1)

    vadd.vv v3, v1, v2

    vse32.v v3, (a2)

    ret

.size vector_add_i32, .-vector_add_i32
