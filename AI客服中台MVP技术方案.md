# AI 客服中台 MVP 技术方案

## 1. 目标与范围

### 1.1 MVP 目标
在 4 到 6 周内交付一个可运行的后端中台，满足以下能力：

- 提供统一客服问答入口
- 支持 `HTTP` 同步问答
- 支持 `SSE` 流式输出
- 可选支持 `WebSocket` 长连接问答
- 支持多轮会话管理
- 支持基础知识库检索问答
- 支持少量业务工具调用
- 保存完整对话、事件和调用日志
- 可供后续 Demo 页面快速接入

### 1.2 MVP 不做的内容
这阶段不要做太重的东西：

- 不做复杂多 Agent 自主规划
- 不做完整多租户 SaaS 能力
- 不做完整人工坐席系统
- 不做复杂工单流转
- 不做过早微服务化
- 不做复杂权限中心
- 不做高阶 BI 报表平台

### 1.3 成功标准
MVP 验收至少满足：

- 单次问答成功率高
- 多轮会话上下文可用
- 常见 FAQ 可通过知识库回答
- 部分业务问题可通过工具查询
- 回复可流式返回
- 对话过程可追踪、可回放、可排错

## 2. 总体架构

建议先采用“模块化单体 + 基础中间件”的方式，而不是一开始拆很多服务。

```text
Client / Demo / IM Adapter
        |
        v
   Access Layer
HTTP / SSE / WebSocket / Auth / Rate Limit
        |
        v
Conversation Orchestrator
Session / Context / Routing / Prompt Assembly
        |
   +----+----+------------------+
   |         |                  |
   v         v                  v
LLM Gateway  RAG Service        Tool Service
   |         |                  |
   +---------+------------------+
             |
             v
   PostgreSQL / Redis / Vector Store
             |
             v
   Logs / Metrics / Trace / Audit
```

## 3. 技术栈建议

### 3.1 后端框架
- `Python 3.11+`
- `FastAPI`
- `Uvicorn` / `Gunicorn`

### 3.2 数据存储
- `PostgreSQL`
  - 存用户、会话、消息、事件、工具调用记录、知识文档元数据
- `Redis`
  - 存在线会话状态、短期上下文缓存、幂等键、限流计数
- 向量检索
  - 初版建议 `pgvector`
  - 后期量大再迁 `Qdrant` 或 `Milvus`

### 3.3 异步与任务
- MVP 可先用 `FastAPI BackgroundTasks`
- 稍复杂后接 `Celery + Redis`

### 3.4 观测与治理
- 日志：结构化 JSON 日志
- 指标：`Prometheus`
- 可视化：`Grafana`
- Trace：`OpenTelemetry`

### 3.5 模型接入
建议抽象一层 `LLM Gateway`，不要业务代码直接绑死某个模型厂商。

统一支持：

- `chat completion`
- `stream chat`
- `embedding`
- 可选 `rerank`

## 4. 服务边界

MVP 阶段建议逻辑上分 5 个模块，代码可以先放在一个仓库里。

### 4.1 Access Gateway
职责：

- 提供统一 API 接口
- 支持 `REST / SSE / WebSocket`
- 请求鉴权
- 限流
- 渠道透传信息标准化
- 请求 ID、trace ID 注入

不负责：

- 不直接做 Prompt 拼接
- 不直接做知识检索
- 不直接做模型调用

### 4.2 Conversation Service
职责：

- 创建/读取 session
- 保存 message
- 维护对话上下文
- 生成 prompt
- 判断路由：FAQ / RAG / Tool / LLM
- 产出事件流

这是 MVP 的核心。

### 4.3 LLM Gateway
职责：

- 封装模型供应商 SDK
- 统一输入输出格式
- 支持流式与非流式
- 超时、重试、熔断
- 成本和耗时埋点

### 4.4 Knowledge Service
职责：

- 文档导入
- 文档切片
- embedding
- 索引构建
- 召回
- 重排
- 返回引用片段

### 4.5 Tool Service
职责：

- 统一业务工具协议
- 订单查询
- 物流查询
- 会员/账户查询
- 权限校验
- 工具返回结构标准化

## 5. 核心链路设计

### 5.1 问答主流程
1. 客户端发来消息
2. Access Gateway 做鉴权、限流、生成 trace_id
3. Conversation Service 校验 session
4. 保存用户消息
5. 执行意图识别与路由
6. 如果命中 FAQ/RAG，则检索知识
7. 如果需要工具，则调用 Tool Service
8. 拼装 prompt
9. 调用 LLM Gateway
10. 将生成内容流式回传
11. 保存 assistant message 与事件日志
12. 记录质量埋点与耗时

### 5.2 路由策略
MVP 不建议让模型完全自由决策，而是做规则优先：

