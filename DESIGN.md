BA-Agent (Building Automation AI Agent) 系统架构与代码结构设计指南1. 概述BA-Agent 是一个基于 J2 Innovations FIN Framework / Haxall 架构的跨语言集成系统。它旨在通过 AI 技术打通建筑自动化系统的全生命周期：从工程建设阶段的 HMI 自动生成，到运维阶段的 智能报警诊断 (FDD)、动态节能优化 以及 虚拟自动巡检。1.1 技术栈核心中枢神经 (Middleware): Fantom (Haxall/FIN Pod) & AXON 脚本。大脑 (AI Engine): Python (LangChain, NumPy, Pydantic, DuckDB)。桥接层 (Integration): hxPy (Haxall Python Bridge)。交互界面 (HMI/UI): HTML5 (React/Vue) + WebSocket。2. 项目目录结构ba-agent-project/
├── docker-compose.yml              # 容器化编排 (Python 环境 + Haxall 实例)
├── src/
│   ├── baAgentPod/                # Fantom 核心插件层
│   │   ├── build.fan              # Pod 构建定义
│   │   ├── fan/                   # Fantom 源码 (Ext, WebHandler, Bridge)
│   │   ├── axon/                  # AXON 脚本库 (定义系统 Ops)
│   │   │   ├── hmiOps.axon        # 工程侧：HMI 逻辑处理
│   │   │   ├── omOps.axon         # 运维侧：FDD、节能、巡检逻辑
│   │   │   └── utilOps.axon       # 工具类：数据打包与格式化
│   │   └── assets/                # 前端静态资源挂载点
│   │
│   ├── baAgentPy/                 # Python AI 服务层 (运行于 Docker)
│   │   ├── main.py                # hxPy 入口与会话管理
│   │   ├── core/                  # LLM 编排与 Agent 逻辑
│   │   │   └── agent_workflow.py  # 任务路由与指令解析
│   │   ├── services/              # 业务算法服务
│   │   │   ├── hmi_engine.py      # [工程] UI/逻辑自动化布局算法
│   │   │   ├── fdd_engine.py      # [运维] 故障诊断与根因分析 (RCA)
│   │   │   ├── energy_opt.py      # [运维] 能效孪生与动态设定值优化
│   │   │   ├── inspect_engine.py  # [运维] 虚拟巡检与传感器健康评分
│   │   │   └── report_engine.py   # [运维] 自动化运行简报生成
│   │   └── utils/                 # Grid 转换与数据处理
│   │
│   └── baAgentUI/                 # 前端交互界面 (SPA)
│       ├── src/
│       │   ├── components/        # 聊天窗口、诊断卡片、预览面板
│       │   └── hooks/             # WebSocket 状态管理
│       └── package.json
│
└── tests/                         # 跨平台功能测试 (Python/Axon)
3. 核心模块职责详述3.1 baAgentPod (Fantom/AXON)负责与建筑底层点位数据的直接交互，是 AI 指令的执行者。数据网关: 通过 AXON 抓取实时点位 (curVal)、历史趋势 (hisRead) 和语义标签 (Haystack 4)。运维 Ops 扩展:agentTicketGen: 确认为设备故障后，自动对接第三方工单系统。agentLoadShed: 响应电力负荷需求，执行柔性策略。安全屏障 (Shadow Mode): AI 的写入操作默认进入暂存区（Priority 16），需人工通过 UI 确认后生效。3.2 baAgentPy (Python AI)利用 Python 强大的生态处理非结构化任务。fdd_engine:故障模式识别: 利用关联分析判断是局部设备故障还是全局系统异常。根因分析 (RCA): 沿着 Haystack 拓扑链路追溯。例如：VAV 风量不足 -> 追溯至 AHU 变频器故障。energy_opt:能耗预测: 基于天气和室内负荷预测未来能耗。动态控制策略: 每小时计算最优 PID 设定值（如冷却水出水温度优化）。inspect_engine:零漂检测: 识别传感器长期存在的微小读数偏差。一致性核查: 比较相互关联的传感器数据（如送风温度与回风温度的差值是否在物理合理范围内）。3.3 baAgentUI (前端)交互式 HMI: 不再只是静态画面，而是能与 AI 对话的动态面板。诊断可视化: 通过 3D 拓扑图直观展示 AI 诊断出的故障路径。4. 关键业务流程设计4.1 智能报警与根因诊断 (O&M Scene)报警产生: 建筑产生原始报警（如冷机排气压力过高）。上下文富化: AXON 自动提取该报警及其上下游所有关联设备的实时 Grid 数据。AI 分析: Python 引擎结合历史模式与专家规则库进行推理。交互输出: UI 展示诊断结论：“有 85% 概率为冷却水塔风机皮带打滑，导致换热效率下降”。4.2 动态节能闭环 (Energy Scene)实时监测: energy_opt 模块订阅建筑总能耗点位。模拟预测: AI 运行数字孪生模型，模拟不同控制参数下的节能百分比。指令下发: agentOptimizeSetpoints 将优化后的参数组发送给 FIN 系统。效果评估: 24 小时后，AI 自动生成“节能贡献报告”，量化节约的电费与碳排。4.3 虚拟巡检流程 (Inspection Scene)触发: 定时器每周触发虚拟巡检任务。全量扫描: 对所有末端传感器进行“数据体检”。健康评分: AI 根据数据响应速度、线性度、波动频率给出 0-100 分。维护建议: 将得分低于 60 的传感器列入“建议更换名单”，推送到运维人员手机。5. 技术原则与风险控制数据安全 (Security):涉及生命安全（消防、排烟、应急电源）的点位设为 Read-Only，AI 仅能观察，无权操作。可解释性 (XAI):AI 所有的运维建议必须包含“因为...所以...”的推导逻辑，并附带历史趋势图表作为证据。性能保障:Python 与 Haxall 之间使用非阻塞异步调用，确保 AI 的大规模计算不影响底层控制器的实时性。离线生存能力:核心诊断逻辑应能在本地 Docker 运行，不强制依赖公网 LLM，确保在离线专网环境下依然可用。