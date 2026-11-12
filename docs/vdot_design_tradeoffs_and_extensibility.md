# vdot.vv 设计取舍与扩展路径分析

本文补充说明 `vdot.vv` 实现中的微架构取舍，并给出向其他向量指令与更高 SEW/VLEN 扩展的可行路径。本文不复述功能语义（见《设计文档》），只讨论**为什么这样设计**与**还能怎么扩**。

---

## 1. 为什么采用平衡归约树，而不是串行累加链

### 1.1 两种结构

8 项 int8 乘积求和，最直观的写法是串行累加：

```scala
// 串行链（未采用）
var acc = 0
for (i <- 0 until 8) acc = acc + products(i)
```

本项目采用三级平衡归约树（`VIMacU.scala:85-99`）：

```scala
private val vdotProducts = (0 until 8).map { i =>
  val a = vs1(8 * i + 7, 8 * i).asSInt
  val b = vs2(8 * i + 7, 8 * i).asSInt
  a * b
}

private val vdotSumL1 = (0 until 4).map { i =>
  vdotProducts(2 * i) +& vdotProducts(2 * i + 1)
}
private val vdotSumL2 = (0 until 2).map { i =>
  vdotSumL1(2 * i) +& vdotSumL1(2 * i + 1)
}
private val vdotSum = vdotSumL2(0) +& vdotSumL2(1)
```

### 1.2 关键差异：加法器级数

| 结构 | 加法器级数 | 单级最大扇入 |
|---|---|---|
| 串行链 | 7 级 | 2（但有 7 级串行依赖） |
| 平衡树 | **3 级** | 2 |

这才是 `vdot` 相对软件实现能拿到加速的结构性原因：**组合逻辑深度从 7 级降到 3 级**。串行链虽然加法器数量相同（都是 7 个），但关键路径长了一倍多，会直接压低功能单元的高频能力。

需要说明的是：本项目的 `VimacCfg` 采用 `CertainLatency(2)`，功能单元整体延迟由流水线配置决定（见 `VIMacU.scala:109` 的注释），因此**树形结构带来的组合深度收益在 2 级流水下部分被吸收**。这解释了为什么阶段三实测的"compute speedup 4.77x"主要来自**指令数压缩**（5 条 RVV 指令 → 1 条 vdot），而不是功能单元延迟本身。这个区分在阶段三的 `STEP7E_PHASE3_PERFORMANCE_FINAL_INTERPRETATION.txt` 中已明确标注。

### 1.3 位宽增长设计

树的每一级用 `+&`（扩展加法），位宽逐级增长：

```
乘积：int8 × int8 → 16 位（有符号）
L1：  16 + 16      → 17 位
L2：  17 + 17      → 18 位
L3：  18 + 18      → 19 位
```

19 位足以容纳极值：`8 × (-128) × (-128) = 131072`，需要 18 位（`2^17 = 131072`，正值需 18 位含符号位），取 19 位留有 1 位余量。最终收窄到 32 位（`VIMacU.scala:101-102`）以满足架构定义。

**这个位宽推演是设计文档必须写清楚的部分**：如果直接在 16 位上累加，`8 × 127 × 127 = 129032` 会溢出成 `-1828`，边界测试会失败。项目选 `+&` 而非 `+`，正是为了避免这个静默溢出。

---

## 2. 为什么旁路 MGU，而不是修改 MGU

### 2.1 两种接入方式

`VIMacU` 原有写回路径是 `mgu.io.out.vd`（逐元素写回）。接入 `vdot` 有两条路：

**方案 A：改 MGU 内部逻辑**，让它在遇到 `vdot` 时输出归约结果。
**方案 B（本项目采用）：在 `VIMacU` 外壳用 Mux 旁路。**

```scala
private val outIsVDot = VDotType.isVDot(outCtrl.fuOpType)
private val outVDotIllegal = outVecCtrl.vsew =/= VSew.e8

io.out.bits.res.data := Mux(outIsVDot, vdotResult, mgu.io.out.vd)

io.out.bits.res.vxsat.get := Mux(outIsVDot, false.B,
  (outVxsat & mgu.io.out.active).orR)

io.out.bits.ctrl.exceptionVec.get(ExceptionNO.illegalInstr) := Mux(
  outIsVDot, outVDotIllegal, mgu.io.out.illegal)
```