- 规则命中 FAQ：直接 FAQ/RAG
- 命中业务查询类意图：走 Tool
- 命中高风险类：固定话术或转人工
- 其余：走 LLM 普通回答

### 5.3 高风险问题处理
以下问题应做特殊策略：

- 涉及退款金额、赔付承诺
- 涉及法律、医疗、金融建议
- 涉及用户隐私
- 涉及账号安全
- 无知识依据但模型倾向瞎编

策略：

- 不确定就降级回复
- 明确提示“建议人工处理”
- 留审计日志

## 6. 数据模型与表结构

下面给的是 MVP 够用的核心表。可以先从这些开始，不要一次建太多。

### 6.1 `tenants`
如果你目前只有单租户，也建议先留这个表，后面好扩展。

```sql
CREATE TABLE tenants (
    id BIGSERIAL PRIMARY KEY,
    tenant_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 6.2 `channels`
记录接入渠道。

```sql
CREATE TABLE channels (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    channel_code VARCHAR(64) NOT NULL,
    channel_type VARCHAR(32) NOT NULL,
    config JSONB,
    status SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

建议 `channel_type` 值：

- `demo`
- `web`
- `app`
- `wechat`
- `im`

### 6.3 `users`
这里是客服系统里的终端用户标识，不一定是内部账号。

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    external_user_id VARCHAR(128) NOT NULL,
    nickname VARCHAR(128),
    phone_masked VARCHAR(32),
    extra JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, external_user_id)
);
```

### 6.4 `sessions`
会话主表。

```sql
CREATE TABLE sessions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    session_code VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    current_intent VARCHAR(64),
    summary TEXT,
    last_message_at TIMESTAMP,
    extra JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

`status` 可取：

- `active`
- `closed`
- `handover`
- `expired`

### 6.5 `messages`
消息主表。

```sql
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    message_code VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(32) NOT NULL,
    message_type VARCHAR(32) NOT NULL DEFAULT 'text',
    content TEXT,
    content_json JSONB,
    reply_to_message_id BIGINT,
    token_count INT,
    model_name VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

建议字段说明：

- `role`: `user / assistant / system / tool`
- `message_type`: `text / event / tool_result`
- `content_json`: 用于结构化内容扩展

### 6.6 `message_events`
非常关键。流式输出不要只存在内存里，要能落库或至少落关键事件。

```sql
CREATE TABLE message_events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    message_id BIGINT,
    event_type VARCHAR(64) NOT NULL,
    event_seq INT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

建议 `event_type`：

- `message_received`
- `route_selected`
- `retrieval_started`
- `retrieval_finished`
- `tool_call_started`
- `tool_call_finished`
- `llm_started`
- `llm_delta`
- `llm_finished`
- `response_completed`
- `response_failed`

### 6.7 `knowledge_documents`
知识文档元数据。

```sql
CREATE TABLE knowledge_documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    doc_code VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(256) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_uri TEXT,
    category VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    version INT NOT NULL DEFAULT 1,
    extra JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 6.8 `knowledge_chunks`
文档切片。

```sql
CREATE TABLE knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(1536),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

如果 embedding 维度不同，按模型改。

### 6.9 `tool_call_logs`
工具调用日志。

```sql
CREATE TABLE tool_call_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    message_id BIGINT,
    tool_name VARCHAR(64) NOT NULL,
    request_payload JSONB,
    response_payload JSONB,
    status VARCHAR(32) NOT NULL,
    error_message TEXT,
    latency_ms INT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 6.10 `feedbacks`
用户反馈，可用于后续优化。

```sql
CREATE TABLE feedbacks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    rating SMALLINT,
    feedback_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## 7. Redis 设计建议

Redis 在 MVP 里主要做这些：

### 7.1 在线会话状态
Key 例子：

- `chat:session:{session_code}:state`
- `chat:session:{session_code}:context_cache`

### 7.2 幂等控制
- `chat:idempotent:{request_id}`

### 7.3 限流
- `rate_limit:{tenant}:{user}:{minute}`

### 7.4 WebSocket 连接映射
如果后面要支持主动推送：

- `ws:conn:{session_code}`

## 8. API 设计

API 设计目标是：后面无论接 Demo、Web、IM、App，消息结构尽量一致。

### 8.1 创建会话

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

### 8.2 发送消息

`POST /api/v1/messages`

请求：

```json
{
  "tenant_code": "demo_tenant",
  "session_code": "s_202603260001",
  "message": {
    "type": "text",
    "content": "我的订单什么时候到？"
  },
  "stream": true,
  "request_id": "req_001",
  "metadata": {
    "trace_id": "trace_abc"
  }
}
```

同步响应可分两种：

