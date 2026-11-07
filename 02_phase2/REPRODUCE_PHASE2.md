# Phase 2 测试复现说明

## 1. 文档目的

本文档用于说明如何根据最终提交目录中的源码，重新复现 Phase 2 的
`vdot.vv` 功能测试。

本文给出的命令依据以下内容整理：

- 最终提交目录中的测试源码；
- 当前 Makefile；
- 已验证的 nexus-am 构建接口；
- XiangShan emulator 的命令行接口；
- 已保存的 Phase 2 实验日志。

本文档是“当前可复现步骤”，不声称下面每一条命令都是最初实验时
终端历史记录的逐字符复制。

本项目 Phase 2 实现的 `vdot.vv` 行为为：

- 使用 `vs1` 的低 8 个 signed INT8 元素；
- 使用 `vs2` 的低 8 个 signed INT8 元素；
- 对这 8 对元素执行有符号乘加；
- 本实现使用 32 位有符号累加结果；
- 结果写入 `vd` 的低 32 位；
- 本实现将其余目标位清零。

---

## 2. Phase 2 的 DiffTest 策略

Phase 2 的自定义 `vdot.vv` 功能测试使用：

~~~bash
--no-diff
~~~

这是有意的阶段划分。

在 Phase 2 中，主要任务是验证 XiangShan RTL 中新增的自定义
`vdot.vv` 指令功能。

NEMU reference model 对 `vdot.vv` 的支持属于 Phase 3 的：

- NEMU 指令扩展；
- RTL 与 NEMU 协同仿真；
- DiffTest 一致性验证。

因此：

**Phase 2 的 VDOT 测试只声明 XiangShan RTL 功能验证通过，
不声明自定义 `vdot.vv` 已通过 NEMU DiffTest。**

标准 RVV `vadd.vv` 回归测试则使用正常 DiffTest。
已保存的 `rvv_vadd_regression.log` 中可以看到：

- NEMU reference model；
- `Difftest enabled`；
- 向量加法 PASS；
- good trap。

---

## 3. 环境变量

下面以本项目实际目录结构为例：

~~~bash
export AM_HOME="$HOME/xs-env/nexus-am"
export XS="$HOME/xs-env/XiangShan"
export EMU="$XS/build/emu"
~~~

其中：

- `AM_HOME`：nexus-am 路径；
- `XS`：XiangShan 源码路径；
- `EMU`：已经构建好的 XiangShan emulator。

Phase 2 已验证 emulator 支持：

~~~bash
-i IMAGE
--image=IMAGE
--no-diff
~~~

其中：

- `-i` / `--image`：指定运行的 workload image；
- `--no-diff`：关闭 reference-model differential testing。

---

## 4. Phase 2 测试源码结构

最终提交目录中的测试源码位于：

~~~text
02_phase2/tests/source/
├── Makefile
├── vdot.S
├── main.c
├── main_positive.c
├── main_negative.c
└── main_boundary.c
~~~

Makefile 中实际参与构建的是：

~~~make
NAME = cie2026-vdot
SRCS = main.c vdot.S
~~~

因此，要切换不同测试，需要先把相应测试源码复制为 `main.c`，
然后重新构建。

最终提交目录默认保留：

~~~text
main.c = main_boundary.c
~~~

即默认 `main.c` 为边界测试版本。

---

## 5. 正数测试

从最终提交目录：

~~~bash
cd CIE2026_FINAL_SUBMISSION

export AM_HOME="$HOME/xs-env/nexus-am"
export EMU="$HOME/xs-env/XiangShan/build/emu"

cd 02_phase2/tests/source

cp -f main_positive.c main.c
rm -rf build

make \
  ARCH=riscv64-xs \
  AM_HOME="$AM_HOME"

"$EMU" \
  --no-diff \
  -i build/cie2026-vdot-riscv64-xs.bin \
  | tee ../results/positive_reproduced.log
~~~

期望看到：

~~~text
Expected low-8 dot = 36
VDOT result = [36, 0, 0, 0]
VDOT_POSITIVE_PASS
HIT GOOD TRAP
~~~

原始实验结果保存在：

~~~text
tests/results/positive_run.log
tests/results/positive_SUMMARY.txt
~~~

---

## 6. 负数测试

~~~bash
cd CIE2026_FINAL_SUBMISSION

export AM_HOME="$HOME/xs-env/nexus-am"
export EMU="$HOME/xs-env/XiangShan/build/emu"

cd 02_phase2/tests/source

cp -f main_negative.c main.c
rm -rf build

make \
  ARCH=riscv64-xs \
  AM_HOME="$AM_HOME"

"$EMU" \
  --no-diff \
  -i build/cie2026-vdot-riscv64-xs.bin \
  | tee ../results/negative_reproduced.log
~~~

负数测试低 8 个输入为：

~~~text
a = [-1, -2, -3, -4, -5, -6, -7, -8]
b = [ 1,  1,  1,  1,  1,  1,  1,  1]
~~~

因此：

~~~text
(-1) + (-2) + (-3) + (-4)
+ (-5) + (-6) + (-7) + (-8)
= -36
~~~

期望看到：

~~~text
Expected low-8 dot = -36
VDOT result = [-36, 0, 0, 0]
VDOT_NEGATIVE_PASS
HIT GOOD TRAP
~~~

原始实验结果保存在：

~~~text
tests/results/negative_run.log
tests/results/negative_SUMMARY.txt
~~~

---

## 7. 边界测试

~~~bash
cd CIE2026_FINAL_SUBMISSION

export AM_HOME="$HOME/xs-env/nexus-am"
export EMU="$HOME/xs-env/XiangShan/build/emu"

cd 02_phase2/tests/source

cp -f main_boundary.c main.c
rm -rf build

