#include <klib.h>
#include <stdint.h>

extern void vector_add_i32(
    const int32_t *a,
    const int32_t *b,
    int32_t *c,
    unsigned long n
);

int main()
{
    int32_t a[4] = {1, 2, 3, 4};
    int32_t b[4] = {10, 20, 30, 40};
    int32_t c[4] = {0, 0, 0, 0};

    printf("===== CIE2026 XiangShan RVV Vector Add =====\n");

    printf("A = [%d, %d, %d, %d]\n",
           a[0], a[1], a[2], a[3]);

    printf("B = [%d, %d, %d, %d]\n",
           b[0], b[1], b[2], b[3]);

    vector_add_i32(a, b, c, 4);

    printf("C = [%d, %d, %d, %d]\n",
           c[0], c[1], c[2], c[3]);

    if (c[0] == 11 &&
        c[1] == 22 &&
        c[2] == 33 &&
        c[3] == 44) {
        printf("VECTOR_ADD_PASS\n");
        return 0;
    }

    printf("VECTOR_ADD_FAIL\n");
    return 1;
}
