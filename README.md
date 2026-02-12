# BA-Agent

Building Automation AI Agent for FIN Framework / Haxall

## 项目简介

BA-Agent 是一个建筑自动化 AI 代理服务，通过 hxPy 容器运行在 Haxall/FIN Framework 中。它使用 LLM（Gemini 2.5 Flash）进行意图解析，并通过多个领域引擎执行诊断、优化、巡检、HMI 生成等任务。

## 功能特性

- **LLM 意图解析** - 使用 Gemini 2.5 Flash API 进行自然语言理解
- **故障诊断 (FDD)** - 根因分析、异常检测
- **能源优化** - 设定值优化、节能策略
- **虚拟巡检** - 传感器健康评分、漂移检测
- **HMI 生成** - 自动生成监控画面布局
- **报告生成** - 运维日报、操作摘要
- **自动标注** - Haystack 4.0 语义标签

## 快速开始

### 前置要求

- Python 3.12+
- Docker
- Haxall/FIN Framework (用于运行 hxPy 容器)

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/your-org/ba-agent.git
cd ba-agent

# 安装依赖
uv sync

# 运行测试
uv run pytest tests/

# 本地运行服务
uv run python src/baAgentPy/main.py
```

### Docker 构建

```bash
# 构建镜像
docker build -t ba-agent-py:latest -f src/baAgentPy/Dockerfile .

# 或使用便捷脚本
./scripts/build-and-push.sh
```

## 部署

详细的部署指南请参考 [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### 快速部署到 Haxall

```bash
# 1. 构建镜像
docker build -t ba-agent-py:latest -f src/baAgentPy/Dockerfile .

# 2. 在 Haxall AXON 中使用
py(image: "ba-agent-py:latest")
pyExec(session, "from baAgentPy.main import BaAgentService")
pyEval(session, "svc = BaAgentService()")
pyEval(session, "svc.ask('诊断一下AHU-01')")
```

### GitHub Actions 自动部署

推送到 `main` 分支时自动构建和推送 Docker 镜像。

配置 GitHub Secrets:
- `DOCKERHUB_USERNAME` - Docker Hub 用户名
- `DOCKERHUB_TOKEN` - Docker Hub 访问令牌

## 项目结构

```
ba-agent/
├── src/
│   ├── baAgentPod/          # Fantom/AXON 代码 (插件、Ops)
│   ├── baAgentPy/           # Python AI 服务
│   │   ├── main.py          # BaAgentService 入口
│   │   ├── core/            # 核心编排
│   │   ├── services/        # 领域引擎
│   │   └── utils/          # 工具函数
│   └── baAgentUI/          # React 前端 (Vite + TypeScript)
├── tests/                   # Python 测试
├── docs/                    # 项目文档
└── scripts/                 # 构建和部署脚本
```

## API 使用示例

### 在 AXON 中调用

```axon
// === 本地 Python 会话 ===
session := py(image: "ba-agent-py:latest")
pyExec(session, "from baAgentPy.main import BaAgentService")
pyDefine(session, {agent: "BaAgentService(enable_llm=true)"})

// === LLM 意图解析 ===
result := pyEval(session, "agent.ask('优化12楼空调设定值')")
// 返回: {status: "ok", action: "optimize", result: {...}, llm_enabled: true}

// === 直接调用引擎 ===
diagnosis := pyEval(session, "agent.handle('diagnose', {target_equip: 'AHU-01'})")
optimization := pyEval(session, "agent.handle('optimize', {floor: 12})")
inspection := pyEval(session, "agent.handle('inspect', {equip_type: 'VAV'})")
```

## 环境变量

| 变量 | 描述 | 默认值 |
|--------|--------|--------|
| `GEMINI_API_KEY` | Gemini 2.5 Flash API 密钥 | - |
| `MAX_RETRIES` | API 重试次数 | 5 |
| `REQUEST_TIMEOUT` | 请求超时（秒） | 30 |

## 开源协议

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 相关链接

- [部署指南](DOCKER_DEPLOYMENT.md)
- [设计文档](DESIGN.md)
- [Haxall 文档](https://github.com/haxall/haxall)
- [FIN Framework](https://finframework.com/)

## 许可

MIT License

---

**BA-Agent Team** © 2024-2025
