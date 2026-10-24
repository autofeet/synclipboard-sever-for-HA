# SyncClipboard Server for Home Assistant

Unofficial Home Assistant OS application packaging for [Jeric-X/SyncClipboard](https://github.com/Jeric-X/SyncClipboard).

为 Home Assistant OS 提供 SyncClipboard 服务端，支持跨设备剪贴板同步。手机、电脑仍需安装和配置 SyncClipboard 兼容客户端。

仓库地址：`https://github.com/autofeet/synclipboard-sever-for-HA`

## 安装

1. 在 Home Assistant 的“设置 → 应用 → 安装应用 → 菜单 → 仓库”添加本 GitHub 仓库的网页地址。
2. 安装 **SyncClipboard Server**。
3. 在“配置”设置独立的用户名和至少 16 字符密码，然后启动。
4. 客户端服务端地址填写 `http://你的HA局域网IP:5033`，使用上述账号密码。

目前支持 **amd64**，由 HA 在设备上构建。未验证其他架构。初始密码为空，服务会拒绝启动，必须先配置密码。

默认不开机启动。验证客户端连接后，可自行打开“开机启动”和“自动更新”。HTTP 端口仅用于可信局域网；本仓库不创建公网入口或配置 TLS。

## 自动更新是如何工作的

- GitHub Actions 每天约 UTC 02:23（上海时间 10:23）检查官方 `jericx/syncclipboard-server:latest` 的摘要；GitHub 可能延迟执行。
- 发现变化时，更新候选 Dockerfile 的固定摘要并递增加载项版本。
- 在临时容器中验证空密码拒绝启动、无凭据及错误凭据被拒绝、正确凭据可访问、中文文本读写与更换容器后数据保留。
- 全部验证通过才提交新版本到 `main`；失败则不发布，详见 Actions 日志。
- HA 刷新仓库后发现新版本。打开 HA 的“自动更新”后，Supervisor 按自身更新机制安装。

本仓库不修改 HA 的更新检查频率，不在 HA 上运行额外的定时检查。GitHub 中的验证不等于每一台 HA 主机的完整兼容性验证。

## 维护和故障处理

在 Actions 页面可手动运行 **Validate app** 和 **Maintain upstream**。首次发布需要确认工作流成功。维护工作流需要此仓库的 `contents: write` 权限；仓库规则若阻止机器人提交，则不会发布。

即使上游未变化，每 28 天也会重新运行容器验证，成功后提交 `maintenance.json` 维护记录，保持可核查的运行证据与仓库活动。GitHub 可能在公开仓库连续 60 天无活动后停用定时工作流；如果验证持续失败、工作流被暂停或平台中断，仍需所有者检查 Actions 并重新启用。工作流失败通知由 GitHub 账户的通知设置控制。本项目无法保证上游或平台变化后永远无需人工处理。

主版本由应用包维护，`upstream.json` 记录实际服务版本与不可变摘要。上游变化后只发布通过当前测试的候选版本；重大协议或存储格式变化仍可能需要人工适配。

## 从本地加载项迁移

本地加载项与 GitHub 仓库应用在 HA 中有不同标识，添加仓库不会自动接管原应用。

迁移前备份原应用和数据。新应用先设置其他端口，验证后停止旧应用，再把账号配置与数据迁到新应用的独立数据目录，最后切换回所需端口。验证完成前保留旧应用与备份。不要同时让两个容器写入同一数据库。单纯卸载并重装会丢失未备份的数据。

## 开发验证

```sh
python3 -m unittest discover -s tests -v
sh -n syncclipboard_server/run.sh
docker build --pull -t syncclipboard-ha:test syncclipboard_server
python3 scripts/verify.py --image syncclipboard-ha:test
```

测试使用随机临时凭据与临时数据目录，不读取 HA 或客户端的真实剪贴板。

## 许可证与来源

本仓库的包装代码采用 MIT 许可证，见 [LICENSE](LICENSE)。SyncClipboard 及官方图标来自 Jeric-X/SyncClipboard，使用其 MIT 许可证，保留于 [THIRD_PARTY_LICENSE.txt](THIRD_PARTY_LICENSE.txt)。上游镜像内的 .NET、Ubuntu 与其他组件保留各自许可证。本项目不是 Home Assistant 或 SyncClipboard 的官方发行版。