#### 非流式
```json
{
  "message_code": "m_10002",
  "role": "assistant",
  "content": "请提供您的订单号，我来帮您查询。",
  "finish_reason": "stop"
}
```

#### 流式
返回：

- `SSE`
- 或返回一个 `stream_url`

例如：

```json
{
  "message_code": "m_10002",
  "stream_url": "/api/v1/messages/stream?session_code=s_202603260001&message_code=m_10002"
}
```

### 8.3 SSE 流式输出

`GET /api/v1/messages/stream?session_code=...&message_code=...`

事件类型建议：

```text
event: start
data: {"message_code":"m_10002"}

event: retrieval
data: {"status":"started"}

event: delta
data: {"content":"您好，"}

event: delta
data: {"content":"我来帮您查询订单状态。"}

event: tool_call
data: {"tool_name":"order_query","status":"started"}

event: tool_result
data: {"tool_name":"order_query","status":"finished"}

event: done
data: {"finish_reason":"stop"}
```

### 8.4 WebSocket 问答

`WS /api/v1/ws/chat`

客户端发送：

```json
{
  "action": "chat",
  "tenant_code": "demo_tenant",
  "session_code": "s_202603260001",
  "request_id": "req_002",
  "message": {
    "type": "text",
    "content": "帮我查下订单 A123456"
  }
}
```

服务端推送：

```json
{
  "event": "delta",
  "message_code": "m_10003",
  "content": "正在为您查询订单信息"
}
```

结束事件：

```json
{
  "event": "done",
  "message_code": "m_10003",
  "finish_reason": "stop"
}
```

### 8.5 获取会话历史

`GET /api/v1/sessions/{session_code}/messages`

响应：

```json
{
  "session_code": "s_202603260001",
  "items": [
    {
      "message_code": "m_1",
      "role": "user",
      "content": "我的订单什么时候到？",
      "created_at": "2026-03-26T10:00:00Z"
    },
    {
      "message_code": "m_2",
      "role": "assistant",
      "content": "请提供订单号。",
      "created_at": "2026-03-26T10:00:02Z"
    }
  ]
}
```

### 8.6 导入知识文档

`POST /api/v1/knowledge/documents`

请求：

```json
{
  "title": "售后退货规则",
  "source_type": "text",
  "content": "签收后7天内可申请退货......",
  "category": "after_sale"
}
```

响应：

```json
{
  "doc_code": "doc_1001",
  "status": "processing"
}
```

### 8.7 触发知识索引构建

`POST /api/v1/knowledge/documents/{doc_code}/index`

响应：

```json
{
  "doc_code": "doc_1001",
  "status": "indexed"
}
```

### 8.8 用户反馈

`POST /api/v1/feedbacks`

请求：

```json
{
  "session_code": "s_202603260001",
  "message_code": "m_2",
  "rating": 1,
  "feedback_text": "没有回答到重点"
}
```

## 9. 内部模块接口建议

为了后面方便拆服务，内部接口最好先标准化。

### 9.1 Conversation -> LLM Gateway

```python
class ChatRequest(BaseModel):
    model: str
    system_prompt: str
    messages: list[dict]
    temperature: float = 0.2
    stream: bool = False
    metadata: dict | None = None
```

### 9.2 Conversation -> Knowledge Service

```python
class RetrieveRequest(BaseModel):
    tenant_id: int
    query: str
    top_k: int = 5
    categories: list[str] | None = None
```

### 9.3 Conversation -> Tool Service

```python
class ToolInvokeRequest(BaseModel):
    tool_name: str
    tenant_id: int
    session_id: int
    user_id: int
    arguments: dict
    trace_id: str
```

## 10. 项目目录建议

如果你准备后续真开工，Python 项目结构建议直接这样搭：

```text
app/
  api/
    v1/
      sessions.py
      messages.py
      ws.py
      knowledge.py
      feedback.py
  core/
    config.py
    logger.py
    security.py
    middleware.py
  db/
    base.py
    models/
      tenant.py
      user.py
      session.py
      message.py
      event.py
      knowledge.py
      tool_log.py
    repositories/
  schemas/
    common.py
    session.py
    message.py
    knowledge.py
    tool.py
  services/
    conversation/
      orchestrator.py
      context_manager.py
      router.py
      prompt_builder.py
    llm/
      base.py
      provider_x.py
    knowledge/
      ingest.py
      retriever.py
      reranker.py
    tools/
      registry.py
      order_query.py
      logistics_query.py
    streaming/
      sse.py
      websocket.py
  workers/
    tasks.py
  tests/
    api/
    services/
    integration/
  main.py
```

## 11. 开发排期

下面按 5 周给一个较实用的排期。一个人也能做，但要控制范围。

