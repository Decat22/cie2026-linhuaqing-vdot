import ctypes
import struct
import sys

SO = sys.argv[1]

DIFFTEST_TO_DUT = False
DIFFTEST_TO_REF = True

TEST_PC = 0x80000000
INSTR = 0x0294050B

# Confirmed from this exact NEMU build/state layout.
OFF_MODE    = 0x200
OFF_MSTATUS = 0x208
OFF_PC      = 0x290

# CONFIG_RVH is enabled in this reference model.
# After the RVH extension fields, the 32 x 128-bit vector registers begin here.
OFF_VR      = 0x320

VREG_BYTES  = 16

OFF_VSTART  = OFF_VR + 32 * VREG_BYTES
OFF_VXSAT   = OFF_VSTART + 8
OFF_VXRM    = OFF_VXSAT + 8
OFF_VCSR    = OFF_VXRM + 8
OFF_VL      = OFF_VCSR + 8
OFF_VTYPE   = OFF_VL + 8
OFF_VLENB   = OFF_VTYPE + 8

OFF_V8  = OFF_VR + 8  * VREG_BYTES
OFF_V9  = OFF_VR + 9  * VREG_BYTES
OFF_V10 = OFF_VR + 10 * VREG_BYTES

STATE_BUFFER_SIZE = 65536

def get_u64(buf, off):
    return struct.unpack_from("<Q", buf, off)[0]

def put_u64(buf, off, value):
    struct.pack_into("<Q", buf, off, value & 0xffffffffffffffff)

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

print("DLOPEN=PASS", flush=True)

print()
print("===== INITIALIZE NEMU =====", flush=True)

init()

print("DIFFTEST_INIT=PASS", flush=True)

print()
print("===== READ INITIAL ARCH STATE =====", flush=True)

