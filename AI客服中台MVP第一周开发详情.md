# AI 客服中台 MVP 第一周开发详情

## 1. 第一周目标

第一周的目标不是把 AI 客服做“聪明”，而是把后端工程骨架和主数据结构搭起来，让项目进入可持续开发状态。到第一周结束时，系统至少要具备以下基础能力：

- 项目可以正常启动
- 已完成基础工程结构搭建
- PostgreSQL、Redis 连接可用
- 核心数据表已经建立
- 数据迁移流程可用
- 基础中间件、日志、配置管理已接入
- 会话创建接口可用
- 消息入库接口可用
- API 文档可通过 Swagger 查看

第一周完成后，虽然还没有完整 AI 问答能力，但应该已经具备“可以接着开发主链路”的工程基础。

---

## 2. 第一周开发边界

第一周只做基础设施和最小业务闭环，不进入复杂业务逻辑。

### 2.1 本周要做

- FastAPI 项目初始化
- 配置管理
- 日志体系
- 数据库建模
- Alembic 迁移
- Redis 接入
- 基础异常处理
- 请求链路追踪字段
- 会话创建接口
- 消息入库接口
- 健康检查接口

### 2.2 本周不做

- 不做 LLM 模型调用
- 不做知识库检索
- 不做工具调用
- 不做 SSE 流式生成
- 不做 WebSocket 长连接
- 不做复杂权限系统
- 不做后台管理页面

---

## 3. 第一周交付结果

第一周的交付物建议明确为以下几项：

- 一个可运行的后端仓库
- 一套清晰的项目目录结构
- 一组基础数据表和迁移脚本
- 一份 `.env.example`
- 一套基础 API
- 一份 README，说明如何本地启动

建议本周完成后，任何开发人员拿到仓库都能在本地完成：

1. 安装依赖
2. 启动 PostgreSQL、Redis
3. 执行数据库迁移
4. 启动 FastAPI 服务
5. 调用创建会话与发送消息接口

---

## 4. 推荐项目结构

第一周就要把结构搭对。不要一开始把所有逻辑塞到 `main.py` 里。

推荐目录如下：

```text
aibotchat/
  app/
    api/
      v1/
        __init__.py
        router.py
        health.py
        sessions.py
        messages.py
    core/
      __init__.py
      config.py
      logger.py
      exception_handlers.py
      middleware.py
      security.py
    db/
      __init__.py
      session.py
      base.py
      models/
        __init__.py
        tenant.py
        channel.py
        user.py
        session.py
        message.py
        message_event.py
      repositories/
        __init__.py
        session_repo.py
        message_repo.py
    schemas/
      __init__.py
      common.py
      session.py
      message.py
    services/
      __init__.py
      session_service.py
      message_service.py
    utils/
      __init__.py
      ids.py
      time.py
    tests/
      api/
        test_health.py
        test_sessions.py
        test_messages.py
      services/
    main.py
  alembic/
    versions/
  alembic.ini
  requirements.txt
  .env.example
  README.md
```

---

## 5. 项目结构说明

### 5.1 `app/api/v1`

用于放 API 路由层，只负责：

- 收请求
- 参数校验
- 调 service
- 返回统一响应

不要在这里写复杂业务逻辑。

建议第一周先包含：

- `health.py`
- `sessions.py`
- `messages.py`
- `router.py`

### 5.2 `app/core`

放系统级基础能力：

- 配置管理
- 日志
- 全局异常处理
- 中间件
- 鉴权占位逻辑

第一周最关键的是：

- `config.py`
- `logger.py`
- `exception_handlers.py`
- `middleware.py`

### 5.3 `app/db`

放数据库相关代码：

- SQLAlchemy Session
- Base Model
- 数据模型
- 仓储层

建议第一周开始就把 ORM 与 Repository 分开，不然后面会越来越乱。

### 5.4 `app/schemas`

放 Pydantic 请求/响应模型：

- 创建会话请求
- 创建会话响应
- 发送消息请求
- 统一响应结构

### 5.5 `app/services`

放业务服务层：

- `session_service.py`
- `message_service.py`

第一周这些 service 逻辑很简单，但这一层一定要先建立。

### 5.6 `app/utils`

放公共工具方法：

- 生成业务编码
- 时间格式处理
- trace_id 处理

### 5.7 `tests`

第一周就要建立测试目录，哪怕测试不多，也不要后面再补结构。

