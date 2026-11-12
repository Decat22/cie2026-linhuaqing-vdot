// CIE2026 vdot.vv datapath — Verilog equivalent of VIMacU.scala:85-107
// Faithful reproduction for synthesis: 8 signed INT8 multipliers + 3-level
// balanced adder tree (16->17->18->19 bit) + 32-bit narrowing + upper clear.
module vdot_unit (
    input  wire signed [127:0] vs1,
    input  wire signed [127:0] vs2,
    output wire        [127:0] vd
);
    // products[i] = vs1[8i+7:8i] * vs2[8i+7:8i], signed INT8 -> INT16
    wire signed [15:0] p0 = vs1[7:0]     * vs2[7:0];
    wire signed [15:0] p1 = vs1[15:8]    * vs2[15:8];
    wire signed [15:0] p2 = vs1[23:16]   * vs2[23:16];
    wire signed [15:0] p3 = vs1[31:24]   * vs2[31:24];
    wire signed [15:0] p4 = vs1[39:32]   * vs2[39:32];
    wire signed [15:0] p5 = vs1[47:40]   * vs2[47:40];
    wire signed [15:0] p6 = vs1[55:48]   * vs2[55:48];
    wire signed [15:0] p7 = vs1[63:56]   * vs2[63:56];

    // Level 1: 8 -> 4, width 16 -> 17
    wire signed [16:0] s0 = p0 + p1;
    wire signed [16:0] s1 = p2 + p3;
    wire signed [16:0] s2 = p4 + p5;
    wire signed [16:0] s3 = p6 + p7;

    // Level 2: 4 -> 2, width 17 -> 18
    wire signed [17:0] t0 = s0 + s1;
    wire signed [17:0] t1 = s2 + s3;

    // Level 3: 2 -> 1, width 18 -> 19
    wire signed [18:0] sum19 = t0 + t1;

    // Narrow to signed INT32, zero the upper 96 bits
    wire signed [31:0] sum32 = sum19;

    assign vd = {96'b0, sum32};
endmodule
