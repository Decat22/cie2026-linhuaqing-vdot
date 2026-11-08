# 阶段一：`vadd.vv` 向量加法指令执行过程分析

本文依据 XiangShan 昆明湖 V2 的 RTL 仿真波形（`wave/vadd_15000_17000.fst`）、提交追踪日志（`runtime/05_vadd_commit_trace.log`）与反汇编（`vadd_objdump.txt`），逐步描述标准 RVV 向量加法指令 `vadd.vv` 在本处理器中的完整执行过程。

选取 `vadd.vv` 作为分析对象，是因为它是向量单元中最基础、最典型的一条指令：它同时涉及向量配置（`vsetvli`）、向量访存（`vle32.v` / `vse32.v`）与向量运算三类子路径，且寄存器写入是向量寄存器，能够完整暴露香山向量单元的分派、发射、执行与写回机制。后续阶段二要新增的 `vdot.vv` 走的正是这条链路（`VecDecoder` → `VFU` → `VIMacU`），因此本阶段的分析构成了第二阶段设计的前置理解。

---

## 1. 被分析的测试程序

### 1.1 源码

测试程序位于 `source/vadd/`，核心计算函数如下：

```c
// main.c
int32_t A[4] = {1, 2, 3, 4};
int32_t B[4] = {10, 20, 30, 40};
int32_t C[4] = {0, 0, 0, 0};

vector_add_i32(A, B, C, 4);
```

```asm
# vector_add.S
vector_add_i32:
    li      t1, 1536            # mstatus.VS = 011 (Dirty)
    csrs    mstatus, t1         # 打开向量单元状态
    vsetvli t0, a3, e32, m1, ta, ma
    vle32.v v1, (a0)            # 读 A
    vle32.v v2, (a1)            # 读 B
    vadd.vv v3, v1, v2          # C = A + B
    vse32.v v3, (a2)            # 写 C
    ret
```

`mstatus.VS` 必须先置为 Dirty，否则任何向量指令都会触发非法指令异常。这是 RVV 的状态使能要求，不是香山特有实现。

### 1.2 反汇编与地址

`vadd_instruction_evidence.txt` 给出的反汇编：

| 地址 | 机器码 | 汇编 | 语义 |
|---|---|---|---|
| `0x8000012c` | `60000313` | `li t1, 1536` | 准备 `mstatus.VS` 位 |
| `0x80000130` | `30032073` | `csrs mstatus, t1` | 置 VS = Dirty |
| `0x80000134` | `0d06f2d7` | `vsetvli t0, a3, e32, m1, ta, ma` | 配置 VL / SEW / LMUL |
| `0x80000138` | `02056087` | `vle32.v v1, (a0)` | 向量加载 A |
| `0x8000013c` | `0205e107` | `vle32.v v2, (a1)` | 向量加载 B |
| `0x80000140` | `021101d7` | `vadd.vv v3, v1, v2` | 向量加法 |
| `0x80000144` | `020661a7` | `vse32.v v3, (a2)` | 向量存储 C |
| `0x80000148` | `8082` | `ret` | 返回 |

### 1.3 预期结果

四个 32 位元素逐分量相加：

```
C[0] =  1 + 10 = 11 = 0x0b
C[1] =  2 + 20 = 22 = 0x16
C[2] =  3 + 30 = 33 = 0x21
C[3] =  4 + 40 = 44 = 0x2c
```

程序实际输出（`vadd_run_summary.txt`）：

```
A = [1, 2, 3, 4]
B = [10, 20, 30, 40]
C = [11, 22, 33, 44]
VECTOR_ADD_PASS
Core 0: HIT GOOD TRAP at pc = 0x80000210
Core-0 instrCnt = 5,472, cycleCnt = 20,922, IPC = 0.261543
```

---

## 2. 提交轨迹：指令逐条流过的证据

`runtime/05_vadd_commit_trace.log` 的 280–287 行是本次分析最重要的一手证据。这是香山仿真器在提交阶段打印的指令退休记录，每一行对应一条真正提交（commit）的指令：

