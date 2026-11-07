import ctypes
import struct
import sys

SO = sys.argv[1]

DIFFTEST_TO_DUT = False
DIFFTEST_TO_REF = True

TEST_PC = 0x80000000
TRAP_PC = 0x80000100

VDOT_INSTR = 0x0294050B

# jal x0, 0
# A harmless self-loop at mtvec in case NEMU continues far enough
# to execute one instruction in the trap handler.
TRAP_LOOP_INSTR = 0x0000006F

# Confirmed CPU_state layout for this exact NEMU reference build.
OFF_MODE     = 0x200
OFF_MSTATUS  = 0x208
OFF_SSTATUS  = 0x210
OFF_MEPC     = 0x218
OFF_SEPC     = 0x220
OFF_MTVAL    = 0x228
OFF_STVAL    = 0x230
OFF_MTVEC    = 0x238
OFF_STVEC    = 0x240
OFF_MCAUSE   = 0x248
OFF_SCAUSE   = 0x250
OFF_MIDELEG  = 0x280
OFF_MEDELEG  = 0x288
OFF_PC       = 0x290

OFF_VR       = 0x320
VREG_BYTES   = 16

OFF_VSTART   = OFF_VR + 32 * VREG_BYTES
OFF_VXSAT    = OFF_VSTART + 8
OFF_VXRM     = OFF_VXSAT + 8
OFF_VCSR     = OFF_VXRM + 8
OFF_VL       = OFF_VCSR + 8
OFF_VTYPE    = OFF_VL + 8
OFF_VLENB    = OFF_VTYPE + 8

OFF_V8       = OFF_VR + 8  * VREG_BYTES
OFF_V9       = OFF_VR + 9  * VREG_BYTES
OFF_V10      = OFF_VR + 10 * VREG_BYTES

STATE_BUFFER_SIZE = 65536

def get_u64(buf, off):
    return struct.unpack_from("<Q", buf, off)[0]

def put_u64(buf, off, value):
    struct.pack_into(
        "<Q",
        buf,
        off,
        value & 0xffffffffffffffff
    )

def hex128(data):
    hi = int.from_bytes(data[8:16], "little")
    lo = int.from_bytes(data[0:8], "little")
    return "%016x_%016x" % (hi, lo)

print("===== LOAD REFERENCE MODEL =====", flush=True)

lib = ctypes.CDLL(SO)

init = lib.difftest_init
init.argtypes = []
init.restype = None

memcpy_fn = lib.difftest_memcpy
memcpy_fn.argtypes = [
    ctypes.c_uint64,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_bool,
]
memcpy_fn.restype = None

regcpy = lib.difftest_regcpy
regcpy.argtypes = [
    ctypes.c_void_p,
    ctypes.c_bool,
]
regcpy.restype = None

execute = lib.difftest_exec
execute.argtypes = [ctypes.c_uint64]
execute.restype = None

print("DLOPEN=PASS")

print()
print("===== INITIALIZE NEMU =====")

init()

print("DIFFTEST_INIT=PASS")