---

## 6. 技术实现建议

### 6.1 Web 框架

- `FastAPI`
- `uvicorn`

原因：

- 异步支持好
- Swagger 文档开箱即用
- 对后续 SSE、WebSocket 友好

### 6.2 ORM

- `SQLAlchemy 2.x`
- `Alembic`

原因：

- 后续扩展性好
- 数据迁移规范
- Python 后端团队普遍可维护

### 6.3 数据库

- `PostgreSQL`

原因：

- 后续可以接 `pgvector`
- 对 JSONB 支持好
- 适合客服中台这种结构化 + 半结构化数据混合场景

### 6.4 缓存

- `Redis`

第一周先完成连接和基础封装即可，后面再真正用于：

- 幂等
- 限流
- 在线会话态

### 6.5 配置管理

建议使用：

- `pydantic-settings`

环境变量至少包含：

```env
APP_NAME=aibotchat
APP_ENV=local
APP_HOST=0.0.0.0
APP_PORT=8000

POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=aibotchat
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

LOG_LEVEL=INFO
```

---

## 7. 第一周核心数据表

第一周不需要把所有表都建完，但建议先把最基础 5 张建好。

### 7.1 `tenants`

即便先做单租户，也建议保留。

### 7.2 `channels`

记录接入渠道，例如：

- `demo`
- `web`

### 7.3 `users`

记录终端用户标识。

### 7.4 `sessions`

记录会话主信息。

### 7.5 `messages`

记录消息内容。

如果你第一周时间足够，可以顺带补：

- `message_events`

但如果节奏紧，可以放到第二周。

---

## 8. 建模建议

### 8.1 `sessions` 最少字段

```text
id
tenant_id
channel_id
user_id
session_code
status
current_intent
summary
last_message_at
extra
created_at
updated_at
```

### 8.2 `messages` 最少字段

```text
id
tenant_id
session_id
message_code
role
message_type
content
content_json
reply_to_message_id
status
created_at
```

### 8.3 编码规范

建议业务编码独立生成，不直接把数据库自增 ID 暴露给前端。

例如：

- `session_code`: `s_202603260001`
- `message_code`: `m_202603260001`

---

## 9. 第一周 API 范围

第一周只做 3 类接口就够了。

### 9.1 健康检查

`GET /api/v1/health`

响应：

```json
{
  "status": "ok"
}
```

### 9.2 创建会话

`POST /api/v1/sessions`

请求：

```json
{
  "tenant_code": "demo_tenant",
  "channel": "demo",
  "external_user_id": "u_10001",
  "metadata": {
    "device_id": "d_001"
  }
}
```

响应：

```json
{
  "session_code": "s_202603260001",
  "status": "active",
  "created_at": "2026-03-26T10:00:00Z"
}
```

### 9.3 发送消息

`POST /api/v1/messages`

请求：

```json
{
  "tenant_code": "demo_tenant",
  "session_code": "s_202603260001",
  "message": {
    "type": "text",
    "content": "你好"
  },
  "request_id": "req_001"
}
```

第一周这个接口只需要完成：

- 校验 session 是否存在
- 把用户消息写入数据库
- 返回消息编号

响应：

```json
{
  "message_code": "m_202603260001",
  "role": "user",
  "status": "accepted"
}
```

注意，第一周不要求这个接口真正调模型。

---

## 10. 统一响应与异常处理

第一周一定要先定好统一响应风格，不然后面接口很容易乱。

### 10.1 成功响应建议

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

### 10.2 失败响应建议

```json
{
  "code": 40001,
  "message": "session not found",
  "data": null,
  "trace_id": "trace_xxx"
}
```

### 10.3 第一周至少处理这些异常

- 参数校验错误
- 数据库连接错误
- 资源不存在
- 未知系统异常

---

## 11. 中间件建议

第一周建议至少加 3 个中间件能力：

### 11.1 请求日志中间件

记录：

- 请求方法
- 请求路径
- 状态码
- 耗时
- trace_id

### 11.2 Trace ID 中间件

如果请求头里有 `X-Trace-Id`，优先使用；没有则自动生成。

后续所有日志、错误响应、链路埋点都复用这个值。

### 11.3 异常兜底中间件

确保所有未捕获异常都返回统一 JSON 格式。

---

## 12. 第一周详细开发计划

建议按 5 个工作日安排。

### Day 1：项目初始化

任务：

