    .text
    .align 2

/*
 * CIE2026 Phase3.3 VDOT performance benchmark
 *
 * Fixed architectural operation:
 *
 *   sum(a[i] * b[i]), i=0..7
 *
 * signed INT8 inputs -> signed INT32 result
 *
 * Measured block size:
 *   256 statically-unrolled operations
 *
 * No loop branches exist inside measured regions.
 */

.macro CIE_ENABLE_VS
    li      t6, 1536
    csrs    mstatus, t6
.endm


/* ============================================================
 * Warm-up: custom VDOT, 16 operations
 * ============================================================
 *
 * a0 = A
 * a1 = B
 * a2 = output
 */
    .globl cie_custom_compute_warmup
    .type  cie_custom_compute_warmup, @function

cie_custom_compute_warmup:
    CIE_ENABLE_VS

    /*
     * Custom VDOT only requires SEW=e8.
     *
     * VL=8 means both implementations load exactly the
     * same eight signed INT8 source elements.
     */
    vsetivli zero, 8, e8, m1, ta, ma

    vle8.v      v8, (a0)
    vle8.v      v9, (a1)

    .rept 16
    .word 0x0294050b
    .endr

    vsetivli zero, 1, e32, m1, ta, ma
    vse32.v     v10, (a2)

    ret

    .size cie_custom_compute_warmup, .-cie_custom_compute_warmup


/* ============================================================
 * Warm-up: standard RVV baseline, 16 operations
 * ============================================================
 */
    .globl cie_baseline_compute_warmup
    .type  cie_baseline_compute_warmup, @function

cie_baseline_compute_warmup:
    CIE_ENABLE_VS

    vsetivli zero, 8, e8, mf2, ta, ma

    vle8.v      v8, (a0)
    vle8.v      v9, (a1)

    .rept 16
    vwmul.vv    v10, v8, v9
    vsetivli    zero, 8, e16, m1, ta, ma
    vmv.v.i     v12, 0
    vwredsum.vs v14, v10, v12

    /*
     * Restore the precondition required by the next
     * mathematically identical dot-product invocation.
     */
    vsetivli    zero, 8, e8, mf2, ta, ma
    .endr

    vsetivli zero, 1, e32, m1, ta, ma
    vse32.v     v14, (a2)

    ret

    .size cie_baseline_compute_warmup, .-cie_baseline_compute_warmup


/* ============================================================
 * Compute-only custom benchmark, 256 operations
 * ============================================================
 *
 * a0 = A
 * a1 = B
 * a2 = output
 * a3 = cycle delta pointer
 * a4 = instret delta pointer
 */
    .globl cie_custom_compute_256
    .type  cie_custom_compute_256, @function

cie_custom_compute_256:
    CIE_ENABLE_VS

    /*
     * Input setup is deliberately outside the measured region.
     */
    vsetivli zero, 8, e8, m1, ta, ma
    vle8.v      v8, (a0)
    vle8.v      v9, (a1)

    rdcycle     t0
    rdinstret   t1

    .rept 256
    .word 0x0294050b
    .endr

    rdinstret   t2
    rdcycle     t3

    sub         t3, t3, t0
    sub         t2, t2, t1

    sd          t3, 0(a3)
    sd          t2, 0(a4)

    /*
     * Result extraction is outside the measured region.
     */
    vsetivli zero, 1, e32, m1, ta, ma
    vse32.v     v10, (a2)

    ret

    .size cie_custom_compute_256, .-cie_custom_compute_256


/* ============================================================
 * Compute-only standard RVV baseline, 256 operations
 * ============================================================
 */
    .globl cie_baseline_compute_256
    .type  cie_baseline_compute_256, @function

