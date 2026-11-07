#include <stdint.h>
#include <klib.h>

extern void cie2026_measure_loop(
    uint64_t iterations,
    uint64_t *cycle_delta,
    uint64_t *instret_delta
);

int main(void)
{
    uint64_t cycle16 = 0;
    uint64_t inst16 = 0;

    uint64_t cycle64 = 0;
    uint64_t inst64 = 0;

    printf("===== CIE2026 Phase3 Counter Runtime Sanity =====\n");

    cie2026_measure_loop(16, &cycle16, &inst16);
    cie2026_measure_loop(64, &cycle64, &inst64);

    printf("CYCLE_DELTA_16=%d\n", (int)cycle16);
    printf("INSTRET_DELTA_16=%d\n", (int)inst16);

    printf("CYCLE_DELTA_64=%d\n", (int)cycle64);
    printf("INSTRET_DELTA_64=%d\n", (int)inst64);

    /*
     * We only require:
     *
     * 1. rdcycle changes over a non-empty measured region.
     * 2. rdinstret changes.
     * 3. A 64-iteration loop retires more instructions
     *    than a 16-iteration loop.
     *
     * We intentionally do NOT require cycle64 > cycle16
     * as an architectural rule; cycle count is microarchitectural.
     */
    if (cycle16 > 0 &&
        cycle64 > 0 &&
        inst16 > 0 &&
        inst64 > inst16) {

        printf("PERF_COUNTER_SANITY_PASS\n");
        return 0;
    }

    printf("PERF_COUNTER_SANITY_FAIL\n");
    return 1;
}