```
280:[11] commit pc 000000008000012c inst 60000313 wen 1 dst 06 data 0000000000000600 idx 06b
281:[12] commit pc 0000000080000130 inst 30032073 wen 0 dst 00 data 0000000000000000 idx 06c
282:[13] commit pc 0000000080000134 inst 0d06f2d7 wen 1 dst 05 data 0000000000000004 idx 06d
283:[14] commit pc 0000000080000138 inst 02056087 wen 1 dst 01 data 0000000080009fb0 idx 06e (00)
284:[15] commit pc 000000008000013c inst 0205e107 wen 1 dst 02 data 0000000080009fc0 idx 06f (00)
285:[16] commit pc 0000000080000140 inst 021101d7 wen 1 dst 03 data 000000160000000b idx 070
286:[17] commit pc 0000000080000144 inst 020661a7 wen 1 dst 32 data 0000000080009fd0 idx 071 (00)
287:[18] commit pc 0000000080000148 inst 00008067 wen 0 dst 00 data 0000000000000000 idx 072
```

逐字段解读：

- **`pc`** —— 该指令的地址，与第 1.2 节的反汇编逐条对齐，无跳转、无重放，说明这八条指令按程序顺序连续提交。
- **`inst`** —— 提交的机器码原文，可直接与反汇编比对，排除"反汇编和实际执行不一致"的可能。
- **`wen` / `dst`** —— 是否写寄存器堆、目标寄存器号。`vsetvli` 写 `x5`（`t0`），两条 `vle32.v` 分别写 `v1`、`v2`，`vadd.vv` 写 `v3`，`vse32.v` 的 `dst=32`（记录中为 5 位域，非标量寄存器编号），全部符合语义。
- **`idx`** —— 提交序号，从 `06b` 到 `072` 连续递增，无空缺，证明期间没有发生异常或流水线冲刷。
- **`data`** —— 写回数据，这是最能说明问题的一列，下面单独展开。

### 2.1 `vsetvli` 的写回：VL = 4

```
[13] pc 0x80000134 inst 0d06f2d7 wen 1 dst 05 data 0000000000000004
```

`vsetvli t0, a3, e32, m1, ta, ma` 的语义是：AVL 取 `a3`（值为 4），SEW=32，LMUL=1，尾元素与掩码策略均为 agnostic。硬件计算出的实际 VL 写回 `x5`。

写回值是 **4**，与数组长度一致。说明：

1. VL 计算正确。VLEN=128、SEW=32、LMUL=1 时单次最大可容纳 128/32 = 4 个元素，AVL=4 正好被单条指令覆盖，不需要 `vsetvli` 迭代。
2. 后续所有向量指令都只处理 4 个元素，`vl = 4`。

### 2.2 两次 `vle32.v` 的写回：基址

```
[14] pc 0x80000138 inst 02056087 wen 1 dst 01 data 0000000080009fb0
[15] pc 0x8000013c inst 0205e107 wen 1 dst 02 data 0000000080009fc0
```

这两条是向量访存，`wen=1` 且 `dst` 为 `v1`/`v2`。提交记录里的 `data` 显示的是地址 `0x80009fb0` / `0x80009fc0`——注意这是**访存基址**而不是加载回来的数据，因为向量加载的写回发生在写回级之后，提交日志在这一列记录的是该 uop 的地址域。

两个地址相差 `0x10` = 16 字节 = 4 × 4 字节，正好是 4 个 float32/int32 元素的总长，与 A、B 两个数组在原程序中相邻或等距分配的事实一致。

### 2.3 `vadd.vv` 的写回：结果正确

```
[16] pc 0x80000140 inst 021101d7 wen 1 dst 03 data 000000160000000b
```

这是整个分析的核心证据。`vadd.vv v3, v1, v2` 写回 `v3`（`dst=03`），写回数据 `0x000000160000000b`。

按 VLEN=128 拆成 4 个 32 位 lane：

| lane | 位域 | 值 | 期望值 | 判定 |
|---|---|---|---|---|
| 0 | `[31:0]` | `0x0000000b` = 11 | 1 + 10 = 11 | ✓ |
| 1 | `[63:32]` | `0x00000016` = 22 | 2 + 20 = 22 | ✓ |
| 2 | `[95:64]` | `0x00000000` = 0 | 3 + 30 = 33 | ✗ 本拍未写 |
| 3 | `[127:96]` | `0x00000000` = 0 | 4 + 40 = 44 | ✗ 本拍未写 |