state_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(state_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

state = bytearray(state_array)

initial_pc = get_u64(state, OFF_PC)
initial_vtype = get_u64(state, OFF_VTYPE)
initial_vlenb = get_u64(state, OFF_VLENB)

print("INITIAL_PC=0x%016x" % initial_pc)
print("INITIAL_VTYPE=0x%016x" % initial_vtype)
print("INITIAL_VLENB=%d" % initial_vlenb)

if (
    initial_pc == 0x10000000
    and initial_vtype == 0x8000000000000000
    and initial_vlenb == 16
):
    print("STATE_LAYOUT_GATE=PASS")
else:
    print("STATE_LAYOUT_GATE=FAIL")
    raise RuntimeError("unexpected initial CPU/vector state")

print()
print("===== VERIFY CUSTOM INSTRUCTION =====")

opcode = VDOT_INSTR & 0x7f
vd = (VDOT_INSTR >> 7) & 0x1f
funct3 = (VDOT_INSTR >> 12) & 0x7
vs1 = (VDOT_INSTR >> 15) & 0x1f
vs2 = (VDOT_INSTR >> 20) & 0x1f
funct7 = (VDOT_INSTR >> 25) & 0x7f

print("INSTR=0x%08x" % VDOT_INSTR)
print("OPCODE=0x%02x" % opcode)
print("FUNCT7=%s" % format(funct7, "07b"))
print("FUNCT3=%s" % format(funct3, "03b"))
print("VD=v%d" % vd)
print("VS1=v%d" % vs1)
print("VS2=v%d" % vs2)

if (
    opcode == 0x0b
    and funct7 == 0x01
    and funct3 == 0
    and vd == 10
    and vs1 == 8
    and vs2 == 9
):
    print("ENCODING_GATE=PASS")
else:
    print("ENCODING_GATE=FAIL")
    raise RuntimeError("VDOT encoding mismatch")

print()
print("===== WRITE VDOT + TRAP SELF-LOOP =====")

vdot_bytes = struct.pack("<I", VDOT_INSTR)
vdot_buf = (ctypes.c_ubyte * 4).from_buffer_copy(vdot_bytes)

memcpy_fn(
    TEST_PC,
    ctypes.cast(vdot_buf, ctypes.c_void_p),
    4,
    DIFFTEST_TO_REF,
)

trap_bytes = struct.pack("<I", TRAP_LOOP_INSTR)
trap_buf = (ctypes.c_ubyte * 4).from_buffer_copy(trap_bytes)

memcpy_fn(
    TRAP_PC,
    ctypes.cast(trap_buf, ctypes.c_void_p),
    4,
    DIFFTEST_TO_REF,
)

read_vdot = (ctypes.c_ubyte * 4)()
read_trap = (ctypes.c_ubyte * 4)()

memcpy_fn(
    TEST_PC,
    ctypes.cast(read_vdot, ctypes.c_void_p),
    4,
    DIFFTEST_TO_DUT,
)

memcpy_fn(
    TRAP_PC,
    ctypes.cast(read_trap, ctypes.c_void_p),
    4,
    DIFFTEST_TO_DUT,
)

vdot_rb = struct.unpack("<I", bytes(read_vdot))[0]
trap_rb = struct.unpack("<I", bytes(read_trap))[0]

print("VDOT_MEMORY_READBACK=0x%08x" % vdot_rb)
print("TRAP_MEMORY_READBACK=0x%08x" % trap_rb)

if (
    vdot_rb == VDOT_INSTR
    and trap_rb == TRAP_LOOP_INSTR
):
    print("INSTRUCTION_MEMORY_GATE=PASS")
else:
    print("INSTRUCTION_MEMORY_GATE=FAIL")
    raise RuntimeError("instruction memory setup failed")

print()
print("===== PREPARE E16 ILLEGAL CASE =====")

# If the custom helper incorrectly accepts e16, these inputs would
# produce the normal +36 result. Therefore v10 is poisoned first.
v8 = bytes([
    1, 2, 3, 4, 5, 6, 7, 8,
    0, 0, 0, 0, 0, 0, 0, 0,
])

v9 = bytes([
    1, 1, 1, 1, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0,
])

v10_poison = bytes([0xA5] * 16)

state[OFF_V8:OFF_V8 + 16] = v8
state[OFF_V9:OFF_V9 + 16] = v9
state[OFF_V10:OFF_V10 + 16] = v10_poison

# M-mode.
put_u64(state, OFF_MODE, 3)

# Vector state enabled: mstatus.VS = Dirty.
put_u64(
    state,
    OFF_MSTATUS,
    get_u64(state, OFF_MSTATUS) | 0x600,
)

# Start at custom instruction.
put_u64(state, OFF_PC, TEST_PC)

# Force synchronous exception handling into M-mode at known mtvec.
put_u64(state, OFF_MTVEC, TRAP_PC)
put_u64(state, OFF_MEDELEG, 0)

# Clear old trap evidence.
put_u64(state, OFF_MEPC, 0)
put_u64(state, OFF_MCAUSE, 0)
put_u64(state, OFF_MTVAL, 0)

put_u64(state, OFF_VSTART, 0)
put_u64(state, OFF_VL, 16)

# VTYPE = e16, m1, ta, ma:
#
#   vill  = 0
#   vma   = 1
#   vta   = 1
#   vsew  = 001 -> e16
#   vlmul = 000 -> m1
#
# e8 was 0xC0; e16 is 0xC8.
put_u64(state, OFF_VTYPE, 0xC8)
put_u64(state, OFF_VLENB, 16)

print("PC_BEFORE=0x%016x" % get_u64(state, OFF_PC))
print("MTVEC_BEFORE=0x%016x" % get_u64(state, OFF_MTVEC))
print("MSTATUS_BEFORE=0x%016x" % get_u64(state, OFF_MSTATUS))
print("VSTART_BEFORE=%d" % get_u64(state, OFF_VSTART))
print("VL_BEFORE=%d" % get_u64(state, OFF_VL))
print("VTYPE_BEFORE=0x%016x" % get_u64(state, OFF_VTYPE))

print("V8=%s" % hex128(v8))
print("V9=%s" % hex128(v9))
print("V10_BEFORE=%s" % hex128(v10_poison))

prepared_array = (
    ctypes.c_ubyte * STATE_BUFFER_SIZE
).from_buffer_copy(state)

regcpy(
    ctypes.cast(prepared_array, ctypes.c_void_p),
    DIFFTEST_TO_REF,
)

print("REGCPY_TO_NEMU=PASS")

print()
print("===== PRE-EXEC ROUNDTRIP =====")

check_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(check_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

check = bytes(check_array)

print("ROUNDTRIP_PC=0x%016x" % get_u64(check, OFF_PC))
print("ROUNDTRIP_MTVEC=0x%016x" % get_u64(check, OFF_MTVEC))
print("ROUNDTRIP_MEDELEG=0x%016x" % get_u64(check, OFF_MEDELEG))
print("ROUNDTRIP_VTYPE=0x%016x" % get_u64(check, OFF_VTYPE))
print("ROUNDTRIP_V10=%s" % hex128(
    check[OFF_V10:OFF_V10 + 16]
))

if (
    get_u64(check, OFF_PC) == TEST_PC
    and get_u64(check, OFF_MTVEC) == TRAP_PC
    and get_u64(check, OFF_MEDELEG) == 0
    and get_u64(check, OFF_VTYPE) == 0xC8
    and check[OFF_V10:OFF_V10 + 16] == v10_poison
):
    print("PREEXEC_STATE_GATE=PASS")
else:
    print("PREEXEC_STATE_GATE=FAIL")
    raise RuntimeError("illegal-test state setup failed")

print()
print("===== EXECUTE NON-E8 VDOT =====")

execute(1)

print("DIFFTEST_EXEC_1=RETURNED")

print()
print("===== READ TRAP STATE =====")

after_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(after_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

after = bytes(after_array)

pc_after = get_u64(after, OFF_PC)
mepc_after = get_u64(after, OFF_MEPC)
mcause_after = get_u64(after, OFF_MCAUSE)
mtval_after = get_u64(after, OFF_MTVAL)
mtvec_after = get_u64(after, OFF_MTVEC)

vtype_after = get_u64(after, OFF_VTYPE)
vstart_after = get_u64(after, OFF_VSTART)

v8_after = after[OFF_V8:OFF_V8 + 16]
v9_after = after[OFF_V9:OFF_V9 + 16]
v10_after = after[OFF_V10:OFF_V10 + 16]

print("PC_AFTER=0x%016x" % pc_after)
print("MEPC_AFTER=0x%016x" % mepc_after)
print("MCAUSE_AFTER=0x%016x" % mcause_after)
print("MTVAL_AFTER=0x%016x" % mtval_after)
print("MTVEC_AFTER=0x%016x" % mtvec_after)

print("VTYPE_AFTER=0x%016x" % vtype_after)
print("VSTART_AFTER=%d" % vstart_after)

print("V8_AFTER=%s" % hex128(v8_after))
print("V9_AFTER=%s" % hex128(v9_after))
print("V10_AFTER=%s" % hex128(v10_after))

print()
print("===== ILLEGAL-INSTRUCTION CHECKS =====")

ok = True

if mcause_after == 2:
    print("ILLEGAL_MCAUSE_CHECK=PASS")
else:
    print("ILLEGAL_MCAUSE_CHECK=FAIL")
    ok = False

if mepc_after == TEST_PC:
    print("ILLEGAL_MEPC_CHECK=PASS")
else:
    print("ILLEGAL_MEPC_CHECK=FAIL")
    ok = False

if pc_after == TRAP_PC:
    print("ILLEGAL_TRAP_PC_CHECK=PASS")
else:
    print("ILLEGAL_TRAP_PC_CHECK=FAIL")
    ok = False

if v10_after == v10_poison:
    print("ILLEGAL_NO_VD_WRITE_CHECK=PASS")
else:
    print("ILLEGAL_NO_VD_WRITE_CHECK=FAIL")
    ok = False

if v8_after == v8:
    print("ILLEGAL_VS1_PRESERVED_CHECK=PASS")
else:
    print("ILLEGAL_VS1_PRESERVED_CHECK=FAIL")
    ok = False

if v9_after == v9:
    print("ILLEGAL_VS2_PRESERVED_CHECK=PASS")
else:
    print("ILLEGAL_VS2_PRESERVED_CHECK=FAIL")
    ok = False

if vtype_after == 0xC8:
    print("ILLEGAL_E16_VTYPE_CHECK=PASS")
else:
    print("ILLEGAL_E16_VTYPE_CHECK=FAIL")
    ok = False

if mtval_after == VDOT_INSTR:
    print("ILLEGAL_MTVAL_INSTR_CHECK=PASS")
else:
    print(
        "ILLEGAL_MTVAL_INSTR_CHECK=INFO "
        "(MTVAL policy is not used as a pass/fail gate)"
    )

if ok:
    print()
    print("VDOT_NON_E8_ILLEGAL_PASS")
else:
    print()
    print("VDOT_NON_E8_ILLEGAL_FAIL")
    raise RuntimeError(
        "CIE2026 non-e8 vdot did not trap as required"
    )
