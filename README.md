# RAG Demo01

一个前后端分离的 RAG 示例项目：

- `RAG/`：FastAPI 后端，负责知识库入库、检索、rerank 和对话
- `web/`：Vite + React 前端
- `storage/`：运行时数据目录（知识库、聊天历史、md5 索引）
- `scripts/`：初始化和启动脚手架

## 目录结构

```text
demo01/
├── RAG/                  # 后端源码
├── web/                  # 前端源码
├── scripts/              # 初始化 / 启动脚本
├── storage/              # 运行时数据（默认不提交）
├── .env.example          # 配置模板
├── requirements.txt      # 后端依赖
└── README.md
```

## 环境要求

- Python 3.11+
- Node.js 20+
- `npm` 或 `pnpm`

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd demo01
```

### 2. 初始化项目

```bash
python scripts/bootstrap.py
```

这个脚本会自动完成：

- 创建根目录 `.env`
- 创建 `.venv`
- 安装后端依赖
- 安装前端依赖
- 初始化 `storage/` 目录

### 3. 填写配置

打开根目录 `.env`，至少填写：

```env
DASHSCOPE_API_KEY=你的密钥
```

其他配置已经在 `.env.example` 中给出了默认值，可以按需调整。

## 启动项目

### 一键启动前后端

```bash
python scripts/dev.py
```

默认访问地址：

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- 健康检查：http://localhost:8000/health

### 分别启动

```bash
python scripts/start_backend.py
python scripts/start_frontend.py
```

## 配置说明

项目默认优先读取根目录 `.env`，同时兼容旧的 `RAG/.env`。

常用配置：

- `DASHSCOPE_API_KEY`：DashScope API Key
- `EMBEDDING_MODEL_NAME`：Embedding 模型
- `CHAT_MODEL_NAME`：聊天模型
- `RERANK_ENABLED`：是否开启 rerank
- `RERANK_MODEL_NAME`：rerank 模型名
- `RETRIEVE_TOP_K`：初始召回条数
- `RETRIEVAL_NEIGHBOR_CHUNKS`：命中 chunk 前后补充块数
- `PERSIST_DIRECTORY`：Chroma 数据目录
- `CHAT_HISTORY_DIRECTORY`：聊天历史目录