cie_baseline_compute_256:
    CIE_ENABLE_VS

    /*
     * Source loading is outside the measured region.
     */
    vsetivli zero, 8, e8, mf2, ta, ma
    vle8.v      v8, (a0)
    vle8.v      v9, (a1)

    rdcycle     t0
    rdinstret   t1

    /*
     * Each repeated block begins and ends in the same
     * e8,mf2 state, making every invocation equivalent.
     */
    .rept 256
    vwmul.vv    v10, v8, v9
    vsetivli    zero, 8, e16, m1, ta, ma
    vmv.v.i     v12, 0
    vwredsum.vs v14, v10, v12
    vsetivli    zero, 8, e8, mf2, ta, ma
    .endr

    rdinstret   t2
    rdcycle     t3

    sub         t3, t3, t0
    sub         t2, t2, t1

    sd          t3, 0(a3)
    sd          t2, 0(a4)

    vsetivli zero, 1, e32, m1, ta, ma
    vse32.v     v14, (a2)

    ret

    .size cie_baseline_compute_256, .-cie_baseline_compute_256


/* ============================================================
 * End-to-end custom warm-up, 16 operations
 * ============================================================
 */
    .globl cie_custom_e2e_warmup
    .type  cie_custom_e2e_warmup, @function

cie_custom_e2e_warmup:
    CIE_ENABLE_VS

    .rept 16
    vsetivli zero, 8, e8, m1, ta, ma
    vle8.v      v8, (a0)
    vle8.v      v9, (a1)
    .word       0x0294050b
    vsetivli    zero, 1, e32, m1, ta, ma
    vse32.v     v10, (a2)
    .endr

    ret

    .size cie_custom_e2e_warmup, .-cie_custom_e2e_warmup


/* ============================================================
 * End-to-end baseline warm-up, 16 operations
 * ============================================================
 */
    .globl cie_baseline_e2e_warmup
    .type  cie_baseline_e2e_warmup, @function

cie_baseline_e2e_warmup:
    CIE_ENABLE_VS

    .rept 16
    vsetivli    zero, 8, e8, mf2, ta, ma
    vle8.v      v8, (a0)
    vle8.v      v9, (a1)
    vwmul.vv    v10, v8, v9
    vsetivli    zero, 8, e16, m1, ta, ma
    vmv.v.i     v12, 0
    vwredsum.vs v14, v10, v12
    vsetivli    zero, 1, e32, m1, ta, ma
    vse32.v     v14, (a2)
    .endr

    ret

    .size cie_baseline_e2e_warmup, .-cie_baseline_e2e_warmup


/* ============================================================
 * End-to-end custom benchmark, 256 operations
 * ============================================================
 */
    .globl cie_custom_e2e_256
    .type  cie_custom_e2e_256, @function

cie_custom_e2e_256:
    CIE_ENABLE_VS

    rdcycle     t0
    rdinstret   t1

    .rept 256
    vsetivli zero, 8, e8, m1, ta, ma
    vle8.v      v8, (a0)
    vle8.v      v9, (a1)
    .word       0x0294050b
    vsetivli    zero, 1, e32, m1, ta, ma
    vse32.v     v10, (a2)
    .endr

    rdinstret   t2
    rdcycle     t3

    sub         t3, t3, t0
    sub         t2, t2, t1

    sd          t3, 0(a3)
    sd          t2, 0(a4)

    ret

    .size cie_custom_e2e_256, .-cie_custom_e2e_256


/* ============================================================
 * End-to-end standard RVV baseline, 256 operations
 * ============================================================
 */
    .globl cie_baseline_e2e_256
    .type  cie_baseline_e2e_256, @function

cie_baseline_e2e_256:
    CIE_ENABLE_VS

    rdcycle     t0
    rdinstret   t1

    .rept 256
    vsetivli    zero, 8, e8, mf2, ta, ma
    vle8.v      v8, (a0)
    vle8.v      v9, (a1)
    vwmul.vv    v10, v8, v9
    vsetivli    zero, 8, e16, m1, ta, ma
    vmv.v.i     v12, 0
    vwredsum.vs v14, v10, v12
    vsetivli    zero, 1, e32, m1, ta, ma
    vse32.v     v14, (a2)
    .endr

    rdinstret   t2
    rdcycle     t3

    sub         t3, t3, t0
    sub         t2, t2, t1

    sd          t3, 0(a3)
    sd          t2, 0(a4)

    ret

    .size cie_baseline_e2e_256, .-cie_baseline_e2e_256
