import ctypes
import struct
import sys

SO = sys.argv[1]

DIFFTEST_TO_DUT = False
DIFFTEST_TO_REF = True

TEST_PC = 0x80000000

# Phase1 verified instruction:
#   vadd.vv v3, v1, v2
VADD_INSTR = 0x021101D7

OFF_MODE    = 0x200
OFF_MSTATUS = 0x208
OFF_PC      = 0x290

OFF_VR      = 0x320
VREG_BYTES  = 16

OFF_VSTART  = OFF_VR + 32 * VREG_BYTES
OFF_VXSAT   = OFF_VSTART + 8
OFF_VXRM    = OFF_VXSAT + 8
OFF_VCSR    = OFF_VXRM + 8
OFF_VL      = OFF_VCSR + 8
OFF_VTYPE   = OFF_VL + 8
OFF_VLENB   = OFF_VTYPE + 8

OFF_V1 = OFF_VR + 1 * VREG_BYTES
OFF_V2 = OFF_VR + 2 * VREG_BYTES
OFF_V3 = OFF_VR + 3 * VREG_BYTES

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

def words32(data):
    return list(struct.unpack("<4I", data))

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

initial_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(initial_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

state = bytearray(initial_array)

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
    raise RuntimeError("unexpected initial state")

print()
print("===== VERIFY STANDARD OP-V ENCODING =====")

opcode = VADD_INSTR & 0x7f
vd = (VADD_INSTR >> 7) & 0x1f
funct3 = (VADD_INSTR >> 12) & 0x7
vs1_field = (VADD_INSTR >> 15) & 0x1f
vs2_field = (VADD_INSTR >> 20) & 0x1f
vm = (VADD_INSTR >> 25) & 0x1
funct6 = (VADD_INSTR >> 26) & 0x3f

print("INSTR=0x%08x" % VADD_INSTR)
print("OPCODE=0x%02x" % opcode)
print("FUNCT6=%s" % format(funct6, "06b"))
print("VM=%d" % vm)
print("FUNCT3=%s" % format(funct3, "03b"))
print("VD=v%d" % vd)
print("VS1_FIELD=v%d" % vs1_field)
print("VS2_FIELD=v%d" % vs2_field)

if (
    opcode == 0x57
    and funct6 == 0
    and vm == 1
    and funct3 == 0
    and vd == 3
    and vs1_field == 2
    and vs2_field == 1
):
    print("VADD_ENCODING_GATE=PASS")
else:
    print("VADD_ENCODING_GATE=FAIL")
    raise RuntimeError("unexpected vadd.vv encoding")

print()
print("===== WRITE ONE STANDARD VADD =====")

instr_bytes = struct.pack("<I", VADD_INSTR)
instr_buf = (ctypes.c_ubyte * 4).from_buffer_copy(instr_bytes)

memcpy_fn(
    TEST_PC,
    ctypes.cast(instr_buf, ctypes.c_void_p),
    4,
    DIFFTEST_TO_REF,
)

readback = (ctypes.c_ubyte * 4)()

memcpy_fn(
    TEST_PC,
    ctypes.cast(readback, ctypes.c_void_p),
    4,
    DIFFTEST_TO_DUT,
)

readback_word = struct.unpack("<I", bytes(readback))[0]

print("MEM_INSTR_WRITE=0x%08x" % VADD_INSTR)
print("MEM_INSTR_READ =0x%08x" % readback_word)

if readback_word == VADD_INSTR:
    print("INSTRUCTION_MEMORY_GATE=PASS")
else:
    print("INSTRUCTION_MEMORY_GATE=FAIL")
    raise RuntimeError("vadd instruction memory roundtrip failed")

print()
print("===== PREPARE E32 VECTOR STATE =====")

v1 = struct.pack("<4I", 1, 2, 3, 4)
v2 = struct.pack("<4I", 10, 20, 30, 40)

v3_poison = bytes([0xA5] * 16)
expected_v3 = struct.pack("<4I", 11, 22, 33, 44)

state[OFF_V1:OFF_V1 + 16] = v1
state[OFF_V2:OFF_V2 + 16] = v2
state[OFF_V3:OFF_V3 + 16] = v3_poison

# Enable vector state.
put_u64(
    state,
    OFF_MSTATUS,
    get_u64(state, OFF_MSTATUS) | 0x600,
)

put_u64(state, OFF_PC, TEST_PC)
put_u64(state, OFF_VSTART, 0)

# Four 32-bit elements in VLEN=128, LMUL=1.
put_u64(state, OFF_VL, 4)

# vtype = e32, m1, ta, ma:
# e8  = 0xC0
# e16 = 0xC8
# e32 = 0xD0
put_u64(state, OFF_VTYPE, 0xD0)
put_u64(state, OFF_VLENB, 16)

print("PC_BEFORE=0x%016x" % get_u64(state, OFF_PC))
print("MSTATUS_BEFORE=0x%016x" % get_u64(state, OFF_MSTATUS))
print("VSTART_BEFORE=%d" % get_u64(state, OFF_VSTART))
print("VL_BEFORE=%d" % get_u64(state, OFF_VL))
print("VTYPE_BEFORE=0x%016x" % get_u64(state, OFF_VTYPE))

print("V1_BEFORE=%s" % hex128(v1))
print("V2_BEFORE=%s" % hex128(v2))
print("V3_BEFORE=%s" % hex128(v3_poison))

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

check_pc = get_u64(check, OFF_PC)
check_vstart = get_u64(check, OFF_VSTART)
check_vl = get_u64(check, OFF_VL)
check_vtype = get_u64(check, OFF_VTYPE)

check_v1 = check[OFF_V1:OFF_V1 + 16]
check_v2 = check[OFF_V2:OFF_V2 + 16]
check_v3 = check[OFF_V3:OFF_V3 + 16]

print("ROUNDTRIP_PC=0x%016x" % check_pc)
print("ROUNDTRIP_VSTART=%d" % check_vstart)
print("ROUNDTRIP_VL=%d" % check_vl)
print("ROUNDTRIP_VTYPE=0x%016x" % check_vtype)

print("ROUNDTRIP_V1=%s" % hex128(check_v1))
print("ROUNDTRIP_V2=%s" % hex128(check_v2))
print("ROUNDTRIP_V3=%s" % hex128(check_v3))

if (
    check_pc == TEST_PC
    and check_vstart == 0
    and check_vl == 4
    and check_vtype == 0xD0
    and check_v1 == v1
    and check_v2 == v2
    and check_v3 == v3_poison
):
    print("PREEXEC_STATE_GATE=PASS")
else:
    print("PREEXEC_STATE_GATE=FAIL")
    raise RuntimeError("vadd pre-exec state mismatch")

print()
print("===== EXECUTE EXACTLY ONE STANDARD VADD.VV =====")

execute(1)

print("DIFFTEST_EXEC_1=RETURNED")

print()
print("===== READ POST-EXEC STATE =====")

after_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(after_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

after = bytes(after_array)

pc_after = get_u64(after, OFF_PC)
vstart_after = get_u64(after, OFF_VSTART)
vl_after = get_u64(after, OFF_VL)
vtype_after = get_u64(after, OFF_VTYPE)

v1_after = after[OFF_V1:OFF_V1 + 16]
v2_after = after[OFF_V2:OFF_V2 + 16]
v3_after = after[OFF_V3:OFF_V3 + 16]

print("PC_AFTER=0x%016x" % pc_after)
print("VSTART_AFTER=%d" % vstart_after)
print("VL_AFTER=%d" % vl_after)
print("VTYPE_AFTER=0x%016x" % vtype_after)

print("V1_AFTER=%s" % hex128(v1_after))
print("V2_AFTER=%s" % hex128(v2_after))
print("V3_AFTER=%s" % hex128(v3_after))

print("V1_WORDS=%s" % words32(v1_after))
print("V2_WORDS=%s" % words32(v2_after))
print("V3_WORDS=%s" % words32(v3_after))

print()
print("===== NORMAL RVV REGRESSION CHECKS =====")

ok = True

if pc_after == TEST_PC + 4:
    print("PC_ADVANCE_CHECK=PASS")
else:
    print("PC_ADVANCE_CHECK=FAIL")
    ok = False

if v1_after == v1:
    print("VADD_V1_PRESERVED_CHECK=PASS")
else:
    print("VADD_V1_PRESERVED_CHECK=FAIL")
    ok = False

if v2_after == v2:
    print("VADD_V2_PRESERVED_CHECK=PASS")
else:
    print("VADD_V2_PRESERVED_CHECK=FAIL")
    ok = False

if v3_after == expected_v3:
    print("VADD_RESULT_CHECK=PASS")
else:
    print("VADD_RESULT_CHECK=FAIL")
    print("EXPECTED_V3=%s" % hex128(expected_v3))
    ok = False

if words32(v3_after) == [11, 22, 33, 44]:
    print("VADD_WORDS_CHECK=PASS")
else:
    print("VADD_WORDS_CHECK=FAIL")
    ok = False

if vstart_after == 0:
    print("VADD_VSTART_ZERO_CHECK=PASS")
else:
    print("VADD_VSTART_ZERO_CHECK=FAIL")
    ok = False

if vl_after == 4 and vtype_after == 0xD0:
    print("VADD_VECTOR_CONFIG_CHECK=PASS")
else:
    print("VADD_VECTOR_CONFIG_CHECK=FAIL")
    ok = False

if ok:
    print()
    print("RVV_VADD_REGRESSION_PASS")
else:
    print()
    print("RVV_VADD_REGRESSION_FAIL")
    raise RuntimeError("standard RVV vadd regression failed")
