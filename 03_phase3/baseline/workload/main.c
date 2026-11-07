#include <stdint.h>
#include <klib.h>

extern void cie2026_vdot_rvv_baseline(
    const int8_t *a,
    const int8_t *b,
    int32_t *out
);

static int32_t out __attribute__((aligned(16)));

/*
 * Positive:
 *
 * low 8 = 1 + 2 + ... + 8 = 36
 */
static const int8_t a_positive[16]
__attribute__((aligned(16))) = {
      1,   2,   3,   4,
      5,   6,   7,   8,
      9,  10,  11,  12,
     13,  14,  15,  16
};

static const int8_t b_ones[16]
__attribute__((aligned(16))) = {
      1,   1,   1,   1,
      1,   1,   1,   1,
      1,   1,   1,   1,
      1,   1,   1,   1
};

/*
 * Negative:
 *
 * low 8 = -(1 + 2 + ... + 8) = -36
 */
static const int8_t a_negative[16]
__attribute__((aligned(16))) = {
     -1,  -2,  -3,  -4,
     -5,  -6,  -7,  -8,
     -9, -10, -11, -12,
    -13, -14, -15, -16
};

/*
 * Boundary operands.
 */
static const int8_t a_min[16]
__attribute__((aligned(16))) = {
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128
};

static const int8_t b_min[16]
__attribute__((aligned(16))) = {
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128,
    -128, -128, -128, -128
};

static const int8_t b_max[16]
__attribute__((aligned(16))) = {
     127,  127,  127,  127,
     127,  127,  127,  127,
     127,  127,  127,  127,
     127,  127,  127,  127
};

/*
 * Mixed-sign case.
 *
 * Low eight dot product:
 *
 * 127*2 + (-128)*1 + 0*127 + 127*(-1)
 * + (-128)*(-1) + 0*(-128) + 127*0 + (-128)*0
 *
 * = 127
 */
static const int8_t a_mixed[16]
__attribute__((aligned(16))) = {
     127, -128,    0,  127,
    -128,    0,  127, -128,
       0,    1,   -1,   64,
     -64,  100, -100,    0
};

static const int8_t b_mixed[16]
__attribute__((aligned(16))) = {
       2,    1,  127,   -1,
      -1, -128,    0,    0,
       0,    1,    1,    1,
       1,    1,    1,    1
};

/*
 * Upper-half poison case.
 *
 * Low eight values are identical to mixed.
 * Bytes 8..15 are deliberately 127.
 *
 * Correct official 8-term result remains 127.
 */
static const int8_t a_upper_poison[16]
__attribute__((aligned(16))) = {
     127, -128,    0,  127,
    -128,    0,  127, -128,
     127,  127,  127,  127,
     127,  127,  127,  127
};

static const int8_t b_upper_poison[16]
__attribute__((aligned(16))) = {
       2,    1,  127,   -1,
      -1, -128,    0,    0,
     127,  127,  127,  127,
     127,  127,  127,  127
};

static int run_case(
    const char *name,
    const int8_t *a,
    const int8_t *b,
    int32_t expected
)
{
    out = 0x5a5a5a5a;

    cie2026_vdot_rvv_baseline(a, b, &out);

    printf(
        "%s result = %d, expected = %d\n",
        name,
        out,
        expected
    );

    if (out == expected) {
        printf("%s_PASS\n", name);
        return 0;
    }

    printf("%s_FAIL\n", name);
    return 1;
}

int main(void)
{
    int fail = 0;

    printf(
        "===== CIE2026 Phase3 Mathematically Equivalent RVV Baseline =====\n"
    );

    fail |= run_case(
        "BASELINE_POSITIVE_36",
        a_positive,
        b_ones,
        36
    );

    fail |= run_case(
        "BASELINE_NEGATIVE_MINUS36",
        a_negative,
        b_ones,
        -36
    );

    fail |= run_case(
        "BASELINE_MAX_POS",
        a_min,
        b_min,
        131072
    );

    fail |= run_case(
        "BASELINE_MAX_NEG",
        a_min,
        b_max,
        -130048
    );

    fail |= run_case(
        "BASELINE_MIXED",
        a_mixed,
        b_mixed,
        127
    );

    fail |= run_case(
        "BASELINE_UPPER_HALF_IGNORED",
        a_upper_poison,
        b_upper_poison,
        127
    );

    if (fail == 0) {
        printf("RVV_BASELINE_ALL_PASS\n");
        return 0;
    }

    printf("RVV_BASELINE_FAIL\n");
    return 1;
}
