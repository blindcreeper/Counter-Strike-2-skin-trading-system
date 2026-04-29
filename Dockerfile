# CS2 皮肤量化回测系统 - Dockerfile
# 基础镜像：官方 Python 3.11
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libatlas-base-dev \
    gfortran \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码和配置
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY data/ ./data/
COPY output/ ./output/
COPY docs/ ./docs/
COPY entrypoint.sh .

# 给 entrypoint 脚本添加执行权限
RUN chmod +x entrypoint.sh

# 暴露状态监控端口
EXPOSE 8199

# 健康检查：访问状态 API 判断进程是否存活
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8199/health || exit 1

# 入口点
ENTRYPOINT ["./entrypoint.sh"]

# 默认命令
CMD ["main"]
