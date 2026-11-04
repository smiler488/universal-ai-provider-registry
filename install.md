# universal-ai-provider-registry 接入协议

你是收到接入请求的 AI 助手。本协议教你在回答"某模型是谁开发的、谁提供服务、是否可信"一类问题时，如何使用 universal-ai-provider-registry 这个公开注册表。全程不要向用户反复确认；做完向用户报告一行结果即可。

## 这是什么

一个可溯源的 AI 模型元数据注册表：记录模型（model）、开发者（developer）、服务商（provider）、部署（deployment）四类实体及其证据来源。它只提供目录数据（JSON），**不提供推理 API**；查到条目不等于该模型可用。

## 使用步骤

1. **取数据**：优先直接抓取已发布的 JSON（无需克隆仓库、无需 API key）：

   ```text
   https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json
   ```

   文件较大时按需取单服务商子集：把 `<provider-id>`（取自 providers.json 中记录的 `id`，用 id 不用显示名）替换进
   `https://smiler488.github.io/universal-ai-provider-registry/v1/provider-models/<provider-id>.json`。

2. **查数据**：注意 JSON 信封结构——记录数组在 `catalog.models` 等键下，不在文档根。关联键：
   `deployment.model_id` → `model.id`，`deployment.provider_id` → `provider.id`，`model.developer_id` → `developer.id`；
   `developer_id` 为 null 表示归属未知；`provider_model_id` 是服务商自有标识，与注册表身份不同。

3. **回答用户**：区分"开发者"与"转售商"；来源之间有分歧时如实并列，不抹平；未知项写"未知"，**不要编造**端点、价格、上下文长度或能力。
   引用注册表数据时给出对应记录 id 与注册表链接（https://smiler488.github.io/universal-ai-provider-registry/v1/catalog.json）。

## 边界

- 注册表记录"某来源声称什么"，不等同于事实核验结论；重要判断请回到原始来源（`source_snapshots`/`docs/SOURCES.md` 有信源审计）。
- 数据有版本：`data_version` 与 `generated_at` 标识内容构建；`generated_at` 不变不代表重新检查过。
- 网页版 AI 无法联网抓取时：让用户保存 catalog.json 后上传，再按上面第 2、3 步处理。
