package xiangshan.backend.decode

import chisel3._
import chisel3.util.BitPat

/**
  * CIE2026 custom vdot.vv internal FuOp.
  *
  * VimacType uses:
  *   [8:7] pad
  *   [6]   vs2 signed
  *   [5]   vs1 signed
  *   [4]   old vd signed
  *   [3]   widen
  *   [2:0] opcode
  *
  * 01_110_0_000 keeps the low 7 bits identical to signed vmul,
  * while using the otherwise-unused upper pad bits to distinguish VDOT.
  */
object VDotType {
  val vdot: BitPat = BitPat("b011100000")

  def isVDot(fuOpType: UInt): Bool = {
    fuOpType === "b011100000".U(9.W)
  }
}
