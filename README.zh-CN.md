# Hermes Codex Search

[English](README.md) | [Tiếng Việt](README.vi.md) | 简体中文

> 本译文可能落后于英文版。如有出入，以 [README.md](README.md) 为准。

一个仅用于搜索的 Hermes Agent 后端，对接兼容 Codex 的独立网页搜索端点。

## 这是 `web_search` 的后端插件

本仓库**不会**添加 `codex_web` 工具。它为 Hermes 现有的 `web_search` 工具注册一个名为
`codex` 的 provider：

```text
Hermes web_search -> provider: codex -> /v1/alpha/search
```

当你希望 Hermes 普通的 `web_search` 调用经由兼容 Codex 的搜索端点，同时保持 Hermes
原有搜索工具的形态时，使用本插件。它不提供 `open`、`find`、`click`、PDF 截图或页面内容提取。

如需这些 Codex 风格的高级命令，请改用
[Hermes Codex Web](https://github.com/duu261/hermes-codex-web)。那是一个单独的独立工具插件，
注册的是 `codex_web`；它不是搜索后端。

## 它做什么

Hermes 保持主模型不变，照常调用 `web_search` 工具。本插件将查询发送到 `/v1/alpha/search`，再把结构化的搜索结果返回给同一个 Hermes 模型。它不生成回答，也不提供页面内容提取。

该端点要求提供 `model` 字段。默认值为 `gpt-5.6-sol`；当网关使用其他兼容模型时，可用 `CODEX_SEARCH_MODEL` 覆盖。该字段用于标识搜索请求，以便路由和计费，不会额外启动一轮模型生成。

## 安装

将本仓库安装为 Hermes 插件并启用，然后重启将要使用它的 Hermes 界面：

```bash
hermes plugins install <repository-url> --enable
```

在 Hermes 的私有环境文件中设置端点和凭据：

```text
CODEX_SEARCH_BASE_URL=https://gateway.example/v1
CODEX_SEARCH_API_KEY=replace-me
# Optional:
CODEX_SEARCH_MODEL=gpt-5.6-sol
```

base URL 必须包含 `/v1`；插件会追加 `/alpha/search`。切勿提交凭据。

远程端点必须使用 HTTPS。明文 HTTP 只接受在 `localhost`、`127.0.0.1` 或 `::1` 上进行本地开发。
适配器会拒绝 URL 中嵌入的凭据，拒绝重定向，限制响应体大小，并丢弃没有有效 HTTP(S) URL 的结果行。

## 只切换搜索后端而不改变提取后端

按能力分别设置后端：

```yaml
web:
  search_backend: codex
  extract_backend: firecrawl
```

或者在 Hermes 的 Web Search 设置中，为本 provider 选择 **Use for Search**，并单独为某个提取 provider 选择 **Use for Extract**。

## 开发

测试只使用 Python 标准库和模拟的 HTTP 响应：

```bash
python -m unittest discover -s tests -v
```

本插件基于 Hermes 公开的 `WebSearchProvider` 扩展点。它不修改 Hermes 核心，也不替换内置的 `web_search` 工具。