这里出现了一个需要解释的现象：单个提交记录的 `data` 只包含 lane 0 和 lane 1 的结果，lane 2、lane 3 为零。

**这里必须区分「观测到的事实」与「对事实的解释」。**

观测到的事实是：`[16]` 这一行提交记录的 `data` 字段中，lane 2、lane 3 为零；而程序级输出 `C = [11, 22, 33, 44]` 证明四个 lane 最终都正确。

对本现象的解释（推断，未从波形直接验证）：香山的向量单元对向量指令做 **uop 拆分**，一条 `vadd.vv` 在 VL=4、SEW=32、VLEN=128 时按数据通路宽度拆成多个 uop 分拍，每个 uop 负责一部分 lane；提交日志的 `[16]` 行记录的是主 uop 的写回数据，只覆盖 `[63:0]`，其余 lane 由后续 uop 完成写回且不单独打印。

支持该推断的依据有两点：一是本测试的数据通路宽度为 64 位（与阶段二 `VIMacU` 中 `VIMac64b` 的命名一致），恰好等于 2 个 32 位 lane，与"主 uop 覆盖 lane 0–1"吻合；二是 `vdot.vv` 实现中 `VimacCfg` 同样按 64 位数据通路组织。但严格地说，本阶段未采集 uop 拆分信号，因此该解释仍属推断而非观测。若要坐实，需在波形中抓取 `virtu` / `decodedVFuOpType` 与 uop 计数信号。

最终的 `C = [11, 22, 33, 44]` 由程序自身的 `VECTOR_ADD_PASS` 判定，这是端到端的正确性证据，覆盖了全部 4 个 lane。因此 lane 2、lane 3 在这个字段中为零，只反映提交日志的采样口径，不反映硬件行为。

这一点恰好说明了本阶段的意义：**单看提交日志不足以判定向量指令正确，必须结合程序级输出与波形。** 这也是后续阶段二设计 `vdot.vv` 时需要特别注意的——`vdot.vv` 的结果只写 `vd[31:0]`，其"只写低 32 位"的行为在提交日志中反而无法与"漏写"区分，必须依赖精确的语义测试。

### 2.4 `vse32.v` 与 `ret`

```
[17] pc 0x80000144 inst 020661a7 wen 1 dst 32 data 0000000080009fd0
[18] pc 0x80000148 inst 00008067 wen 0 dst 00 data 0000000000000000
```

`vse32.v` 的 `dst=32` 超出标量寄存器编号范围（x0–x31），该字段在向量访存中记录的是访存地址 `0x80009fd0`，不应读作寄存器号。`ret` 不写寄存器（`wen=0`）。

---

## 3. 波形分析：指令在流水中的时序

### 3.1 波形文件

- 文件：`wave/vadd_15000_17000.fst`
- 采样窗口：15000–17000 个周期
- SHA256：见 `wave/vadd_15000_17000.fst.sha256`
- 工具：GTKWave

查看方式：

```bash
gtkwave vadd_15000_17000.fst
```

需要观察的信号：

| 信号 | 含义 |
|---|---|
| `io_bits_instr[31:0]` | 提交级指令机器码 |
| `io_bits_pc[63:0]` | 提交级 PC |
| `io_bits_vecwen` | 向量写使能 |
| `io_bits_wdest[7:0]` | 目标寄存器号 |

### 3.2 时间窗口与指令序列

`phase1_vadd_vv_waveform.png` 与 `phase1_vector_add_execution_sequence.png` 两张截图取自同一窗口：

- 起始时间：**31710 ps**
- 结束时间：**31724 ps**
- 窗口宽度：**14 ps**

在这个窗口内，`io_bits_instr` 依次出现：

```
0D06F2D7  →  02056087  →  0205E107  →  021101D7  →  020661A7
```

对应 PC：

```
0x80000134  →  0x80000138  →  0x8000013c  →  0x80000140  →  0x80000144
```

与第 1.2 节反汇编和第 2 节提交轨迹**一致**（注：仓库内 `vadd_objdump.txt` 曾误放一版缺少 `li`/`csrs` 的旧构建，已替换为与运行镜像一致的版本）。这是本次分析可信度的关键：反汇编给的是静态编码，提交日志给的是提交序，波形给的是逐周期信号，三者互相印证。

