============================================================
2026 CIE 全国 RISC-V 高水平创新及应用大赛
香山 Kunminghu V2 自定义 vdot.vv 项目
最终提交工作区检查表
============================================================

重要：

本目录是最终提交准备区。
Phase 1、Phase 2、Phase 3 技术实验均已完成。
当前仍待完成的是正式文档、演示材料和最后的 GitHub 官方提交。

队友写作素材：
- ../phase1_handout/
- ../phase2_handout/
- ../phase3_handout/

============================================================
一、阶段完成状态
============================================================

[OK] 1. 阶段一：环境部署与验证
[OK] 2. 阶段二：vdot.vv 设计与实现
[OK] 3. 阶段三：协同仿真与性能评估（技术部分）

阶段三已完成：
[OK] NEMU reference model 支持自定义 vdot.vv
[OK] 标准 RVV vadd.vv DiffTest 回归
[OK] vdot.vv 六类合法输入 RTL + NEMU DiffTest
[OK] 非 e8 illegal-instruction 测试
[OK] 标准 RVV 数学等价 baseline
[OK] baseline RTL + NEMU DiffTest
[OK] 正式性能 benchmark
[OK] compute speedup = 4.769517x
[OK] end-to-end speedup = 1.432995x
[OK] Phase 3 technical evidence sealed

============================================================
二、正式提交前仍需完成
============================================================

[OK] 队友完成最终项目报告 / 说明文档
[OK] 队友完成需要的 Phase 2 / Phase 3 讲解视频或 PPT
[OK] 将最终通过审核的文档放入 docs/
[OK] 将最终通过审核的演示材料放入 demo/
[OK] 对正式提交目录做最终全包审计
[OK] 建立并确认作品 GitHub 公有仓库
[OK] 推送最终公开作品仓库
[OK] Fork OpenXiangShan/XiangShanLab
[OK] 按最终官方指南准备 my_submission.txt
[OK] 生成 submission.asc
[OK] 推送 submission.asc 至自己的 XiangShanLab Fork
[OK] 向 OpenXiangShan/XiangShanLab 创建最终 PR

注意：正式提交当天再次核对官方 SUBMISSION_GUIDE。

============================================================
三、目录用途
============================================================

01_phase1/
  Phase 1 最终技术证据

02_phase2/
  Phase 2 最终技术证据

03_phase3/
  Phase 3 技术证据，已完成并封存；不要修改技术封存内容

docs/
  最终报告、说明书等正式文档

source/
  最终提交版本源码材料

demo/
  最终演示视频、截图及展示材料

github_submission/
  官方提交辅助材料
  不要提前在公开作品仓库中放置联系方式等隐私信息

============================================================
四、重要原则
============================================================

1. Phase 1 / Phase 2 / Phase 3 技术证据已经封存，不因文档整理而重跑或修改。

2. 不把大型 FST、emu、运行时 SO、ELF、BIN 等调试产物无脑提交进公开 GitHub 仓库。

3. 公开作品仓库优先包含源码、workload、README、复现说明、关键日志、截图和性能摘要。

4. 所有性能数字必须与正式封存日志一致。

5. 正式文档不得出现旧的 16-term VDOT 语义。官方实现只计算低 8 个 signed INT8 元素。

6. Phase 3 已完成的是技术实现与验证；最终报告、视频/PPT和官方提交仍需单独完成。

7. 最终提交前再次检查 README、报告、视频、GitHub 仓库和 submission.asc 之间的信息一致性。

============================================================

