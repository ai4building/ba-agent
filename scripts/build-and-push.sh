#!/bin/bash
# BA-Agent Docker Build & Push Script
# 快速构建和推送 Docker 镜像的便捷脚本

set -e  # Exit on any error

# 配置
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="ba-agent-py"
DOCKERFILE_PATH="src/baAgentPy"
REGISTRY="ghcr.io"
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-${GITHUB_ORG:-ai4building}}"  # Docker Hub 组织名，默认使用 GitHub 组织名
GITHUB_ORG="${GITHUB_ORG:-ai4building}"  # GitHub 组织名

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  BA-Agent Docker Build & Push${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""

# 步骤 1: 清理旧构建
echo -e "${YELLOW}[1/5]${NC} 清理旧镜像..."
docker rmi ${IMAGE_NAME}:latest 2>/dev/null || true
echo -e "${GREEN}✓ 清理完成${NC}\n"

# 步骤 2: 构建新镜像
echo -e "${YELLOW}[2/5]${NC} 构建 Docker 镜像..."
echo -e "   ${GREEN}docker build${NC} -t ${IMAGE_NAME}:latest -f ${DOCKERFILE_PATH}/Dockerfile ."
docker build -t ${IMAGE_NAME}:latest -f ${DOCKERFILE_PATH}/Dockerfile .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 构建成功${NC}\n"
else
    echo -e "${RED}✗ 构建失败${NC}\n"
    exit 1
fi

# 步骤 3: 测试镜像
echo -e "${YELLOW}[3/5]${NC} 测试镜像..."
docker run --rm ${IMAGE_NAME}:latest python -c "from baAgentPy.main import BaAgentService; print('BA-Agent loaded successfully')"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 镜像测试通过${NC}\n"
else
    echo -e "${RED}✗ 镜像测试失败${NC}\n"
    exit 1
fi

# 步骤 4: 询问是否推送到 GitHub Container Registry
echo ""
read -p "$(echo -e "${YELLOW}是否推送到 GitHub Container Registry? (y/N): ${NC}")" -n -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[4/5]${NC} 推送到 GitHub Container Registry (${REGISTRY})..."
    echo -e "   ${GREEN}docker tag${NC} ${IMAGE_NAME}:latest ${REGISTRY}/${GITHUB_ORG}/${IMAGE_NAME}:latest"
    docker tag ${IMAGE_NAME}:latest ${REGISTRY}/${GITHUB_ORG}/${IMAGE_NAME}:latest

    echo -e "   ${GREEN}docker push${NC} ${REGISTRY}/${GITHUB_ORG}/${IMAGE_NAME}:latest"
    docker push ${REGISTRY}/${GITHUB_ORG}/${IMAGE_NAME}:latest

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 推送完成${NC}\n"
        echo -e "镜像: ${GREEN}${REGISTRY}/${GITHUB_ORG}/${IMAGE_NAME}:latest${NC}"
    else
        echo -e "${RED}✗ 推送失败${NC}\n"
        exit 1
    fi
fi

# 步骤 5: 询问是否推送到 Docker Hub
echo ""
read -p "$(echo -e "${YELLOW}是否推送到 Docker Hub? (y/N): ${NC}")" -n -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    DOCKERHUB_FINAL_USERNAME="${DOCKERHUB_USERNAME:-${GITHUB_ORG}}"
    echo -e "${YELLOW}[5/5]${NC} 推送到 Docker Hub..."
    echo -e "   ${GREEN}docker tag${NC} ${IMAGE_NAME}:latest ${DOCKERHUB_FINAL_USERNAME}/${IMAGE_NAME}:latest"
    docker tag ${IMAGE_NAME}:latest ${DOCKERHUB_FINAL_USERNAME}/${IMAGE_NAME}:latest

    echo -e "   ${GREEN}docker push${NC} ${DOCKERHUB_FINAL_USERNAME}/${IMAGE_NAME}:latest"
    docker push ${DOCKERHUB_FINAL_USERNAME}/${IMAGE_NAME}:latest

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 推送完成${NC}\n"
        echo -e "镜像: ${GREEN}docker.io/${DOCKERHUB_FINAL_USERNAME}/${IMAGE_NAME}:latest${NC}"
    else
        echo -e "${RED}✗ 推送失败${NC}\n"
        exit 1
    fi
fi

# 完成
echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN} 构建完成！${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo -e "本地镜像: ${GREEN}${IMAGE_NAME}:latest${NC}"
echo ""
echo -e "在 Haxall 中使用:"
echo -e "  ${GREEN}py(image: \"${IMAGE_NAME}:latest\")${NC}"
echo ""
echo -e "加载服务:"
echo -e "  ${GREEN}pyExec(session, \"from baAgentPy.main import BaAgentService\")${NC}"
echo -e "  ${GREEN}pyEval(session, \"svc = BaAgentService()\")${NC}"
echo -e "  ${GREEN}pyEval(session, \"svc.ask('你的指令')\")${NC}"
echo ""
echo -e "${GREEN}镜像地址:${NC}"
echo -e "  GitHub: ${GREEN}ghcr.io/${GITHUB_ORG}/${IMAGE_NAME}:latest${NC}"
echo -e "  Docker Hub: ${GREEN}docker.io/${DOCKERHUB_USERNAME}/${IMAGE_NAME}:latest${NC}"
