# PDF 解析改动说明

更新日期：2026-10-30。

本文记录本轮新增的解析器选择、解析预览、Docling 公式增强及验证结果。项目整体安装与启动方式见 [项目 README](../README.md)。

## 1. 当前功能

| 功能 | 当前行为 |
| --- | --- |
| PDF 解析器 | 上传页可选 pypdf 或 Docling，默认仍为 pypdf |
| pypdf | 保留原有逐页文本提取逻辑，无需安装 Docling |
| Docling | 输出带结构的 Markdown，开启公式增强 |
| 解析预览 | 展示完整文本、解析器和字符数，不向量化、不写入知识库 |
| 上传入库 | 使用与预览相同的解析入口，继续使用原有分块和知识库逻辑 |
| TXT / Markdown | 直接读取 UTF-8 文本，不走 PDF 解析器 |

这仍是两个可选解析器，并未实现“Docling 提取结构、pypdf 自动补齐公式”的混合解析。

## 2. 安装和配置 Docling

Docling 为可选依赖，版本在 `requirements-docling.txt` 固定为 `docling[vlm]==2.145.0`。建议使用独立 Python 环境，避免影响现有后端依赖。

在项目根目录的 PowerShell 执行（环境不存在时才需要创建）：

```powershell
python -m venv .venv-docling
& ./.venv-docling/Scripts/python.exe -m pip install -r requirements-docling.txt
```

在根目录 `.env` 中设置：

```dotenv
DOCLING_PYTHON=C:/path/to/RAGTool/.venv-docling/Scripts/python.exe
DOCLING_MODEL_CACHE=C:/path/to/huggingface-cache
```

迁移项目后需修改路径。两个配置留空时，分别使用后端当前 Python 和默认模型缓存。修改配置后重启后端。

首次解析可能需要联网下载模型；模型缓存完整后在本地推理，无需另起 Ollama 或其他 AI 模型服务。当前关闭远程推理服务、代码增强和图片描述增强；公式增强会增加耗时及资源占用。

## 3. 使用方法

1. 打开上传页，选择 PDF。
2. 选择 `pypdf` 或 `Docling`。
3. 点击“预览解析结果”，检查实际用于入库的文本。
4. 确认内容后，点击“上传到知识库”。

预览窗口目前展示原始文本或 Markdown，包括 LaTeX 源码，不直接渲染公式或图片。更换文件或解析器会使旧预览失效。

后端按 PDF 内容和解析器缓存最近四份解析结果，供预览和上传复用。缓存仅在当前进程内有效，重启或淘汰后需要重新解析。Docling 子进程在单个后端进程内串行执行，每次解析超时为 600 秒。

## 4. 公式增强与回退

`RAG/app/utils/docling_worker.py` 设置：

```python
options.do_formula_enrichment = True
```

识别成功的公式由 Docling 导出为 `$$ ... $$` 包围的 LaTeX。若增强结果为空，但 PDF 中仍有原始公式文字，导出会保留这些文字并标注“未恢复数学排版”；若两者均为空，会明确提示查看原文，避免只留下难以理解的占位符。

原始文字回退不是 LaTeX 重建，也不能保证上下标、分式或矩阵布局正确。公式增强同样可能误识别符号或产生不完整结构，科研使用前需对照 PDF 核查。

## 5. 论文验证结果

使用一篇论文进行验证，共提取 **102 条 LaTeX 公式**，其中 **100 条通过排版转换检查，2 条因 LaTeX 结构错误未能渲染**，可渲染比例约为 **98.0%**。

该结果统计的是 LaTeX 排版转换成功率，不代表数学内容识别准确率；未做逐条人工校订。

## 6. 接口变化

| 接口 | 请求 | 作用 |
| --- | --- | --- |
| `POST /api/v1/upload/preview` | multipart：`file`、`parser` | 仅返回解析内容，不调用知识库写入 |
| `POST /api/v1/upload` | multipart：`file`、`parser` | 解析后走原有入库流程 |

`parser` 可选 `pypdf` / `docling`，省略时默认 `pypdf`，兼容原调用方。预览响应包含 `filename`、`parser`、`format`、`text`、`characters`；TXT / Markdown 的实际解析器标识为 `text`。上传响应增加实际解析器信息。

Docling 环境不可用或未安装时返回 503；解析失败返回 422；解析超时返回 504。错误会在前端展示，可根据提示检查环境、模型下载连接或改用 pypdf。

## 7. 主要改动文件

