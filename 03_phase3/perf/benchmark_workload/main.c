#include <stdint.h>
#include <klib.h>

#define SAMPLES 5

extern void cie_custom_compute_warmup(
    const int8_t *, const int8_t *, int32_t *
);

extern void cie_baseline_compute_warmup(
    const int8_t *, const int8_t *, int32_t *
);

extern void cie_custom_e2e_warmup(
    const int8_t *, const int8_t *, int32_t *
);

extern void cie_baseline_e2e_warmup(
    const int8_t *, const int8_t *, int32_t *
);

extern void cie_custom_compute_256(
    const int8_t *, const int8_t *, int32_t *,
    uint64_t *, uint64_t *
);

extern void cie_baseline_compute_256(
    const int8_t *, const int8_t *, int32_t *,
    uint64_t *, uint64_t *
);

extern void cie_custom_e2e_256(
    const int8_t *, const int8_t *, int32_t *,
    uint64_t *, uint64_t *
);

extern void cie_baseline_e2e_256(
    const int8_t *, const int8_t *, int32_t *,
    uint64_t *, uint64_t *
);

/*
 * Official mixed-sign low-eight case.
 *
 * Expected:
 * 127
 */
static const int8_t input_a[16]
__attribute__((aligned(16))) = {
     127, -128,    0,  127,
    -128,    0,  127, -128,

      55,   66,   77,   88,
      99,  100,  101,  102
};

static const int8_t input_b[16]
__attribute__((aligned(16))) = {
       2,    1,  127,   -1,
      -1, -128,    0,    0,

     -55,  -66,  -77,  -88,
     -99, -100, -101, -102
};

static int32_t out_custom_compute __attribute__((aligned(16)));
static int32_t out_base_compute   __attribute__((aligned(16)));
static int32_t out_custom_e2e     __attribute__((aligned(16)));
static int32_t out_base_e2e       __attribute__((aligned(16)));

static uint64_t cc_cycles[SAMPLES];
static uint64_t cc_instret[SAMPLES];

static uint64_t bc_cycles[SAMPLES];
static uint64_t bc_instret[SAMPLES];

static uint64_t ce_cycles[SAMPLES];
static uint64_t ce_instret[SAMPLES];

static uint64_t be_cycles[SAMPLES];
static uint64_t be_instret[SAMPLES];

int main(void)
{
    int fail = 0;

    printf("===== CIE2026 Phase3 VDOT Performance Benchmark =====\n");
    printf("MEASURED_OPERATIONS_PER_SAMPLE=256\n");
    printf("SAMPLES=5\n");
    printf("EXPECTED_RESULT=127\n");

    /*
     * Exactly 16 unmeasured warm-up operations for each path.
     */
    cie_custom_compute_warmup(
        input_a, input_b, &out_custom_compute
    );

    cie_baseline_compute_warmup(
        input_a, input_b, &out_base_compute
    );

    cie_custom_e2e_warmup(
        input_a, input_b, &out_custom_e2e
    );

    cie_baseline_e2e_warmup(
        input_a, input_b, &out_base_e2e
    );

    /*
     * No printf occurs inside or between the assembly counter
     * boundaries of any measured kernel.
     */
    for (int i = 0; i < SAMPLES; i++) {

        cie_custom_compute_256(
            input_a,
            input_b,
            &out_custom_compute,
            &cc_cycles[i],
            &cc_instret[i]
        );

        cie_baseline_compute_256(
            input_a,
            input_b,
            &out_base_compute,
            &bc_cycles[i],
            &bc_instret[i]
        );

        cie_custom_e2e_256(
            input_a,
            input_b,
            &out_custom_e2e,
            &ce_cycles[i],
            &ce_instret[i]
        );

        cie_baseline_e2e_256(
            input_a,
            input_b,
            &out_base_e2e,
            &be_cycles[i],
            &be_instret[i]
        );
    }

    if (out_custom_compute != 127) fail = 1;
    if (out_base_compute   != 127) fail = 1;
    if (out_custom_e2e     != 127) fail = 1;
    if (out_base_e2e       != 127) fail = 1;

    printf(
        "CUSTOM_COMPUTE_RESULT=%d\n",
        out_custom_compute
    );

    printf(
        "BASELINE_COMPUTE_RESULT=%d\n",
        out_base_compute
    );

    printf(
        "CUSTOM_E2E_RESULT=%d\n",
        out_custom_e2e
    );

    printf(
        "BASELINE_E2E_RESULT=%d\n",
        out_base_e2e
    );

    for (int i = 0; i < SAMPLES; i++) {

        printf(
            "SAMPLE_%d_CUSTOM_COMPUTE_CYCLES=%d\n",
            i,
            (int)cc_cycles[i]
        );

        printf(
            "SAMPLE_%d_CUSTOM_COMPUTE_INSTRET=%d\n",
            i,
            (int)cc_instret[i]
        );

        printf(
            "SAMPLE_%d_BASELINE_COMPUTE_CYCLES=%d\n",
            i,
            (int)bc_cycles[i]
        );

        printf(
            "SAMPLE_%d_BASELINE_COMPUTE_INSTRET=%d\n",
            i,
            (int)bc_instret[i]
        );

        printf(
            "SAMPLE_%d_CUSTOM_E2E_CYCLES=%d\n",
            i,
            (int)ce_cycles[i]
        );

        printf(
            "SAMPLE_%d_CUSTOM_E2E_INSTRET=%d\n",
            i,
            (int)ce_instret[i]
        );

        printf(
            "SAMPLE_%d_BASELINE_E2E_CYCLES=%d\n",
            i,
            (int)be_cycles[i]
        );

        printf(
            "SAMPLE_%d_BASELINE_E2E_INSTRET=%d\n",
            i,
            (int)be_instret[i]
        );
    }

    if (fail == 0) {
        printf("VDOT_PERF_FUNCTIONAL_RESULT_PASS\n");
        return 0;
    }

    printf("VDOT_PERF_FUNCTIONAL_RESULT_FAIL\n");
    return 1;
}
