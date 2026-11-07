    .text
    .align 2

    .globl cie2026_vdot_rvv_baseline
    .type  cie2026_vdot_rvv_baseline, @function

/*
 * CIE2026 mathematically equivalent RVV baseline
 *
 * a0 = pointer to signed INT8 source A
 * a1 = pointer to signed INT8 source B
 * a2 = pointer to signed INT32 result
 *
 * Mathematical operation:
 *
 *   result = sum(A[i] * B[i]), i = 0..7
 *
 * No custom VDOT instruction is used.
 */
cie2026_vdot_rvv_baseline:

    /*
     * VLEN=128, SEW=8, LMUL=mf2:
     *
     * VLMAX = (128 / 8) * 1/2 = 8
     *
     * Therefore exactly the official low eight INT8 elements
     * participate in the computation.
     */
    vsetivli t0, 8, e8, mf2, ta, ma

    vle8.v      v8, (a0)
    vle8.v      v9, (a1)

    /*
     * Signed widening multiply:
     *
     * INT8 x INT8 -> INT16
     *
     * Eight INT16 products occupy 128 bits.
     */
    vwmul.vv    v10, v8, v9

    /*
     * Reinterpret the widening result as eight INT16 elements.
     */
    vsetivli t0, 8, e16, m1, ta, ma

    /*
     * Zero reduction seed.
     *
     * vwredsum.vs uses a widening INT32 accumulator.
     * The low 32 bits of v12 are zero.
     */
    vmv.v.i     v12, 0

    /*
     * Signed widening reduction:
     *
     * eight INT16 products -> one INT32 sum
     */
    vwredsum.vs v14, v10, v12

    /*
     * Store only the scalar 32-bit mathematical result.
     */
    vsetivli t0, 1, e32, m1, ta, ma
    vse32.v     v14, (a2)

    ret

    .size cie2026_vdot_rvv_baseline, .-cie2026_vdot_rvv_baseline