state_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(state_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

state = bytearray(state_array)

initial_mode = get_u64(state, OFF_MODE)
initial_mstatus = get_u64(state, OFF_MSTATUS)
initial_pc = get_u64(state, OFF_PC)
initial_vtype = get_u64(state, OFF_VTYPE)
initial_vlenb = get_u64(state, OFF_VLENB)

print("INITIAL_MODE=0x%016x" % initial_mode)
print("INITIAL_MSTATUS=0x%016x" % initial_mstatus)
print("INITIAL_PC=0x%016x" % initial_pc)
print("INITIAL_VTYPE=0x%016x" % initial_vtype)
print("INITIAL_VLENB=0x%016x" % initial_vlenb)

# Two independent anchors prove the byte offsets before we modify anything.
if initial_pc != 0x10000000:
    print("STATE_LAYOUT_PC_GATE=FAIL")
    raise RuntimeError(
        "unexpected PC at expected CPU_state offset"
    )

if initial_vtype != 0x8000000000000000:
    print("STATE_LAYOUT_VTYPE_GATE=FAIL")
    raise RuntimeError(
        "unexpected initial vtype at expected CPU_state offset"
    )

print("STATE_LAYOUT_PC_GATE=PASS")
print("STATE_LAYOUT_VTYPE_GATE=PASS")
print("STATE_LAYOUT_GATE=PASS")

print()
print("===== VERIFY INSTRUCTION ENCODING =====")

opcode = INSTR & 0x7f
vd = (INSTR >> 7) & 0x1f
funct3 = (INSTR >> 12) & 0x7
vs1 = (INSTR >> 15) & 0x1f
vs2 = (INSTR >> 20) & 0x1f
funct7 = (INSTR >> 25) & 0x7f

print("INSTR=0x%08x" % INSTR)
print("OPCODE=0x%02x" % opcode)
print("FUNCT7=%07d" % int(format(funct7, "07b")))
print("FUNCT3=%03d" % int(format(funct3, "03b")))
print("VD=v%d" % vd)
print("VS1=v%d" % vs1)
print("VS2=v%d" % vs2)

if not (
    opcode == 0x0b
    and funct7 == 0x01
    and funct3 == 0
    and vd == 10
    and vs1 == 8
    and vs2 == 9
):
    print("ENCODING_GATE=FAIL")
    raise RuntimeError("custom vdot encoding mismatch")

print("ENCODING_GATE=PASS")

print()
print("===== WRITE ONE CUSTOM INSTRUCTION =====")

instr_bytes = struct.pack("<I", INSTR)
instr_buf = (ctypes.c_ubyte * 4).from_buffer_copy(instr_bytes)

memcpy_fn(
    TEST_PC,
    ctypes.cast(instr_buf, ctypes.c_void_p),
    4,
    DIFFTEST_TO_REF,
)

instr_readback = (ctypes.c_ubyte * 4)()

memcpy_fn(
    TEST_PC,
    ctypes.cast(instr_readback, ctypes.c_void_p),
    4,
    DIFFTEST_TO_DUT,
)

readback_word = struct.unpack(
    "<I",
    bytes(instr_readback),
)[0]

print("MEM_INSTR_WRITE=0x%08x" % INSTR)
print("MEM_INSTR_READ =0x%08x" % readback_word)

if readback_word != INSTR:
    print("INSTRUCTION_MEMORY_GATE=FAIL")
    raise RuntimeError("instruction memory roundtrip failed")

print("INSTRUCTION_MEMORY_GATE=PASS")

print()
print("===== PREPARE VECTOR STATE =====")

# Negative test:
# 1*(-1) + 2*(-1) + ... + 8*(-1) = -36.
v8 = bytes([
    1, 2, 3, 4, 5, 6, 7, 8,
    0, 0, 0, 0, 0, 0, 0, 0,
])

v9 = bytes([
    0xff, 0xff, 0xff, 0xff,
    0xff, 0xff, 0xff, 0xff,
    0, 0, 0, 0, 0, 0, 0, 0,
])

# Poison destination first. This proves the instruction really overwrites
# the whole architectural 128-bit destination and zeroes bits 127:32.
v10_poison = bytes([0xA5] * 16)

expected_v10 = (
    struct.pack("<i", -36) +
    bytes(12)
)

state[OFF_V8:OFF_V8 + 16] = v8
state[OFF_V9:OFF_V9 + 16] = v9
state[OFF_V10:OFF_V10 + 16] = v10_poison

# mstatus.VS = Dirty.
put_u64(
    state,
    OFF_MSTATUS,
    get_u64(state, OFF_MSTATUS) | 0x600,
)

# Execute directly from normal RAM instead of reset ROM.
put_u64(state, OFF_PC, TEST_PC)

# Frozen Phase2 test domain.
put_u64(state, OFF_VSTART, 0)
put_u64(state, OFF_VL, 16)

# vtype:
#   vlmul = 000 -> m1
#   vsew  = 000 -> e8
#   vta   = 1
#   vma   = 1
#   vill  = 0
put_u64(state, OFF_VTYPE, 0xC0)
put_u64(state, OFF_VLENB, 16)

print("V8 =%s" % hex128(v8))
print("V9 =%s" % hex128(v9))
print("V10_BEFORE=%s" % hex128(v10_poison))
print("PC_BEFORE=0x%016x" % get_u64(state, OFF_PC))
print("MSTATUS_BEFORE=0x%016x" % get_u64(state, OFF_MSTATUS))
print("VSTART_BEFORE=%d" % get_u64(state, OFF_VSTART))
print("VL_BEFORE=%d" % get_u64(state, OFF_VL))
print("VTYPE_BEFORE=0x%016x" % get_u64(state, OFF_VTYPE))
print("VLENB_BEFORE=%d" % get_u64(state, OFF_VLENB))

print()
print("===== COPY PREPARED STATE INTO NEMU =====")

prepared_array = (
    ctypes.c_ubyte * STATE_BUFFER_SIZE
).from_buffer_copy(state)

regcpy(
    ctypes.cast(prepared_array, ctypes.c_void_p),
    DIFFTEST_TO_REF,
)

print("REGCPY_TO_NEMU=PASS")

print()
print("===== ROUNDTRIP PRE-EXEC STATE =====")

check_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(check_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

check = bytes(check_array)

check_pc = get_u64(check, OFF_PC)
check_v8 = check[OFF_V8:OFF_V8 + 16]
check_v9 = check[OFF_V9:OFF_V9 + 16]
check_v10 = check[OFF_V10:OFF_V10 + 16]
check_vstart = get_u64(check, OFF_VSTART)
check_vl = get_u64(check, OFF_VL)
check_vtype = get_u64(check, OFF_VTYPE)

print("ROUNDTRIP_PC=0x%016x" % check_pc)
print("ROUNDTRIP_V8=%s" % hex128(check_v8))
print("ROUNDTRIP_V9=%s" % hex128(check_v9))
print("ROUNDTRIP_V10=%s" % hex128(check_v10))
print("ROUNDTRIP_VSTART=%d" % check_vstart)
print("ROUNDTRIP_VL=%d" % check_vl)
print("ROUNDTRIP_VTYPE=0x%016x" % check_vtype)

if (
    check_pc != TEST_PC
    or check_v8 != v8
    or check_v9 != v9
    or check_v10 != v10_poison
    or check_vstart != 0
    or check_vl != 16
    or check_vtype != 0xC0
):
    print("PREEXEC_STATE_GATE=FAIL")
    raise RuntimeError("prepared architectural state did not roundtrip")

print("PREEXEC_STATE_GATE=PASS")

print()
print("===== EXECUTE EXACTLY ONE RISC-V INSTRUCTION =====")

execute(1)

print("DIFFTEST_EXEC_1=RETURNED")

print()
print("===== READ POST-EXEC ARCH STATE =====")

after_array = (ctypes.c_ubyte * STATE_BUFFER_SIZE)()

regcpy(
    ctypes.cast(after_array, ctypes.c_void_p),
    DIFFTEST_TO_DUT,
)

after = bytes(after_array)

pc_after = get_u64(after, OFF_PC)
v8_after = after[OFF_V8:OFF_V8 + 16]
v9_after = after[OFF_V9:OFF_V9 + 16]
v10_after = after[OFF_V10:OFF_V10 + 16]

vstart_after = get_u64(after, OFF_VSTART)
vl_after = get_u64(after, OFF_VL)
vtype_after = get_u64(after, OFF_VTYPE)

result_signed = struct.unpack("<i", v10_after[:4])[0]
result_unsigned = struct.unpack("<I", v10_after[:4])[0]

print("PC_AFTER=0x%016x" % pc_after)

print("V8_AFTER =%s" % hex128(v8_after))
print("V9_AFTER =%s" % hex128(v9_after))
print("V10_AFTER=%s" % hex128(v10_after))

print("RESULT_SIGNED=%d" % result_signed)
print("RESULT_UNSIGNED=%d" % result_unsigned)

print("VSTART_AFTER=%d" % vstart_after)
print("VL_AFTER=%d" % vl_after)
print("VTYPE_AFTER=0x%016x" % vtype_after)

print()
print("===== NEGATIVE TEST CHECKS =====")

ok = True

if pc_after == TEST_PC + 4:
    print("PC_ADVANCE_CHECK=PASS")
else:
    print("PC_ADVANCE_CHECK=FAIL")
    ok = False

if v8_after == v8:
    print("VS1_PRESERVED_CHECK=PASS")
else:
    print("VS1_PRESERVED_CHECK=FAIL")
    ok = False

if v9_after == v9:
    print("VS2_PRESERVED_CHECK=PASS")
else:
    print("VS2_PRESERVED_CHECK=FAIL")
    ok = False

if v10_after == expected_v10:
    print("VD_FULL128_CHECK=PASS")
else:
    print("VD_FULL128_CHECK=FAIL")
    print("EXPECTED_V10=%s" % hex128(expected_v10))
    ok = False

if result_signed == -36:
    print("VDOT_RESULT_NEG36_CHECK=PASS")
else:
    print("VDOT_RESULT_NEG36_CHECK=FAIL")
    ok = False

if v10_after[4:] == bytes(12):
    print("VD_HIGH96_ZERO_CHECK=PASS")
else:
    print("VD_HIGH96_ZERO_CHECK=FAIL")
    ok = False

if vstart_after == 0:
    print("VSTART_ZERO_CHECK=PASS")
else:
    print("VSTART_ZERO_CHECK=FAIL")
    ok = False

if ok:
    print()
    print("VDOT_NEGATIVE_PASS")
else:
    print()
    print("VDOT_NEGATIVE_FAIL")
    raise RuntimeError("CIE2026 negative vdot test failed")
