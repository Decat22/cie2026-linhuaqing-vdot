#include <klib.h>
#include <stdint.h>

extern void vdot_i8(
    const int8_t *a,
    const int8_t *b,
    int32_t *out
);

static const int8_t a_min[16] __attribute__((aligned(16))) = {
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128
};

static const int8_t b_min[16] __attribute__((aligned(16))) = {
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128
};

static const int8_t b_max[16] __attribute__((aligned(16))) = {
    127, 127, 127, 127,
    127, 127, 127, 127,
    127, 127, 127, 127,
    127, 127, 127, 127
};

static const int8_t a_mix[16] __attribute__((aligned(16))) = {
     127, -128,    0,  127,
    -128,    0,  127, -128,
       0,    1,   -1,   64,
     -64,  100, -100,    0
};

static const int8_t b_mix[16] __attribute__((aligned(16))) = {
       2,    1,  127,   -1,
      -1, -128,    0,    0,
       0,    1,    1,    1,
       1,    1,    1,    1
};

/*
 * Low 8 elements are identical to a_mix/b_mix.
 *
 * Upper 8 elements are deliberately chosen so that an incorrect
 * 16-element implementation would add a large non-zero contribution:
 *
 *   8 * (127 * 127) = 129032
 *
 * Correct official VDOT semantics must ignore these upper bytes.
 */
static const int8_t a_upper_poison[16] __attribute__((aligned(16))) = {
     127, -128,    0,  127,
    -128,    0,  127, -128,
     127,  127,  127,  127,
     127,  127,  127,  127
};

static const int8_t b_upper_poison[16] __attribute__((aligned(16))) = {
       2,    1,  127,   -1,
      -1, -128,    0,    0,
     127,  127,  127,  127,
     127,  127,  127,  127
};

static int32_t out[4] __attribute__((aligned(16)));

static int check_result(const char *name, int32_t expected)
{
    printf("%s result = [%d, %d, %d, %d], expected = %d\n",
           name,
           out[0], out[1], out[2], out[3],
           expected);

    if (out[0] != expected ||
        out[1] != 0 ||
        out[2] != 0 ||
        out[3] != 0) {
        printf("%s_FAIL\n", name);
        return 1;
    }

    printf("%s_PASS\n", name);
    return 0;
}

int main(void)
{
    int fail = 0;

    printf("===== CIE2026 XiangShan Official VDOT 8-Term Test =====\n");

    /*
     * Case 1:
     * Only low 8 elements participate.
     *
     * 8 * (-128 * -128)
     * = 8 * 16384
     * = 131072
     */
    vdot_i8(a_min, b_min, out);
    fail |= check_result("VDOT_BOUNDARY_MAX_POS", 131072);

    /*
     * Case 2:
     * 8 * (-128 * 127)
     * = 8 * (-16256)
     * = -130048
     */
    vdot_i8(a_min, b_max, out);
    fail |= check_result("VDOT_BOUNDARY_MAX_NEG", -130048);

    /*
     * Case 3:
     * Low 8 products:
     *
     * 127*2 + (-128)*1 + 0*127 + 127*(-1)
     * + (-128)*(-1) + 0*(-128) + 127*0 + (-128)*0
     *
     * = 127
     */
    vdot_i8(a_mix, b_mix, out);
    fail |= check_result("VDOT_BOUNDARY_MIXED", 127);

    /*
     * Case 4:
     * Same low 8 elements as Case 3.
     * Upper 8 bytes contain large non-zero poison values.
     *
     * Correct result must remain 127.
     */
    vdot_i8(a_upper_poison, b_upper_poison, out);
    fail |= check_result("VDOT_UPPER_HALF_IGNORED", 127);

    if (fail == 0) {
        printf("VDOT_OFFICIAL_8TERM_ALL_PASS\n");
        return 0;
    }

    printf("VDOT_OFFICIAL_8TERM_FAIL\n");
    return 1;
}