| 文件 | 改动 |
| --- | --- |
| `RAG/app/utils/file_reader.py` | 统一解析入口、解析器分支、PDF 内存缓存、线程池调用 |
| `RAG/app/utils/docling_reader.py` | 独立解释器调用、临时文件、串行锁、超时及错误处理 |
| `RAG/app/utils/docling_worker.py` | Docling 转换、公式增强及空公式回退 |
| `RAG/app/api/v1/endpoints/upload.py` | 预览接口、上传解析器参数 |
| `RAG/app/schemas/upload.py` | 预览响应和上传解析器字段 |
| `RAG/app/core/config.py`、`.env.example` | 可选解释器和模型缓存配置 |
| `requirements-docling.txt` | 可选 Docling 依赖 |
| `web/src/api/upload.ts` | 解析器类型、预览请求、错误处理 |
| `web/src/pages/UploadPage/` | 解析器选择、预览弹窗及对应样式 |
| `web/src/index.css` | 移除无法解析的 `@heroui/styles` 导入 |


## 8. 当前分块方法

解析后的文本统一交给 `SemanticTextSplitter`（`RAG/app/utils/semantic_chunker.py`），由 `RAG/app/services/knowledge_base.py` 在入库时调用。pypdf 和 Docling 共用这一流程，预览仅展示解析结果，不执行入库分块。

当前采用基于段落、标题、列表和句子边界的规则分块。虽然类名包含 Semantic，但分块阶段没有调用大模型或使用 Embedding 相似度判断语义边界；Embedding 在分块完成后用于向量化入库。

### 默认参数

以下是代码默认值，实际运行可由配置覆盖。长度按 Python `len()` 计算，是字符数，不是 token 数。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `max_spliter_char_num` | 1000 | 文本长度严格超过此值才执行分块，否则整篇作为一个块 |
| `chunk_size` | 1000 | 分块目标长度，合并时计入单元间的换行符 |
| `chunk_overlap` | 100 | 相邻块重叠的目标字符数，不保证恰好重叠 100 字符 |
| `separators` | `\n\n`、`\n`、`.`、`!`、`?`、`。`、`！`、`？`、空格、空字符串 | 超长文本递归切分时按此顺序尝试边界，最后可按字符切分 |

### 分块流程

1. **判断是否需要切分**：超过长度阈值才进入分块器，短文本直接入库。
2. **整理换行**：统一换行符，将连续三个及以上换行压缩为两个，去掉首尾空白。
3. **提取文本单元**：按空行分段；Markdown 标题、中文编号、数字编号、项目列表及部分“第几章/节”等行单独形成单元。普通连续行保留在同一段中。
4. **拆分超长段落**：先按中文句号、中英文问号、感叹号、分号等句子边界拆分；英文句点在其后有空白且下一句以大写字母、数字或引号开始时作为边界。再按长度合并句子。单句仍过长或无法识别句子边界时，使用 LangChain 的 `RecursiveCharacterTextSplitter` 兜底。
5. **合并单元与重叠**：按原文顺序合并，单元之间用两个换行连接。加入下一个单元会超过目标长度时，先输出当前块，再尝试携带当前块末尾的完整单元作为重叠。
6. **向量化并保存**：各块带上来源文件名、文档标识及从 0 开始的 `chunk_index` 等元数据，由 Embedding 转为向量后写入 Chroma。

重叠按完整单元累计，达到目标字符数后停止，因此可能超过 `chunk_overlap`。若重叠单元与下一个单元合并后超过 `chunk_size`，会舍弃这一层的重叠；递归兜底切分也会使用配置的重叠参数。

### 结构与公式的处理边界

Docling 的 Markdown 标题、段落等结构可以帮助规则识别文本单元，但当前分块器不读取 Docling 的结构化文档树，也不按 PDF 页码切分。标题单独识别后仍参与长度合并，不保证始终与后文绑定。

当前没有针对 `$$ ... $$` 公式、表格或代码块的完整性保护。较短公式通常随所在段落保留，超长公式仍可能被切开；不能把“公式解析成功”视为“入库后公式一定完整”。

检索时还可按 `chunk_index` 补充同一文档的相邻块，`retrieval_neighbor_chunks` 默认值为 2，即命中块前后各最多补充 2 块。这属于检索阶段的上下文扩展，与入库时的重叠分块是两个步骤。

## 9. 其他验证记录

实现期间，上传解析相关 6 项测试、Docling 公式导出相关 3 项测试均通过，前端生产构建通过。验证覆盖原有 pypdf 行为、预览不写入知识库、缓存复用、错误处理以及公式内容为空时的回退逻辑。

上述记录为实现期间的检查结果，本次文档整理未重新运行测试。
