# CIE2026 Phase3 VDOT Architectural Contract

## Frozen RTL source of truth

XiangShan Phase2 frozen commit:

    86d7b4b98d0235b4a009dfd15b032bd558df33dc

Phase3 NEMU must reproduce the behavior of this frozen RTL.
Phase3 must not redefine the instruction semantics.

## Encoding

Instruction name:

    vdot.vv

Encoding:

    bits[31:25] = 0000001
    bits[24:20] = vs2
    bits[19:15] = vs1
    bits[14:12] = 000
    bits[11:7]  = vd
    bits[6:0]   = 0001011

Opcode:

    custom-0 = 0x0b

Known Phase2 instance:

    vdot.vv v10, v8, v9
    instruction word = 0x0294050b

Therefore:

    vd  = v10
    vs1 = v8
    vs2 = v9

The encoding fixes bit 25 to 1, so this form is unmasked.

## Vector configuration

Frozen implementation target:

    VLEN = 128

Required SEW:

    SEW = 8

If:

    SEW != 8

the frozen RTL raises illegal instruction.

Phase2 conformance workloads use normal vector state with:

    vstart = 0

and load 16 bytes into each source register.

The arithmetic datapath itself has a FIXED term count of 8.
It must not change the term count according to vl.

Behavior outside the tested Phase2 vstart domain is not invented here;
Phase3 first reproduces the already frozen and demonstrated behavior.

## Arithmetic semantics

Only the LOW 8 bytes of each source vector register participate.

For i = 0..7:

    a_i = signed_int8(vs1.byte[i])
    b_i = signed_int8(vs2.byte[i])

Then:

    sum = a_0*b_0
        + a_1*b_1
        + a_2*b_2
        + a_3*b_3
        + a_4*b_4
        + a_5*b_5
        + a_6*b_6
        + a_7*b_7

Bytes 8..15 of both source registers are ignored.

Do NOT:

    - calculate 16 terms
    - loop to vl
    - treat source bytes as unsigned
    - preserve the old contents of vd[127:32]

## Destination

The mathematical sum is represented as signed INT32.

Architectural result:

    vd[31:0]   = uint32 bit pattern of signed INT32 sum
    vd[127:32] = 0

Examples:

    +36      -> 0x00000024
    -36      -> 0xffffffdc in vd[31:0]
    131072   -> 0x00020000
    -130048  -> signed INT32 bit pattern
    127      -> 0x0000007f

The upper 96 bits of vd are always cleared.

## Mandatory Phase3 semantic tests

    positive                 = 36
    negative                 = -36
    maximum positive         = 131072
    maximum negative         = -130048
    mixed                    = 127
    upper-half poison        = 127
    SEW != 8                 = illegal instruction

The upper-half poison case is mandatory because it proves that
source bytes [127:64] are ignored.

## Operand-index invariant

For instruction word:

    0x0294050b

the reference model must decode:

    vd  = 10
    vs1 = 8
    vs2 = 9

Final arithmetic equality alone is not sufficient evidence because
dot-product multiplication is commutative and can hide a vs1/vs2 swap.
