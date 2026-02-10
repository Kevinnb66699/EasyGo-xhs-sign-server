# 使用 Playwright 官方镜像（已包含所有依赖，避免安装过时包的问题）
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PORT=5005

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY server.py .
COPY test_server.py .

# 暴露端口
EXPOSE 5005

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5005/health', timeout=5).raise_for_status()" || exit 1

# 启动应用
CMD ["python", "server.py"]