### 第 1 周：基础骨架
目标：把基础后端框架和主数据结构搭起来。

任务：

- 初始化 `FastAPI` 项目
- 配置 PostgreSQL、Redis
- 建核心表
- 接入 Alembic
- 完成日志、配置、异常处理、中间件
- 实现会话创建接口
- 实现消息入库接口

交付：

- 可创建 session
- 可保存 message
- 基础 API 可跑通

### 第 2 周：问答主链路
目标：打通从消息输入到模型输出的完整链路。

任务：

- 封装 LLM Gateway
- 实现 Conversation Orchestrator
- 支持上下文拼接
- 实现同步问答
- 实现 SSE 流式输出
- 落库 assistant 消息和 message_events

交付：

- Demo 可以完成多轮问答
- 可看到流式返回
- 对话日志可追踪

### 第 3 周：知识库能力
目标：让客服具备基于资料的回答能力。

任务：

- 实现文档导入
- 实现切片和 embedding
- 使用 `pgvector` 建索引
- 实现召回和基础重排
- 将知识片段注入 prompt
- 加“无依据兜底”策略

交付：

- FAQ/帮助文档可检索回答
- 低命中时不乱答

### 第 4 周：工具调用能力
目标：支持业务查询类客服问题。

任务：

- 定义 Tool 协议
- 接两个示例工具：
  - `order_query`
  - `logistics_query`
- 设计路由逻辑
- 实现工具调用日志
- 加错误处理与超时控制

交付：

- 客服可以回答一类真实业务问题
- 工具调用过程可追踪

### 第 5 周：治理与验收
目标：让系统具备试运行条件。

任务：

- 增加敏感词和高风险问题兜底
- 加基础限流
- 加 Prometheus 指标
- 增加反馈接口
- 增加基础测试
- 梳理部署方式和 README

交付：

- 一套可供 Demo 接入的 MVP
- 有最基本的稳定性与可观测性

## 12. 测试重点

MVP 阶段至少覆盖这些测试：

### 12.1 单元测试
- 上下文裁剪逻辑
- 路由逻辑
- Prompt 拼接逻辑
- 工具参数解析

### 12.2 集成测试
- 创建会话 -> 发消息 -> 收回复
- SSE 流式事件完整性
- 知识文档导入 -> 索引 -> 检索
- 工具调用成功/失败链路

### 12.3 回归测试
建议准备 30 到 50 条标准问答样本：

- FAQ 类
- 订单查询类
- 物流类
- 兜底类
- 高风险类

## 13. 关键风险与控制点

### 13.1 幻觉
风险：模型瞎编客服答案。  
控制：

- FAQ/RAG 优先
- 工具查询优先于生成猜测
- 无依据则兜底
- 高风险场景固定策略

### 13.2 成本过高
风险：上下文太长、模型太贵。  
控制：

- 限制上下文窗口
- 历史摘要
- FAQ 命中优先
- 普通问题走便宜模型，复杂问题再升级

### 13.3 延迟过高
风险：检索 + 工具 + 大模型叠加导致超时。  
控制：

- 路由前置
- 工具超时控制
- 并行做部分检索和预处理
- 流式先返回占位信息

### 13.4 后续难扩展
风险：接口设计过于面向单前端。  
控制：

- 统一 message schema
- 事件流标准化
- 渠道信息独立建模

## 14. MVP 验收清单

上线前建议按这份清单验收：

- 能创建会话
- 能多轮问答
- 能流式返回
- 能记录消息与事件
- 能接入一套知识库
- 能调用至少 2 个业务工具
- 能处理超时、错误、重试
- 能返回统一错误码
- 能输出基础监控指标
- 能被 Demo 客户端稳定接入

## 15. 第一版最小可交付配置

如果你现在就要开工，我建议第一版压缩到这套最小配置：

- `FastAPI`
- `PostgreSQL`
- `Redis`
- `pgvector`
- 1 个模型供应商
- 1 种流式方式：`SSE`
- 2 个业务工具：订单查询、物流查询
- 1 套知识库：FAQ/帮助中心文本
- 1 个 Demo 渠道

这套最利于尽快做出结果，也最容易验证架构是不是合理。

## 16. 下一步建议

如果你要继续推进，最合适的下一步不是再谈抽象架构，而是直接产出两份工程化文档：

1. `MVP 接口协议文档`
2. `数据库 ER 图 + 建表 SQL`

如果你愿意，我下一条可以直接继续给你这两样之一：

- 一份可直接交给开发的 `API 详细定义文档`
- 一份可直接落库的 `PostgreSQL 建表 SQL + 索引设计`

如果你希望更进一步，我也可以直接按这份方案给你起一个 `FastAPI` MVP 项目骨架。
