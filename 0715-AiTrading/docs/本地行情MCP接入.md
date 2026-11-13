# 本地行情 MCP 接入

本服务通过 Streamable HTTP 提供只读行情工具，默认地址：

```text
http://127.0.0.1:8766/mcp
```

当前已安装为 macOS 用户常驻服务 `com.local.ai-trading.market-mcp`：用户登录后自动启动，进程退出后由 launchd 重新拉起。它与 `8765` 端口的模拟交易服务是独立进程，不运行盘前、盘后任务，也不创建交易订单。

## 客户端接入

需要支持 Streamable HTTP 且能设置请求头的 MCP 客户端。填写：

| 项目 | 配置 |
|---|---|
| 名称 | `local-market` |
| 类型 | `http` / Streamable HTTP |
| URL | `http://127.0.0.1:8766/mcp` |
| 请求头 | `Authorization: Bearer <本地访问令牌>` |

可直接参照项目生成的完整配置：

```text
data/market-mcp/client.json
```

该文件采用常见的 `mcpServers` 配置结构，包含 URL 和请求头。不同客户端配置格式可能不同，应按各自格式填写对应字段。不要将文件内容粘贴到公共聊天或提交到 Git。

访问令牌保存在 `data/market-mcp/access.token`，它与 Tushare 密钥不同。两份文件都只允许本机当前用户读写，并已加入 `.gitignore`。其他系统无需接触 Tushare 密钥。这里的本地地址仅供同一台 Mac 上的客户端访问，其他电脑不能使用自己的 `127.0.0.1` 连接这台 Mac。

服务使用 MCP 官方 Python SDK 2.x，已通过现代协议和 legacy 握手协议的真实 HTTP 客户端测试。服务入口校验访问令牌，并限制 Host、Origin 和请求体大小。

## 三个工具

### get_daily_bar

查询指定日线，价格不复权。示例参数：

```json
{"symbol":"600584.SH","trade_date":"2026-10-28"}
```

结果包含 `bar`、`cached`、`fetched_at`、`adjustment` 和 `volume_unit`。价格以十进制字符串返回，币种 CNY，成交量单位为股。例如 `bar.close` 为 `"55.41"`，不要求调用方处理不同来源字段。

### get_daily_history

查询起止日期均包含的日线区间：

```json
{"symbol":"600584.SH","start_date":"2026-10-01","end_date":"2026-10-28"}
```

最多接受 366 天的日期跨度，返回前复权到区间末日的价格，结果明确标识 `adjustment=qfq_at_end`。保留实际成交股数，整个区间统一使用同一个数据源，不拼接不同来源的复权价格。

历史必须覆盖交易日历的全部会话；停牌或上游缺失造成的缺口会返回工具错误。Tushare 备用历史需要 `daily` 和 `adj_factor` 两个接口权限，不会用不复权价格代替。

### check_data_sources

参数同单日查询，分别真实访问 AKShare 和 Tushare，返回各源 `available`、安全错误分类和检查时间。此工具不使用缓存；日线探测成功不代表所有历史区间及复权接口都可用。

## 支持范围与切换

目前仅支持沪深 A 股日线，格式如 `600584.SH`、`688001.SH`、`000001.SZ`、`300750.SZ`。暂不提供港股、北交所、ETF、基金、分钟线、盘口或实时成交。拒绝未来日期。

每次未命中缓存的请求先访问 AKShare，异常、空值或校验不通过时转到 Tushare。全部失败时返回 MCP 工具错误，调用方可以据此提示数据不可用。

服务内共享最多 128 项、有效期 300 秒的成功结果缓存，并通过锁串行访问上游。同一请求并发到达时只取数一次。缓存标志和最初取数时间一起返回；失败不缓存，过期结果不用于填补上游故障。重启会清空内存缓存。这里未实现离线行情库，也未实现账户级全局限频；其他应用直接访问 Tushare 的请求仍计入账号额度。

## 配置与运维

Tushare 继续使用项目配置中的 `TUSHARE_TOKEN` 或系统环境变量 `TUSHARE_API_KEY`。launchd 不读取交互式 `.zshrc`，当前凭据已通过项目现有私密 `.env` 配置机制提供给后台进程。

所有运行操作使用项目脚本：

```bash
# 首次安装依赖、注册并启动常驻服务
scripts/setup.sh
scripts/mcp/install.sh

# 检查状态、停止、启动或重启
scripts/mcp/status.sh
scripts/mcp/stop.sh
scripts/mcp/start.sh

# 真实 MCP 客户端验收：工具发现、日线、缓存、历史、逐源检查
scripts/mcp/smoke.sh --symbol 600584.SH --trade-date 2026-10-28 --history --sources

# 卸载常驻项，保留本地配置及日志
scripts/mcp/uninstall.sh
```

`start.sh` 对已注册服务执行重启；配置或代码变更后也用此脚本生效。仅测试时可使用 `scripts/mcp/run.sh` 前台运行，须先停止常驻项避免端口冲突。

日志统一放在 `logs/market-mcp/`；`/health` 表示服务进程可响应，不代表上游取数成功。不要用普通 GET 请求 `/mcp` 判断工具是否可用，应运行 `smoke.sh`。

默认端口为 8766。如需自定义，在安装及后续运维脚本的环境中设置同一个 `AI_TRADING_MCP_PORT`；安装脚本会将端口写入 launchd 配置，并重新生成对应的客户端 URL。

## 本次真实验收

2026-10-29，通过本机常驻服务的 HTTP MCP 连接：

- 发现 `get_daily_bar`、`get_daily_history`、`check_data_sources` 三个工具。
- `600584.SH` 的 2026-10-28 日线由 Tushare 返回，收盘价 `55.41`，成交量 `67589920` 股；AKShare 当次不可用，自动切换成功。
- 同一日线重复请求命中服务端缓存。
- 同一交易日的历史接口取数及复权因子处理成功。

这证明本次指定股票、日期的实际路径可用，不代表所有股票、长区间及所有上游接口持续可用。

## 官方参考

- [官方 Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Streamable HTTP 运行方式](https://py.sdk.modelcontextprotocol.io/run/)
- [结构化工具输出](https://py.sdk.modelcontextprotocol.io/servers/structured-output/)

最终回归检查通过：207 项后端测试、7 项前端测试、Ruff、严格类型检查和前端构建。MCP 专项包含实际 TCP/HTTP 连接、现代及 legacy 协议、备用源切换、鉴权、输入校验、缓存失效、容量限制与并发合并等验证。

23:46—23:47 重载后复测：日线及缓存继续成功；历史工具的 Tushare `adj_factor` 请求返回 `code=40203`，提示频率或额度受限。首次成功不代表后续调用不受限。遇到这类拒绝，服务会返回错误，并在本机日志记录安全原因；不会改用不复权数据。探测脚本在工具错误时以非零状态正常退出，不输出 SDK 异常组堆栈。
