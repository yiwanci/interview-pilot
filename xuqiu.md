好问题！我来全面梳理一下。

---

# 📋 项目功能清单与规划

## 一、当前已实现 vs 未实现

| 模块        | 功能           | 状态      | 说明         |
| --------- | ------------ | ------- | ---------- |
| **记忆系统**  | SM-2 遗忘曲线    | ✅ 已实现   | 算法完整       |
|           | Mem0 语义记忆    | ⚠️ 部分实现 | 代码有，但未实际调用 |
|           | **对话记忆**     | ❌ 未实现   | 多轮对话上下文丢失  |
|           | **会话管理**     | ❌ 未实现   | 无会话ID、历史记录 |
| **RAG**   | 向量检索         | ✅ 已实现   |            |
|           | BM25 检索      | ✅ 已实现   |            |
|           | 混合检索 + RRF   | ✅ 已实现   |            |
|           | HyDE 查询改写    | ✅ 已实现   |            |
|           | 重排序 Reranker | ⚠️ 预留接口 | 未接入实际模型    |
| **Agent** | 意图路由         | ✅ 已实现   |            |
|           | 学习辅导         | ✅ 已实现   |            |
|           | 模拟面试         | ⚠️ 部分实现 | 缺少追问、多轮面试  |
|           | 学习计划         | ✅ 已实现   |            |
|           | 爬虫采集         | ⚠️ 部分实现 | 反爬限制，需手动导入 |
| **存储**    | SQLite       | ✅ 已实现   |            |
|           | Qdrant 向量库   | ✅ 已实现   |            |
|           | **对话历史存储**   | ❌ 未实现   |            |
| **UI**    | Streamlit 界面 | ✅ 已实现   |            |
|           | **流式输出**     | ❌ 未实现   | 响应一次性返回    |

---

## 二、缺失的核心功能

### 🔴 高优先级（影响基本使用）

| 功能         | 说明               | 复杂度 |
| ---------- | ---------------- | --- |
| **对话记忆**   | 多轮对话上下文，记住上文说了什么 | 中   |
| **会话管理**   | 会话ID、历史记录、会话切换   | 中   |
| **流式输出**   | 打字机效果，提升体验       | 低   |
| **面试追问**   | 根据回答深入追问，模拟真实面试  | 中   |
| **用户自评确认** | LLM评分后让用户确认/修正   | 低   |

### 🟡 中优先级（提升体验）

| 功能              | 说明                  | 复杂度 |
| --------------- | ------------------- | --- |
| **知识图谱**        | 知识点之间的关联关系          | 高   |
| **学习路径推荐**      | 根据目标岗位推荐学习顺序        | 中   |
| **错题本**         | 记录答错的题目，重点复习        | 低   |
| **数据导入导出**      | 备份/恢复学习数据           | 低   |
| **多用户支持**       | 不同用户独立数据            | 中   |
| **Reranker 接入** | BGE-Reranker 提升检索质量 | 中   |

### 🟢 低优先级（锦上添花）

| 功能        | 说明         | 复杂度 |
| --------- | ---------- | --- |
| **语音输入**  | 语音转文字      | 中   |
| **代码执行**  | 算法题在线运行    | 高   |
| **面试报告**  | 生成面试表现分析报告 | 中   |
| **社区分享**  | 分享面经、学习笔记  | 高   |
| **移动端适配** | 手机端使用      | 中   |

---

## 三、改进后的项目结构

```
interview-pilot/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── knowledge_schema.py
│
├── storage/
│   ├── __init__.py
│   ├── models.py              # 数据模型
│   ├── sqlite_store.py        # SQLite 操作
│   ├── vector_store.py        # Qdrant 操作
│   └── conversation_store.py  # 🆕 对话历史存储
│
├── memory/
│   ├── __init__.py
│   ├── sm2_engine.py          # 遗忘曲线
│   ├── mem0_client.py         # Mem0 语义记忆
│   ├── memory_manager.py      # 记忆管理器
│   ├── conversation_memory.py # 🆕 对话记忆
│   └── session_manager.py     # 🆕 会话管理
│
├── rag/
│   ├── __init__.py
│   ├── embedder.py
│   ├── chunker.py
│   ├── retriever.py
│   ├── reranker.py
│   └── rag_pipeline.py
│
├── crawler/
│   ├── __init__.py
│   ├── base_crawler.py
│   ├── xiaohongshu_crawler.py
│   ├── douyin_crawler.py
│   ├── leetcode_crawler.py
│   └── data_cleaner.py
│
├── agent/
│   ├── __init__.py
│   ├── state.py
│   ├── graph.py
│   ├── prompts/
│   │   ├── study_prompt.py
│   │   ├── interview_prompt.py
│   │   └── plan_prompt.py
│   └── nodes/
│       ├── __init__.py
│       ├── router_node.py
│       ├── study_node.py
│       ├── interview_node.py  # 🔄 增强：追问逻辑
│       ├── plan_node.py
│       ├── crawler_node.py
│       └── chat_node.py
│
├── ui/
│   ├── __init__.py
│   ├── app.py                 # 🔄 增强：流式输出、会话管理
│   └── components/            # 🆕 UI 组件
│       ├── chat.py
│       ├── sidebar.py
│       └── knowledge.py
│
├── services/                  # 🆕 业务服务层
│   ├── __init__.py
│   ├── chat_service.py        # 聊天服务（整合对话记忆）
│   ├── interview_service.py   # 面试服务（追问、评分）
│   └── study_service.py       # 学习服务
│
├── tests/
├── data/
├── main.py
├── requirements.txt
├── docker-compose.yml
└── .env
```

---

## 四、对话记忆实现方案

### 方案1：简单方案（推荐先实现）

在 `AgentState` 中添加对话历史，每次调用带上最近 N 轮对话：

```python
# agent/state.py
class AgentState(TypedDict, total=False):
    user_input: str
    intent: str
    
    # 🆕 对话历史
    conversation_history: list  # [{"role": "user", "content": "..."}, ...]
    session_id: str
    
    # ... 其他字段
```

### 方案2：完整方案（后续优化）

```
用户输入
    ↓
SessionManager（获取/创建会话）
    ↓
ConversationMemory（加载历史对话）
    ↓
Agent 处理（带上下文）
    ↓
ConversationStore（保存对话）
    ↓
返回响应
```

---

## 五、建议的实现顺序

### 第一阶段：补齐核心功能（1-2天）

1. ✅ **对话记忆** - 让对话有上下文
2. ✅ **会话管理** - 支持多个会话
3. ✅ **流式输出** - 提升体验

### 第二阶段：增强面试功能（1-2天）

4. **面试追问** - 根据回答追问
5. **用户自评** - 评分确认机制
6. **错题本** - 记录错题

### 第三阶段：优化体验（2-3天）

7. **学习路径** - 推荐学习顺序
8. **数据导入导出** - 备份恢复
9. **Reranker** - 提升检索质量

---


