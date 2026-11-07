#include <klib.h>
#include <stdint.h>

extern void vdot_i8(
    const int8_t *a,
    const int8_t *b,
    int32_t *out
);

/*
 * Low 8 elements:
 *   1 + 2 + ... + 8 = 36
 *
 * Upper 8 elements are deliberately non-zero.
 * Official expected result for the low 8 signed INT8 elements is 36.
 */
static const int8_t a[16] __attribute__((aligned(16))) = {
     1,  2,  3,  4,
     5,  6,  7,  8,
     9, 10, 11, 12,
    13, 14, 15, 16
};

static const int8_t b[16] __attribute__((aligned(16))) = {
    1, 1, 1, 1,
    1, 1, 1, 1,
    1, 1, 1, 1,
    1, 1, 1, 1
};

static int32_t out[4] __attribute__((aligned(16))) = {
    0x11111111,
    0x22222222,
    0x33333333,
    0x44444444
};

int main(void)
{
    printf("===== CIE2026 XiangShan Official VDOT Positive Test =====\n");
    printf("Expected low-8 dot = 36\n");

    vdot_i8(a, b, out);

    printf("VDOT result = [%d, %d, %d, %d]\n",
           out[0], out[1], out[2], out[3]);

    if (out[0] == 36 &&
        out[1] == 0 &&
        out[2] == 0 &&
        out[3] == 0) {
        printf("VDOT_POSITIVE_PASS\n");
        return 0;
    }

    printf("VDOT_POSITIVE_FAIL\n");
    return 1;
}
