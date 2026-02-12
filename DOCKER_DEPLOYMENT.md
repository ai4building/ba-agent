# BA-Agent Docker 部署指南

本文档说明如何构建和部署 BA-Agent Python 服务到 Haxall/FIN Framework 环境。

## 目录

- [镜像构建](#镜像构建)
- [自动部署 (GitHub Actions)](#自动部署-github-actions)
- [手动部署](#手动部署)
- [配置环境变量](#配置环境变量)
- [在 Haxall 中使用](#在-haxall-中使用)

---

## 镜像构建

### 前提条件

- Docker 已安装
- 项目代码在本地

### 构建命令

```bash
cd /Users/syatanic/Apps/ai4building/ba-agent
docker build -t ba-agent-py:latest -f src/baAgentPy/Dockerfile .
```

### 验证镜像

```bash
docker run --rm ba-agent-py:latest python -c "from baAgentPy.main import BaAgentService; print('OK')"
```

---

## 自动部署 (GitHub Actions)

### 工作流程

当您推送代码到 `main` 分支时，GitHub Actions 自动：

1. 构建新的 Docker 镜像
2. 推送到 GitHub Container Registry (`ghcr.io`)
3. 推送到 Docker Hub (`docker.io`)

### 手动触发

访问 GitHub Actions 页面，选择 **Docker Build & Push** workflow，点击 **Run workflow** 按钮。

---

## 配置环境变量

脚本支持通过环境变量覆盖组织名称：

| 变量 | 默认值 | 描述 |
|--------|--------|--------|
| `GITHUB_ORG` | `ai4building` | GitHub 用户名/组织 |
| `DOCKERHUB_USERNAME` | `${GITHUB_ORG}` | Docker Hub 用户名（默认与 GitHub 相同） |

---

## GitHub Secrets 配置

在 GitHub 仓库设置中添加以下 Secrets：

| Secret 名称 | 用途 | 示例值 |
|-------------|------|----------|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名（可选，用于推送到 Docker Hub） | `your-dockerhub-username` |
| `DOCKERHUB_TOKEN` | Docker Hub 访问令牌（可选，用于推送到 Docker Hub） | `dckr_pat_xxxxxx` |

**注意**：如果只配置 `GITHUB_ORG`，则只推送到 GitHub Container Registry。

---

## 镜像标签

构建后，镜像将使用以下标签：

- `latest` - 始终指向最新的 main 分支构建
- `v1.0.0` - 语义化版本标签
- `build-YYYYMMDDHHmmss` - 唯一构建 ID

---

## 手动部署

### 构建并推送到 GitHub Container Registry

```bash
# 登录
echo $GITHUB_TOKEN | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# 构建
docker build -t ghcr.io/ai4building/ba-agent-py:latest -f src/baAgentPy/Dockerfile .

# 推送
docker push ghcr.io/ai4building/ba-agent-py:latest
```

### 推送到 Docker Hub (`docker.io`)

```bash
# 登录
docker login -u ${DOCKERHUB_USERNAME}

# 标记
docker tag ba-agent-py:latest ${DOCKERHUB_USERNAME}/ba-agent-py:latest

# 推送
docker push ${DOCKERHUB_USERNAME}/ba-agent-py:latest
```

### 加载到本地 Haxall

```bash
# 将镜像保存为 tar 文件
docker save ba-agent-py:latest -o ba-agent-py.tar

# 在 Haxall 中加载
# (通过 Haxall UI 或配置文件)
```

---

## 配置环境变量

| 变量名 | 必需 | 默认值 | 描述 |
|---------|------|----------|--------|
| `GEMINI_API_KEY` | 否 | - | Google Gemini 2.5 Flash API 密钥 |
| `MAX_RETRIES` | 否 | `5` | API 调用重试次数 |
| `REQUEST_TIMEOUT` | 否 | `30` | 请求超时（秒） |

---

## 在 Haxall 中使用

### 基本用法

```axon
// === 本地 Python 会话 ===
session := py(image: "ba-agent-py:latest")

// === 导入并初始化 ===
pyExec(session, "from baAgentPy.main import BaAgentService")
pyDefine(session, {svc: "BaAgentService()"})
pyEval(session, "svc.handle('ping', {})")

// === LLM 意图解析 ===
result := pyEval(session, "agent.ask('诊断一下AHU-01的故障')")

// === 访问结果 ===
echo(result->status)  // "ok", "error"
echo(result->action)  // "ask"
echo(result->result)  // 包含 _llm_confidence, _llm_thought 等
```

### 直接调用引擎（跳过 LLM）

```axon
// 直接路由到指定引擎
result := pyEval(session, "agent.handle('diagnose', {target_equip: 'AHU-01'})")
```

---

## 故障排除

### 容器无法启动

```bash
# 查看容器日志
docker logs ba-agent-py-container

# 检查 Python 路径
docker exec ba-agent-py-container python -c "import sys; print(sys.path)"

# 检查模块导入
docker exec ba-agent-py-container python -c "from baAgentPy.main import BaAgentService; print('OK')"
```

### API 调用失败

1. 检查 `GEMINI_API_KEY` 是否正确
2. 查看网络连接（容器需要访问互联网）
3. 检查日志中的错误信息

### hxPy 无法导入模块

```bash
# 验证模块在 /io/ 目录中
docker exec ba-agent-py-container ls -la /io/baAgentPy/

# 检查 Python 路径
docker exec ba-agent-py-container python -c "import sys; print('\\n'.join(sys.path))"
```

---

## 镜像信息

- **名称**: `ba-agent-py`
- **版本**: `latest`
- **基础镜像**: `ghcr.io/haxall/hxpy:latest`
- **Python 版本**: `3.13`
- **大小**: 约 500-800 MB（取决于依赖安装）

---

## 相关链接

- [部署指南](.)
- [设计文档](DESIGN.md)
- [Haxall 文档](https://github.com/haxall/haxall)
- [FIN Framework](https://finframework.com/)

---

**BA-Agent Team** © 2024-2025