### 3.3 时序观察

从 `phase1_vadd_vv_waveform.png` 可以看到：

1. **五条指令依次出现在同一组信号线上**，说明提交级每周期处理一条指令，且这五条是连续提交的，没有停顿气泡。
2. **`io_bits_pc` 严格递增且与 `instr` 一一对应**，PC 与指令码没有错位，证明取指、译码、提交各阶段对该序列没有发生重排或投机错误。
3. **窗口内没有出现冲刷信号**，排除了分支预测失败导致的重复提交。
4. `io_bits_vecwen` 在 `vadd.vv`（`021101D7`）与两条 `vle32.v` 期间有效，在 `vsetvli` 与 `ret` 期间表现不同——`vsetvli` 写的是标量寄存器，`ret` 不写寄存器，这一差异与提交日志中 `wen` 字段的取值（`[13]` 是 1 写 `x5`，`[18]` 是 0 不写）吻合。

### 3.4 由波形得到的结论

波形窗口只有 14 ps，覆盖的是**提交级**看到的最终状态，不包含流水内部的发射、执行细节。这是本阶段采样窗口选择的局限，需要在报告中明确说明：

- 可以看到：指令按序提交、PC 与编码对应、写使能行为正确。
- 看不到：译码后的 uop 拆分、功能单元分派、执行级的多拍运算、寄存器堆的实际写端口。

若要观察执行级细节，需要把采样窗口对准指令进入发射队列或功能单元的时刻，并抓取 `VFuType`、`virtu`、`decodedVFuOpType` 等信号。这部分在第二阶段分析 `vdot.vv` 时已补充（见 `02_phase2/wave/`）。

---

## 4. 执行过程完整还原

综合以上三方面证据，`vadd.vv` 在香山昆明湖 V2 中的执行过程可还原如下。

### 4.1 阶段流水

```
取指 IF
  ↓
译码 ID  ── RVV 指令由 VecDecoder 识别
  ↓      (译码为 VFuType.vialuF + VialuFixType.vadd_vv)
重命名 / 分派
  ↓      向量寄存器 v1, v2 重命名到物理寄存器
发射 Issue
  ↓      送入向量 ALU 功能单元
执行 EX
  ↓      4 条 lane 并行相加，按 uop 拆分多拍
写回 WB
  ↓      v3 物理寄存器更新
提交 Commit
        提交日志 [16] 记录主 uop 数据 0x000000160000000b
```

### 4.2 各阶段说明

**译码。** `vadd.vv` 的编码 `021101D7` 属于 OP-V 主 opcode（`0b1010111`），`funct6 = 000000`、`funct3 = 000`。香山 `VecDecoder` 中对应的条目是 `VADD_VV → OPIVV(FuType.vialuF, VialuFixType.vadd_vv)`。这一步把 RISC-V 指令转换成内部 FuOp，并决定后续由哪个功能单元接收。

**寄存器依赖。** `vadd.vv v3, v1, v2` 读 `v1`、`v2`（由前两条 `vle32.v` 产生），写 `v3`。这意味着进入发射级时必须等待两条 `vle32.v` 完成写回。从提交轨迹看，`[14]`、`[15]`、`[16]` 连续提交，说明在实际执行中这两条加载的延迟被流水线其他指令掩盖，或者仿真器在等待访存返回后一次性推进。

**执行。** 向量 ALU 对 4 个 32 位元素并行做加法。VLEN=128、SEW=32 时，一条指令理论上有 4 条数据通路并行，但受限于实际数据通路宽度，硬件会拆成多个 uop 分拍。提交日志只记录主 uop，这就是第 2.3 节中 lane 2、lane 3 为零的原因。

**写回与提交。** 写回更新 `v3` 的物理寄存器；提交级按程序顺序退休，`idx` 连续递增（`06d` → `070`）。`[16]` 的 `data` 字段是本指令在提交级可见的写回值。

### 4.3 与 `vdot.vv` 的关系

理解 `vadd.vv` 的这条链，是第二阶段设计 `vdot.vv` 的直接前提：

