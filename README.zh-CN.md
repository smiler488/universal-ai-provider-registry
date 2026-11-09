# Universal AI Provider Registry

[English](README.md) | 中文

一个保留证据来源的公开注册表，记录 AI 模型、模型开发者、服务商以及各服务商上的部署。它导入公开的模型目录，把来源之间的分歧和未知项如实保留，校验后的 JSON 通过 GitHub Pages 发布。整个过程不需要任何模型 API key，也不需要付费调用。

聚合平台的列表常常把模型合并或改名却不加说明，"这个模型是谁开发的？这个服务商是原厂还是转售？"这类问题因此很难回答。在这个注册表里，每条说法都附带出处链接；没有文档依据的内容一律标记为"未知"，而不是去猜。

仓库：[smiler488/universal-ai-provider-registry](https://github.com/smiler488/universal-ai-provider-registry) · [Actions](https://github.com/smiler488/universal-ai-provider-registry/actions) · [来源与许可审计](docs/SOURCES.md)

## 交给 AI 助手

把下面这句话发给能联网的 AI 助手（WorkBuddy、Claude Code、Codex 或带浏览功能的网页版助手），它就知道怎么查询这个注册表：

```text
请根据 https://raw.githubusercontent.com/smiler488/universal-ai-provider-registry/main/install.md，使用 universal-ai-provider-registry 查询模型出处。
```

面向 AI 助手的接入协议在 [install.md](install.md) 里：该取哪个 JSON、记录之间怎么关联、哪些内容不能编造。

## 获取数据

**从 [catalog.json](https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json) 开始。** 这一个文件就包含完整的注册表，不需要克隆仓库，也不需要 GitHub 账号或 API key：

```sh
curl --fail --location \
  https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json \
  --output catalog.json
```

这只是模型元数据目录，不运行模型，也不提供推理接口。要调用某个模型，仍然需要该服务商自己的服务、凭证和使用条款；注册表里有这一条，不代表你的账号一定能调用成功。

只想要某一家服务商的数据时，先打开 [providers.json](https://smiler488.github.io/universal-ai-provider-registry/v1/providers.json)，在 `providers` 数组里找到这家服务商，复制它的 `id`（注意是 id，不是显示名称），替换进 `https://smiler488.github.io/universal-ai-provider-registry/v1/provider-models/<provider-id>.json`。

程序读取时要注意：JSON 外面有一层"信封"，`data_version` 等元数据和记录数组放在同一层，所以模型列表在 `catalog.models` 下，而不是在文档根部。关联方式是：`deployment.model_id` → `model.id`，`deployment.provider_id` → `provider.id`，`model.developer_id` → `developer.id`。`developer_id` 为 null 表示开发者未知。`provider_model_id` 是服务商自己的模型标识，和注册表里的模型身份不是一回事。

## 公开的 JSON

| 地址 | 内容 |
| --- | --- |
| [catalog.json](https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json) | 完整目录，含开发者和来源 |
| [models.json](https://smiler488.github.io/universal-ai-provider-registry/v1/models.json) | 模型身份 |
| [developers.json](https://smiler488.github.io/universal-ai-provider-registry/v1/developers.json) | 已知的模型开发者 |
| [providers.json](https://smiler488.github.io/universal-ai-provider-registry/v1/providers.json) | 提供模型服务的机构或平台 |
| [deployments.json](https://smiler488.github.io/universal-ai-provider-registry/v1/deployments.json) | 各服务商上的具体模型及来源记录 |
| [schema.json](https://smiler488.github.io/universal-ai-provider-registry/v1/schema.json) | 校验用的 JSON Schema |

`generated_at` 标识的是内容的构建时间：如果后来的抓取没有发现任何变化，它保持不变，所以不能把它当成"最后检查时间"。抓取和发布状态请看最近一次成功的 Actions 运行记录。

示例客户端：[Python](examples/read_catalog.py)、[JavaScript](examples/read_catalog.mjs)、[shell](examples/read_catalog.sh)，下载到本地就能运行，只读取公开元数据。

## 数据约定

| 实体 | 含义 |
| --- | --- |
| `model` | 模型身份；暂时无法确认的身份只在来源服务商范围内有效 |
| `developer` | 已知的模型开发机构；不清楚就保持 `null` |
| `provider` | 提供模型访问的机构或服务 |
| `deployment` | 某服务商上的某个模型，保留上游的原始说法 |

- 不会因为某个服务商托管了某个模型，就推断它是开发者。
- 跨服务商合并同一个模型，必须有上游给出的精确 `canonical_model_id`，或经过人工审核的官方对应关系；名字相似不算证据。
- `data_version` 以 `sha256-` 开头，标识数据内容，和 `schema_version` 相互独立。只是抓取时间变了，不会生成新的内容版本。分别下载多个文件时，要核对它们的 `data_version` 是否一致。
- `diff.json` 比较当前发布和上一版。`updated` 列出事实发生变化的记录，`provenance_only` 列出只有来源版本变了、事实没变的记录。
- 未知本身就是有意义的数据。能力分为 `supported`、`unsupported`、`unknown`：来源之间有矛盾就记为 `unknown`，并写进 `conflicts`。`supported` 只表示有来源这样声称或有文档记载，不代表实际调用测试通过。价格为 0 可能表示包含在订阅里，也可能只是占位值；`zero_requires_verification` 绝不能解读为"已确认免费"。

## 数据来源

注册表导入 [Models.dev 完整 API](https://models.dev/api.json?type=all)、它的[完整目录](https://models.dev/catalog.json?type=all)、OpenClaw Catalog V2，以及经人工审核的官方文档中的部分事实。Models.dev 的两份导出来自同一个上游，不能算两个独立来源互相印证。具体的来源地址、许可情况、署名要求和局限都写在 [docs/SOURCES.md](docs/SOURCES.md)。

[人工审核证据文件](data/reviewed-evidence.json) 保存了带日期的事实记录和原始文档链接。

## 构建与校验

需要 Python 3.11 或更高版本：

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m registry sync        # 抓取、规范化并校验，输出到 public/v1/
python -m registry validate
python -m unittest discover -s tests
```

不重新抓取、只用已提交的源数据快照重建：

```sh
python -m registry build
python -m registry validate
```

不要手动修改生成出来的 JSON，应该去改导入代码或审核证据文件，然后重新构建。贡献规则见 [AGENTS.md](AGENTS.md)。

## 自动化

GitHub Actions 每天 UTC 00:23、06:23、12:23、18:23 自动同步，也可以在 **Actions → Sync and publish registry → Run workflow** 手动触发。抓取或校验失败时会停止发布，并保留上一版。需要可下载的归档时，在 `main` 分支上运行 **Actions → Release immutable data snapshot**，它会生成一个按内容寻址的 `data-…` release，里面有 ZIP 包和 `SHA256SUMS`。

GitHub 的定时任务可能会延迟；公开仓库连续 60 天没有活动时，定时任务可能会被自动停用。所以这是一个尽力而为的更新服务，不保证永久无人值守地运行。

## 许可与版本

原创代码和文档采用 [MIT 许可](LICENSE)。导入的内容保留上游的署名和适用条款，本仓库的许可证不会改变第三方数据或文档的授权，转发源数据之前请先阅读 [docs/SOURCES.md](docs/SOURCES.md)。版本变化见 [CHANGELOG.md](CHANGELOG.md)。项目名里的 "universal" 不代表覆盖了所有模型，也不代表实时更新。

维护者：邓良超（Liangchao Deng）。
