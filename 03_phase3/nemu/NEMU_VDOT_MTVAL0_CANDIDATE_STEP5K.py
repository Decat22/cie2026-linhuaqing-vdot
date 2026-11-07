#!/usr/bin/env python3

import ctypes
import sys

SO = sys.argv[1]

FAULT_PC = 0x80000000
MTVEC = 0x80000100
INSTR = 0x0294050B

# CPU_state offsets established in the frozen Phase3 ABI audit.
OFF_MODE     = 0x200
OFF_MSTATUS  = 0x208
OFF_MEPC     = 0x218
OFF_MTVAL    = 0x228
OFF_MTVEC    = 0x238
OFF_MCAUSE   = 0x248
OFF_PC       = 0x290

OFF_V8       = 0x3A0
OFF_V9       = 0x3B0
OFF_V10      = 0x3C0

OFF_VSTART   = 0x520
OFF_VL       = 0x540
OFF_VTYPE    = 0x548
OFF_VLENB    = 0x550

STATE_SIZE = 0x800

DIFFTEST_TO_DUT = False
DIFFTEST_TO_REF = True

VTYPE_E16_M1_TA_MA = 0xC8
MSTATUS_VS_MASK = 0x600

lib = ctypes.CDLL(SO)

lib.difftest_init.argtypes = []
lib.difftest_init.restype = None

lib.difftest_memcpy.argtypes = [
    ctypes.c_uint64,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_bool,
]
lib.difftest_memcpy.restype = None

lib.difftest_regcpy.argtypes = [
    ctypes.c_void_p,
    ctypes.c_bool,
]
lib.difftest_regcpy.restype = None

lib.difftest_exec.argtypes = [ctypes.c_uint64]
lib.difftest_exec.restype = None

state = (ctypes.c_ubyte * STATE_SIZE)()

def get64(off):
    return ctypes.c_uint64.from_buffer(state, off).value

def put64(off, val):
    ctypes.c_uint64.from_buffer(state, off).value = val & 0xffffffffffffffff

def put_bytes(off, data):
    for i, b in enumerate(data):
        state[off + i] = b

def get_bytes(off, n):
    return bytes(state[off:off+n])

def vec128_hex(off):
    value = int.from_bytes(get_bytes(off, 16), byteorder="little", signed=False)
    return f"{value:032x}"

def gate(name, cond):
    print(f"{name}={'PASS' if cond else 'FAIL'}")
    return bool(cond)

print("===== NEMU CANDIDATE VDOT NON-E8 ILLEGAL MICROTEST =====")
print(f"SO={SO}")

lib.difftest_init()

# Read initialized reference state first so unrelated architectural fields
# remain exactly as initialized by NEMU.
lib.difftest_regcpy(ctypes.byref(state), DIFFTEST_TO_DUT)

print(f"INITIAL_PC=0x{get64(OFF_PC):016x}")
print(f"INITIAL_MODE={get64(OFF_MODE)}")
print(f"INITIAL_MSTATUS=0x{get64(OFF_MSTATUS):016x}")
print(f"INITIAL_VLENB={get64(OFF_VLENB)}")

# Install one custom VDOT instruction at the test PC.
instr_bytes = INSTR.to_bytes(4, byteorder="little")
instr_buf = ctypes.create_string_buffer(instr_bytes, 4)

lib.difftest_memcpy(
    FAULT_PC,
    ctypes.cast(instr_buf, ctypes.c_void_p),
    4,
    DIFFTEST_TO_REF,
)

# Configure architectural state.
put64(OFF_MODE, 3)
put64(OFF_PC, FAULT_PC)

put64(
    OFF_MSTATUS,
    get64(OFF_MSTATUS) | MSTATUS_VS_MASK
)

put64(OFF_MTVEC, MTVEC)

# Poison trap CSRs so the test proves they are actually overwritten.
put64(OFF_MEPC,   0x1111111111111111)
put64(OFF_MCAUSE, 0x2222222222222222)
put64(OFF_MTVAL,  0x3333333333333333)

# e16 is intentionally unsupported by the frozen custom VDOT.
put64(OFF_VSTART, 0)
put64(OFF_VL, 16)
put64(OFF_VTYPE, VTYPE_E16_M1_TA_MA)
put64(OFF_VLENB, 16)

