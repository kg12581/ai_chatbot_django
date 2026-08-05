# Nocturne AI · Django 运行镜像
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装运行时依赖（requirements-docker.txt 已剔除系统包、补齐 APScheduler），利用 Docker 层缓存
# 说明：torch/chromadb 等均有预编译 manylinux wheel，无需系统编译工具；
#       如网络受限可用国内镜像：docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=https://pypi.org/simple
COPY requirements-docker.txt .
RUN pip install --index-url ${PIP_INDEX_URL} -r requirements-docker.txt

# 复制项目代码（.env 不打包，运行时通过环境变量注入）
COPY . .

EXPOSE 8000

# 默认：迁移 + 开发服务器；生产环境可替换 CMD（如 gunicorn）
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