（`VIMacU.scala:194-213`）

### 2.2 取舍理由

| 维度 | 方案 A（改 MGU） | 方案 B（外壳旁路） |
|---|---|---|
| 对上游代码的侵入 | 大，需改 MGU 内部状态机 | 小，仅新增 Mux 与常量 |
| 回归风险 | 高，MGU 是 `vmul` 等指令的公共路径 | 低，`outIsVDot=false` 时原路径完全不变 |
| 可回退性 | 差 | 好，删除新增代码即恢复 |
| 面积开销 | 复用 MGU 的部分逻辑 | 新增 8 乘法器 + 7 加法器 |

**方案 B 的核心理由是隔离性**：`MGU` 服务所有向量乘法类指令，改动它会波及 `vmul.vv`、`vmacc` 等一大批指令的验证。旁路方案保证 `outIsVDot` 为假时**零行为变化**，这在工程上是更稳妥的取舍。

代价是面积：8 个 int8 乘法器 + 7 个加法器独立于 MGU 存在。这部分开销可以用 Yosys 通用门级综合量化：整条 vdot 数据通路（含乘法器与三级加法树）为 **3,736 个等效门**，作为对照的串行累加链实现为 3,806 个。也就是说，采用平衡树不仅没有付出面积代价，反而比串行链略省 1.8%。相对香山整核的规模，这部分属于可接受范围。

**注意**：这一取舍与设计文档原有表述存在措辞冲突。原表述为「VDOT 被送入现有 VIMac 执行通路」，实际是**在不修改 MGU 的前提下于 `VIMacU` 外壳新增独立数据通路**。准确的说法是"复用了 `VIMacU` 这个功能单元外壳与它的译码/发射链路，但数据通路是新增的"。

### 2.3 FuOpType 编码的不新增功能单元

`VDotType.vdot = BitPat("b011100000")`，注释说明：

> `01_110_0_000` keeps the low 7 bits identical to signed vmul, while using the otherwise-unused upper pad bits to distinguish VDOT.

`VimacType` 的字段布局是 `[8:7] pad`、`[6] vs2 signed`、`[5] vs1 signed`、`[4] old vd signed`、`[3] widen`、`[2:0] opcode`。低 7 位 `110_0_000` 与 signed `vmul` 完全一致，因此**不需要在功能单元分派表中新增条目**——`VIMacU` 本来就会接收这类 FuOp，只是在内部按高位的 `01` 分流。

这是一个实现上的小技巧：**用寄存器位的冗余空间做特征位**，避免动 `FuConfig` 的分派逻辑。

---

## 3. 扩展路径

### 3.1 扩展到 SEW=16（vdot 的 16 位版本）

当前实现固定按 `8*i+7, 8*i` 切片，SEW=16 时需改为 `16*i+15, 16*i`，且项数从 8 变为 4（VLEN=128 时每寄存器只有 8 个 16 位元素，取低 4 个或全部 8 个取决于规格）。

**改动点**：

| 位置 | 当前 | SEW=16 版本 |
|---|---|---|
| `vdotProducts` 切片 | `8*i+7, 8*i` | `16*i+15, 16*i` |
| 项数 | 8 | 8（VLEN=128 全用）或 4 |
| 乘积位宽 | 16 | 32 |
| 树级数 | 3（8 项） | 3（8 项） |
| 最终位宽 | 19 | 35 → 需收窄到 32 或扩展架构定义 |
| `outVDotIllegal` | `vsew =/= e8` | `vsew =/= e8 && vsew =/= e16` |

**关键难点是位宽**：int16×int16 的乘积是 32 位，8 项求和需 35 位，超出 32 位架构结果宽度。这需要规格层面决定：是允许溢出（saturate / wrap），还是把结果宽度扩到 64 位并占用 `vd[63:0]`。**这不是实现问题，是规格问题**，也是本项目当前只做 SEW=8 的合理理由。