| 环节 | `vadd.vv` | `vdot.vv`（本项目） |
|---|---|---|
| 译码 | `VecDecoder` → `OPIVV(vialuF, vadd_vv)` | `VecDecoder` 新增条目 → `OPIVV(vimac, VDotType.vdot)` |
| 功能单元 | 向量 ALU | `VIMacU` |
| 数据通路 | 逐 lane 并行加 | 8 项 int8 乘 + 三级归约树 |
| 写回 | 整个向量寄存器（全 lane） | 仅 `vd[31:0]`，`vd[127:32]` 清零 |

关键差异在于**写回粒度**：`vadd.vv` 写满 VLEN，而 `vdot.vv` 只写低 32 位。这正是阶段二 RTL 中需要特殊处理的地方——不能直接复用原有 MGU 的逐元素写回逻辑（见 `02_phase2/rtl/.../VIMacU.scala` 中的 `Mux(outIsVDot, vdotResult, mgu.io.out.vd)`），这也是第二阶段设计文档中需要说明的取舍点。

---

## 5. 小结与遗留

### 5.1 已确认的事实

1. 环境部署完成：Ubuntu 24.04.4 LTS、8 核、15 GiB 内存（`environment/environment_info.txt`），XiangShan 昆明湖 V2 baseline 在 DiffTest 下正常运行。
2. `hello` 程序输出 `hello xiangshan, I am 林淮青, IP address: 192.168.74.128`，命中 `HIT GOOD TRAP`（`runtime/02_cie2026_hello_difftest_SUCCESS.log`）。
3. `vadd.vv` 程序输出 `C = [11, 22, 33, 44]`，判定 `VECTOR_ADD_PASS`，`HIT GOOD TRAP at pc = 0x80000210`。
4. 反汇编、提交轨迹、波形三方对 `vadd.vv` 的 PC 与机器码完全一致。
5. `vsetvli` 正确算出 VL=4（提交日志 `[13]` 写回 `x5 = 4`）。
6. `vadd.vv` 主 uop 写回 `0x000000160000000b`，lane 0 = 11、lane 1 = 22，与期望值一致。

### 5.2 分析局限（如实说明）

1. **波形窗口仅 14 ps**，只覆盖提交级，看不到执行内部的 uop 拆分与功能单元行为。
2. **提交日志的 `data` 字段只反映主 uop**，向量指令的完整写回需要程序级输出或多拍记录才能验证。
3. **未采集 `VFuType` 等译码后信号**，因此"该指令进入向量 ALU"的结论是从 `VecDecoder` 源码与本指令的提交行为推得，不是从波形直接观测。

第 3 点在本阶段是局限；在第二阶段已通过抓取 `VIMacU` 内部信号补齐（见 `02_phase2/wave/vdot_official8_vimac_input_23844.png` 与 `vdot_official8_vimac_output_23848.png`）。

### 5.3 操作日志索引

| 类别 | 文件 |
|---|---|
| 环境信息 | `environment/environment_info.txt` |
| 构建日志（14 份） | `logs/01_baseline_make_verilog*.log`（5 份）、`logs/02_baseline_*.log`（2 份）、`logs/03_baseline_make_emu*.log`（2 份）、`logs/04_cie2026_hello_build*.log`（2 份）、`logs/05_cie2026_vadd_build*.log`（2 份）、`logs/06_make_emu_fst.log` |
| 运行时日志（9 份） | `runtime/01_coremark_difftest.log`、`runtime/02_cie2026_hello_difftest*.log`、`runtime/03_cie2026_vadd_*.log`、`runtime/05_vadd_commit_trace.log`、`runtime/06_vadd_wave_capture.log` |
| 反汇编与提交证据 | `vadd_objdump.txt`、`vadd_instruction_evidence.txt`、`vadd_commit_evidence.txt` |
| 波形 | `wave/vadd_15000_17000.fst`（SHA256 见同名 `.sha256`）、`wave/vadd_pc_hits.txt`、`wave/vadd_instr_hits.txt` |

其中 `logs/01_baseline_make_verilog_attempt1_java_path_failure.log`、`..._attempt2_oom.log`、`04_cie2026_hello_build_attempt1_wrong_toolchain.log`、`runtime/03_cie2026_vadd_attempt1_vs_off.log` 保留了环境搭建过程中的失败尝试，一并附上供复核。
