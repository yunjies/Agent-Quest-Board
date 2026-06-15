# Release Manifests

本目录保存 Agent 委托公告板的 release manifest。

命名规则：

```text
{framework_release}.json
```

注意：

- `framework_release` 是工程发布版本。
- `board_protocol_version` 是协议版本。
- 正式 adapter 接入不必升级协议版本，除非 schema、状态机、权限或事件语义发生变化。
