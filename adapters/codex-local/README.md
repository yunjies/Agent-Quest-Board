# Codex Local Adapter｜Codex 本地甲方适配器

Codex local adapter 用于本地 Codex 甲方工作流。

当前范围是生成标准委托任务 JSON。它不默认写入真实 AgentOps 实例，也不包含任何个人路径、密钥或真实平台 ID。

## 示例

```bash
python adapters/codex-local/codex_principal.py \
  --title "Implement board adapter smoke test" \
  --description-file task.md \
  --principal-id principal-codex-pc \
  --contractor-id contractor-duoduo \
  --board-id board-duoduo \
  --acceptance-test "Unit tests pass" \
  --acceptance-test "Result file contains smoke evidence" \
  --output out/task.json
```

生成的 JSON 可以交给实现了 `publish_task` 的公告板适配器。

## 边界

- 不要求仓库配置 API key。
- 不写入真实本地路径。
- 不绕过公告板直接关闭任务。