make \
  ARCH=riscv64-xs \
  AM_HOME="$AM_HOME"

"$EMU" \
  --no-diff \
  -i build/cie2026-vdot-riscv64-xs.bin \
  | tee ../results/boundary_reproduced.log
~~~

边界测试包含以下检查：

~~~text
VDOT_BOUNDARY_MAX_POS_PASS
VDOT_BOUNDARY_MAX_NEG_PASS
VDOT_BOUNDARY_MIXED_PASS
VDOT_UPPER_HALF_IGNORED_PASS
VDOT_OFFICIAL_8TERM_ALL_PASS
HIT GOOD TRAP
~~~

对应数值为：

~~~text
最大正结果        = 131072
最大负结果        = -130048
混合输入结果      = 127
高半部分干扰测试  = 127
~~~

高半部分干扰测试用于确认：

**只有低 8 个 signed INT8 元素参与 VDOT 运算，
源操作数的其余字节不会改变结果。**

原始实验结果保存在：

~~~text
tests/results/boundary_run.log
tests/results/boundary_SUMMARY.txt
~~~

测试结束后，可恢复默认的 boundary `main.c`：

~~~bash
cp -f main_boundary.c main.c
~~~

---

## 8. 连续复现三个 VDOT 测试

下面的命令可以依次重新构建并运行：

- positive；
- negative；
- boundary。

新生成的日志使用 `_reproduced.log` 后缀，
不会覆盖最终提交中已经保存的历史实验日志。

~~~bash
cd CIE2026_FINAL_SUBMISSION

export AM_HOME="$HOME/xs-env/nexus-am"
export EMU="$HOME/xs-env/XiangShan/build/emu"

cd 02_phase2/tests/source

for CASE in positive negative boundary
do
  echo "===== REPRODUCE $CASE ====="

  cp -f "main_${CASE}.c" main.c
  rm -rf build

  make \
    ARCH=riscv64-xs \
    AM_HOME="$AM_HOME" || break

  "$EMU" \
    --no-diff \
    -i build/cie2026-vdot-riscv64-xs.bin \
    | tee "../results/${CASE}_reproduced.log"
done

cp -f main_boundary.c main.c
~~~

---

## 9. 标准 RVV vadd.vv 回归测试

Phase 2 还保存了标准 RVV `vadd.vv` 回归测试，用于确认新增
VDOT RTL 修改没有破坏原有标准向量指令。

该测试与自定义 VDOT 不同：

**不要添加 `--no-diff`。**

从最终提交目录执行：

~~~bash
cd CIE2026_FINAL_SUBMISSION

export AM_HOME="$HOME/xs-env/nexus-am"
export EMU="$HOME/xs-env/XiangShan/build/emu"

VADD_DIR="$PWD/01_phase1/source/vadd"

cd "$VADD_DIR"
rm -rf build

make \
  ARCH=riscv64-xs \
  AM_HOME="$AM_HOME"

VADD_BIN="$(
  find "$VADD_DIR/build" \
    -maxdepth 1 \
    -type f \
    -name '*-riscv64-xs.bin' \
    -print \
    | head -n 1
)"

echo "VADD_BIN=$VADD_BIN"

"$EMU" \
  -i "$VADD_BIN" \
  | tee "$VADD_DIR/../../../02_phase2/tests/results/rvv_vadd_regression_reproduced.log"
~~~

正常情况下应看到：

~~~text
The reference model is ...
Difftest enabled.
...
VECTOR_ADD_PASS
...
HIT GOOD TRAP
~~~

最终提交中已经保存的原始回归日志为：

~~~text
02_phase2/tests/results/rvv_vadd_regression.log
~~~

---

## 10. VDOT 波形复现

最终提交中已经包含本次比赛使用的正式 VDOT 波形证据。

如需自行重新验证波形，可以先准备 boundary workload：

~~~bash
cd CIE2026_FINAL_SUBMISSION

export AM_HOME="$HOME/xs-env/nexus-am"
export EMU="$HOME/xs-env/XiangShan/build/emu"

cd 02_phase2/tests/source

cp -f main_boundary.c main.c
rm -rf build

make \
  ARCH=riscv64-xs \
  AM_HOME="$AM_HOME"
~~~

如果当前 emulator 是带 FST waveform 支持构建的版本，可执行：

~~~bash
"$EMU" \
  --no-diff \
  --dump-wave \
  --wave-path=vdot_official8_reproduced.fst \
  -b 10000 \
  -e 12000 \
  -i build/cie2026-vdot-riscv64-xs.bin
~~~

本项目已经保存的正式波形证据包括：

~~~text
wave/vdot_official8_instruction_23778.png
wave/vdot_official8_vimac_input_23844.png
wave/vdot_official8_vimac_output_23848.png
wave/vdot_official8_wave_evidence.txt
wave/vdot_official8_signal_scan.txt
~~~

其中：

- `23778 ps` 截图用于定位 `vdot.vv` 指令；
- `23844 ps` 为 VIMacU 输入有效的重要证据；
- `23848 ps` 为 VIMacU 输出有效及结果的重要证据。

正式比赛材料应以已经保存的证据为准。
重新生成的波形只用于独立复现与检查。

---

## 11. 历史证据与复现结果的区别

最终提交包中的：

~~~text
tests/results/positive_run.log
tests/results/negative_run.log
tests/results/boundary_run.log
tests/results/rvv_vadd_regression.log
~~~

属于已经完成实验时保存的历史证据。

如果根据本文重新执行测试，新产生的：

~~~text
positive_reproduced.log
negative_reproduced.log
boundary_reproduced.log
rvv_vadd_regression_reproduced.log
~~~

属于新的复现实验结果。

不要用新生成的日志覆盖提交包中的历史实验日志。