- 初始化 Git 仓库
- 初始化 Python 项目
- 安装 FastAPI、SQLAlchemy、Alembic、Redis 相关依赖
- 建立基础目录结构
- 编写 `main.py`
- 配置 API 主路由

当天产出：

- 服务可以启动
- `GET /api/v1/health` 可访问

### Day 2：配置与日志

任务：

- 编写 `config.py`
- 配置 `.env.example`
- 编写日志初始化逻辑
- 增加 request logging 中间件
- 增加 trace_id 中间件

当天产出：

- 不同环境配置可加载
- 日志输出包含 trace_id

### Day 3：数据库与迁移

任务：

- 配置 SQLAlchemy
- 配置 Alembic
- 建立基础模型
- 生成首个迁移脚本
- 本地执行迁移

当天产出：

- PostgreSQL 中成功建表
- 项目可连接数据库

### Day 4：会话接口

任务：

- 定义会话相关 schema
- 编写 `session_service`
- 编写 `session_repo`
- 实现 `POST /api/v1/sessions`

当天产出：

- 可以创建 session
- 自动初始化 tenant/channel/user/session 关系

注意：

如果当前还不做完整租户初始化，可以先简化为：

- tenant 预置一条默认数据
- channel 预置一个 `demo`

### Day 5：消息接口

任务：

- 定义消息相关 schema
- 编写 `message_service`
- 编写 `message_repo`
- 实现 `POST /api/v1/messages`
- 增加基础单元测试和接口测试
- 补 README

当天产出：

- 用户消息可写库
- API 文档完整
- 项目具备第一周验收条件

---

## 13. 第一周代码职责划分建议

### 13.1 `session_service.py`

职责：

- 校验 tenant/channel/user
- 创建或获取 user
- 创建 session
- 返回会话结果

### 13.2 `message_service.py`

职责：

- 校验 session 是否存在
- 生成消息编码
- 写入消息表
- 更新 session 的 `last_message_at`

### 13.3 `session_repo.py`

职责：

- 负责 session 表查询和写入

### 13.4 `message_repo.py`

职责：

- 负责 message 表查询和写入

原则是：

- API 层不直接操作 ORM
- Service 层不直接处理 HTTP Request

---

## 14. 第一周测试建议

第一周至少写下面几类测试。

### 14.1 `health` 接口测试

- 服务返回 200
- 返回值结构正确

### 14.2 `sessions` 接口测试

- 正常创建 session
- 缺少必要参数时报错

### 14.3 `messages` 接口测试

- 正常写入消息
- session 不存在时报错

### 14.4 service 层测试

- `create_session` 正常返回
- `create_message` 正常返回

---

## 15. 第一周验收标准

第一周结束时，建议按这份清单验收：

- 项目目录结构清晰，不是单文件工程
- 配置管理可通过环境变量加载
- PostgreSQL 可连接
- Redis 可连接
- Alembic 迁移可执行
- 健康检查接口可用
- 创建会话接口可用
- 消息入库接口可用
- Swagger 文档可访问
- 日志中包含 trace_id
- 基础异常响应统一
- README 可指导本地启动

---

## 16. 第一周潜在风险

### 16.1 结构过度设计

问题：

- 一开始拆太细，开发推进慢

建议：

- 保持“模块化单体”
- 先分层，不急着拆服务

### 16.2 表结构一次性设计过大

问题：

- 表太多，迁移频繁改动

建议：

- 第一周只做最基础表
- 第二周再补事件表和模型调用日志

### 16.3 API 设计过早耦合前端

问题：

- 接口只适配某个 Demo 页面

建议：

- 统一按中台风格设计
- 保持 session/message schema 稳定

---

## 17. 第一周结束后的状态

如果第一周按计划完成，那么到下周开始时，你应该已经具备：

- 一个稳定的 Python 后端基础工程
- 一套清晰的数据模型基础
- 两个核心业务入口：session 和 message
- 可以继续接入 LLM、RAG、Tool 的明确扩展点

也就是说，第二周就可以专注做真正的问答主链路，而不需要再反复返工基础工程。

---

## 18. 建议的下一份文档

第一周文档完成后，下一步最适合继续细化的内容有两份：

1. `第二周开发详情：问答主链路与 SSE 流式输出`
2. `PostgreSQL 建表 SQL + Alembic 初始化脚本设计`

如果你继续需要，我下一条可以直接补其中任意一份。
