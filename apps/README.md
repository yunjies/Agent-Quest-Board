# Apps｜应用层

`apps/` 只放可运行应用和接入编排，不放协议规则和引擎逻辑。

应用层可以引用：

```text
packages/*
adapters/*
examples/*
```

应用层不应该反向污染：

```text
protocol/
packages/board-core/
```

## 三类应用

```text
principal/        甲方实现
contractor/       乙方实现
board-interface/  公告板前端 interface 接入
```

## 边界

- 甲方应用负责开单、验收、评分。
- 乙方应用负责接单、执行、提交、返工。
- 公告板前端 interface 负责展示、通知、话题/面板同步。
- 公告板核心状态、权限、事件和关闭规则仍由引擎层提供。

真实配置不得提交到仓库。使用 `config.example.yaml` 作为模板，真实配置放到本地部署目录或环境变量。
