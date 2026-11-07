    .text
    .align 2

    .globl cie2026_measure_loop
    .type cie2026_measure_loop, @function

/*
 * a0 = iteration count
 * a1 = uint64_t *cycle_delta
 * a2 = uint64_t *instret_delta
 */
cie2026_measure_loop:
    mv        t2, a0

    rdcycle   t0
    rdinstret t1

1:
    addi      t2, t2, -1
    bnez      t2, 1b

    rdcycle   t3
    rdinstret t4

    sub       t3, t3, t0
    sub       t4, t4, t1

    sd        t3, 0(a1)
    sd        t4, 0(a2)

    ret

    .size cie2026_measure_loop, .-cie2026_measure_loop
