# AI 客服中台 MVP

第一周版本目标是把后端工程骨架、核心数据模型和最小业务闭环搭起来，当前已包含：

- FastAPI 应用入口与 Swagger
- 统一响应结构、异常处理、`trace_id` 中间件
- `health`、`sessions`、`messages` 三个接口
- SQLAlchemy 模型、Repository、Service 分层
- Alembic 初始化脚本
- 基础 API / Service 测试

## 本地启动

1. 安装依赖

```bash
uv sync --dev
```

如果本机 `uv` 默认缓存目录不可写，可以在项目目录下指定缓存：

```bash
UV_CACHE_DIR=.uv-cache uv sync --dev
```

2. 配置环境变量

```bash
cp .env.example .env
```

默认会优先读取 `DATABASE_URL`。如果未提供，则会根据 `POSTGRES_*` 拼接 PostgreSQL 连接串；如果这些值也未配置，会退回到本地 SQLite 文件，方便本地开发和测试。

3. 启动服务

```bash
uv run uvicorn app.main:app --reload
```

4. 查看文档

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## Alembic

执行迁移：

```bash
uv run alembic upgrade head
```

## 测试

```bash
uv run pytest
```
