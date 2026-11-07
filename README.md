# CIE2026 XiangShan Kunminghu V2 VDOT

本项目面向 2026 CIE 全国 RISC-V 高水平创新及应用大赛，
基于 XiangShan Kunminghu V2 实现自定义 `vdot.vv` 向量点积指令。

## 当前总体状态

- Phase 1：已完成并封存
- Phase 2：已完成并封存
- Phase 3 技术部分：已完成并封存
- 正式报告 / 讲解视频 / PPT：由队友整理中
- GitHub / submission.asc / 官方 PR：最终提交阶段再进行

## Phase 1：环境部署与验证

已完成。

包括：

- XiangShan / NEMU / nexus-am 环境
- Kunminghu V2 baseline
- CoreMark DiffTest
- Hello bare-metal 程序
- 标准 RVV `vadd.vv`
- FST / GTKWave 验证
- Phase 1 操作录屏

## Phase 2：vdot.vv 设计与实现

已完成并封存。

最终官方语义：

- VLEN = 128
- SEW = 8
- 两个源寄存器仅使用低 8 个 signed INT8 元素（0..7）
- 完成 8 项 signed INT8 乘积并归约求和
- 32-bit signed 结果写入 `vd[31:0]`
- `vd[127:32] = 0`
- 高 8 个字节不参与计算

测试指令：`vdot.vv v10, v8, v9`

机器码：`0x0294050B`

主要验证结果：36、-36、131072、-130048、127，以及高半区 poison 忽略测试 127。

## Phase 3：协同仿真与性能评估

技术部分已完成并封存。

### 3.1 NEMU reference model 与 RTL 协同仿真

- NEMU 已支持本项目 custom-0 `vdot.vv`
- 标准 RVV `vadd.vv` DiffTest 回归通过
- `vdot.vv` 六类合法测试 RTL + NEMU DiffTest 全部通过
- 非 e8 的 `vdot.vv` illegal-instruction 行为通过

### 3.2 标准 RVV 等价 baseline

- 使用 `vwmul.vv + vwredsum.vs` 实现数学等价计算
- 六类输入结果与自定义 `vdot.vv` 一致
- RTL + NEMU DiffTest 通过

### 3.3 性能评估

正式测量采用相同输入、相同重复次数和相同模拟器，主要指标为 guest `rdcycle`。

- Custom VDOT compute：1.050781 cycles/op
- RVV baseline compute：5.011719 cycles/op
- Compute speedup：4.769517x
- Custom VDOT end-to-end：6.937500 cycles/op
- RVV baseline end-to-end：9.941406 cycles/op
- End-to-end speedup：1.432995x

VDOT 功能单元 RTL latency 为 2 cycles；该 latency 与上述 benchmark throughput 指标不是同一个概念。

## 目录

    01_phase1/          Phase 1 最终技术证据
    02_phase2/          Phase 2 最终技术证据
    03_phase3/          Phase 3 技术证据（已完成并封存）
    source/             最终源码材料
    docs/               正式报告与说明文档（最终整理中）
    demo/               演示视频与展示材料（最终整理中）
    github_submission/  官方 GitHub 提交辅助材料（最后阶段处理）

## 证据与提交说明

Phase 1、Phase 2 和 Phase 3 的技术实验均已完成。
当前尚未完成的是最终文档整合、演示材料和官方 GitHub 提交流程，而不是 Phase 3 技术实现。

大型 FST、emulator、运行时 SO 等调试产物不进入公开作品仓库。
完整技术证据保留在最终证据目录及独立封存包中，并使用 SHA256 校验。

