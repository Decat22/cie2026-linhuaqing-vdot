#include <stdint.h>
#include <klib.h>

volatile unsigned long cie_mcause = 0;
volatile unsigned long cie_mepc = 0;
volatile unsigned long cie_mtval = 0;

extern long vdot_e16_expect_illegal(void);
extern char cie_vdot_e16_fault_pc[];

int main(void) {
    printf("===== CIE2026 Phase3 VDOT Non-E8 Illegal Test =====\n");
    printf("Requested VTYPE: e16, m1, ta, ma\n");
    printf("Expected exception: Illegal Instruction (mcause=2)\n");

    long trapped = vdot_e16_expect_illegal();
    unsigned long expected_mepc =
        (unsigned long)(uintptr_t)cie_vdot_e16_fault_pc;

    printf("TRAP_RETURN=%ld\n", trapped);
    printf("MCAUSE_AFTER=0x%lx\n", cie_mcause);
    printf("MEPC_AFTER=0x%lx\n", cie_mepc);
    printf("EXPECTED_MEPC=0x%lx\n", expected_mepc);
    printf("MTVAL_AFTER=0x%lx\n", cie_mtval);

    int ok = 1;

    if (trapped == 1) {
        printf("ILLEGAL_TRAP_TAKEN_CHECK=PASS\n");
    } else {
        printf("ILLEGAL_TRAP_TAKEN_CHECK=FAIL\n");
        ok = 0;
    }

    if (cie_mcause == 2) {
        printf("ILLEGAL_MCAUSE_CHECK=PASS\n");
    } else {
        printf("ILLEGAL_MCAUSE_CHECK=FAIL\n");
        ok = 0;
    }

    if (cie_mepc == expected_mepc) {
        printf("ILLEGAL_MEPC_CHECK=PASS\n");
    } else {
        printf("ILLEGAL_MEPC_CHECK=FAIL\n");
        ok = 0;
    }

    /*
     * mtval is recorded for evidence, but is deliberately not
     * a pass/fail gate because implementations may differ in
     * what they write there for an illegal instruction.
     */

    if (ok) {
        printf("VDOT_NON_E8_ILLEGAL_PASS\n");
        return 0;
    }

    printf("VDOT_NON_E8_ILLEGAL_FAIL\n");
    return 1;
}