v8_before = bytes([
    0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
    0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18
])

v9_before = bytes([
    0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,
    0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38
])

v10_before = bytes([0xA5] * 16)

put_bytes(OFF_V8,  v8_before)
put_bytes(OFF_V9,  v9_before)
put_bytes(OFF_V10, v10_before)

print(f"PC_BEFORE=0x{get64(OFF_PC):016x}")
print(f"MTVEC_BEFORE=0x{get64(OFF_MTVEC):016x}")
print(f"VTYPE_BEFORE=0x{get64(OFF_VTYPE):016x}")
print(f"VL_BEFORE={get64(OFF_VL)}")
print(f"VSTART_BEFORE={get64(OFF_VSTART)}")
print(f"V8_BEFORE={vec128_hex(OFF_V8)}")
print(f"V9_BEFORE={vec128_hex(OFF_V9)}")
print(f"V10_BEFORE={vec128_hex(OFF_V10)}")

# Push state to reference and execute exactly one instruction.
lib.difftest_regcpy(ctypes.byref(state), DIFFTEST_TO_REF)
lib.difftest_exec(1)

# Read architectural state back.
lib.difftest_regcpy(ctypes.byref(state), DIFFTEST_TO_DUT)

pc_after     = get64(OFF_PC)
mepc_after   = get64(OFF_MEPC)
mcause_after = get64(OFF_MCAUSE)
mtval_after  = get64(OFF_MTVAL)
mtvec_after  = get64(OFF_MTVEC)

v8_after  = get_bytes(OFF_V8, 16)
v9_after  = get_bytes(OFF_V9, 16)
v10_after = get_bytes(OFF_V10, 16)

print()
print("===== AFTER ONE CUSTOM VDOT INSTRUCTION =====")
print(f"PC_AFTER=0x{pc_after:016x}")
print(f"MEPC_AFTER=0x{mepc_after:016x}")
print(f"MCAUSE_AFTER=0x{mcause_after:016x}")
print(f"MTVAL_AFTER=0x{mtval_after:016x}")
print(f"MTVEC_AFTER=0x{mtvec_after:016x}")

print(f"VTYPE_AFTER=0x{get64(OFF_VTYPE):016x}")
print(f"VL_AFTER={get64(OFF_VL)}")
print(f"VSTART_AFTER={get64(OFF_VSTART)}")

print(f"V8_AFTER={vec128_hex(OFF_V8)}")
print(f"V9_AFTER={vec128_hex(OFF_V9)}")
print(f"V10_AFTER={vec128_hex(OFF_V10)}")

print()
print("===== PASS/FAIL GATES =====")

checks = []

checks.append(gate(
    "TRAP_PC_CHECK",
    pc_after == MTVEC
))

checks.append(gate(
    "MEPC_CHECK",
    mepc_after == FAULT_PC
))

checks.append(gate(
    "MCAUSE_ILLEGAL_CHECK",
    mcause_after == 2
))

checks.append(gate(
    "MTVAL_ZERO_CHECK",
    mtval_after == 0
))

checks.append(gate(
    "MTVEC_PRESERVED_CHECK",
    mtvec_after == MTVEC
))

checks.append(gate(
    "V8_PRESERVED_CHECK",
    v8_after == v8_before
))

checks.append(gate(
    "V9_PRESERVED_CHECK",
    v9_after == v9_before
))

checks.append(gate(
    "V10_UNCHANGED_CHECK",
    v10_after == v10_before
))

checks.append(gate(
    "VTYPE_PRESERVED_CHECK",
    get64(OFF_VTYPE) == VTYPE_E16_M1_TA_MA
))

checks.append(gate(
    "VL_PRESERVED_CHECK",
    get64(OFF_VL) == 16
))

checks.append(gate(
    "VSTART_ZERO_CHECK",
    get64(OFF_VSTART) == 0
))

all_pass = all(checks)

print()
if all_pass:
    print("VDOT_MTVAL0_CANDIDATE_PASS")
else:
    print("VDOT_MTVAL0_CANDIDATE_FAIL")

raise SystemExit(0 if all_pass else 1)
