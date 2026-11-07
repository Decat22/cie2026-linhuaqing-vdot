CIE2026 Phase 2 - vdot.vv
XiangShan Kunminghu V2

建议检查顺序：

1. Phase2_VDOT_Design_and_Verification.txt

2. rtl/
   - baseline_to_official8.patch
   - VDotType.scala
   - VecDecoder.scala
   - VIMacU.scala

3. tests/source/
   - main_positive.c
   - main_negative.c
   - main_boundary.c
   - vdot.S
   - Makefile（若存在）

4. tests/results/
   - positive_SUMMARY.txt
   - negative_SUMMARY.txt
   - boundary_SUMMARY.txt
   - 对应完整运行日志
   - RVV vadd 回归日志

5. objdump/
   - vdot_official8_objdump.txt

6. wave/
   - 指令定位图
   - VIMac 输入图
   - VIMac 输出图
   - 波形定位与自动扫描文本

核心结果：

  Positive = 36
  Negative = -36
  Max Positive = 131072
  Max Negative = -130048
  Mixed = 127
  Upper-half ignored = 127

最终测试标志：

  VDOT_OFFICIAL_8TERM_ALL_PASS
  HIT GOOD TRAP

最终 XiangShan commit：

  86d7b4b98d0235b4a009dfd15b032bd558df33dc

============================================================
PHASE2_REPRODUCIBILITY_NOTE
Phase 2 可复现性与 DiffTest 阶段说明
============================================================

完整测试复现步骤见：
  REPRODUCE_PHASE2.md

重要说明：

1. Phase 2 自定义 vdot.vv 功能测试使用 --no-diff。

2. NEMU reference model 对 vdot.vv 的支持属于 Phase 3。

3. 因此 Phase 2 不声明自定义 vdot.vv 已通过 NEMU DiffTest。

4. 标准 RVV vadd.vv 回归测试使用正常 NEMU DiffTest，
   并已保存通过日志。