### 3.2 项数参数化（当前硬编码 8）

当前 `(0 until 8)`、`0.U(96.W)`、`8*i+7` 三处字面量硬编码。参数化的改法：

```scala
// 引入配置参数
class VDotConfig(terms: Int = 8) extends ...
private val vdotProducts = (0 until terms).map { i => ... }
private val clearWidth = 128 - 32   // 96，与项数无关
private val treeLevels = log2Ceil(terms)
```

**收益**：可复用于项数不同的变体（如 4 项、16 项）。
**成本**：位宽推导需从常量变成函数（`terms × 127 × 127` 的位宽随 terms 变），Chisel 的 `+&` 会自动扩位，但最终收窄到 32 位时需要显式检查是否溢出。

**这一项是低风险改动**，不涉及功能单元结构，只影响参数化程度。

### 3.3 VLEN=256 / 512

VLEN 扩展对本实现**影响很小**，因为语义规定只取**低 8 个元素**，与 VLEN 无关。改动点：

| 位置 | 改动 |
|---|---|
| `Cat(0.U(96.W), vdotSum32)` | `96` 改为 `VLEN - 32`（VLEN=256 时 224） |
| 源切片 | 不变（仍取低 8 字节） |
| 乘法器/加法树 | **不变** |

也就是说，**VLEN 扩展只是清零位宽的变化，计算逻辑完全不动**。这是本设计的一个潜在优势：语义定义在"低 8 元素"上，天然与 VLEN 解耦。

### 3.4 扩展到其他向量指令

本项目的接入模式（`VecDecoder` 新增 `BitPat` → `OPIVV(FuType, FuOpType)` → 在目标功能单元内用 Mux 旁路）**可复用**于其他自定义归约类指令，例如：

- `vsum.vv`（向量求和归约）
- `vmaxred.vv`（向量最大值归约）
- `vdot.vx`（点积，第二个操作数为标量）

这些指令的共同点是"多元素输入、单元素输出"，与 `vdot` 的落位方式一致：只需要在 `VecDecoder` 加一条 `BitPat`，在功能单元内加一条独立数据通路 + Mux，不需要改分派表。

---

## 4. 局限性说明

为保持诚实，以下问题在本实现中**未解决**：

1. **未处理 `vl` / `vstart` / `LMUL`。** 当前实现假定 `vl=8`、`vstart=0`，超出即按非法指令处理（`outVDotIllegal` 只检查 `vsew`）。严格来说应补充 `vl =/= 8 && vl =/= 0` 的检查，或明确声明本指令只支持 `vl=8`。
2. **未做参数化。** 三处字面量硬编码，见 3.2 节。
3. **未测单指令延迟。** 阶段三只测了吞吐（cycles/op），`CertainLatency(2)` 来自上游配置而非本指令的实测。
4. **工艺级面积未量化。** 8 乘法器 + 7 加法器的相对面积已通过 Yosys 通用门级综合测得（见 `synthesis/SYNTHESIS_ANALYSIS.md`：3,736 等效门 vs 串行链 3,806），但**未接入工艺库**，因此没有 µm²、ns 或频率数字。

以上四项中，第 1、2 项是可以低成本补的；第 3、4 项需要重新实验，超出本次提交范围。

---

## 5. 小结

| 设计点 | 取舍 | 收益 | 代价 |
|---|---|---|---|
| 平衡归约树 vs 串行链 | 选平衡树 | 关键路径 45 级 vs 62 级（−27.4%），面积还省 1.8% | 无 |
| 外壳旁路 vs 改 MGU | 选旁路 | 对 `vmul` 等指令零影响 | 新增独立数据通路面积 |
| 高位特征位 vs 新分派条目 | 选特征位 | 不动 `FuConfig` 分派表 | 编码空间被占用 2 位 |
| 硬编码 8 项 vs 参数化 | 选硬编码 | 实现简单、易验证 | 扩展性差（3.2 节给出改法） |
| 仅支持 SEW=8 | 限于规格 | 避免 35 位溢出问题 | 无法覆盖 16 位场景（3.1 节分析） |
