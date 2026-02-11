# 小红书签名服务器

为部署在 Vercel 上的小红书发布 API 提供签名服务。

## 📚 官方实现参考

本服务基于 xhs 官方库的实现：
- **官方仓库**: https://github.com/ReaJason/xhs
- **参考示例**: https://github.com/ReaJason/xhs/blob/master/example/basic_usage.py

## ✨ 功能特性

- ✅ **生成小红书 API 签名**：x-s 和 x-t 参数
- ✅ **自动重试机制**：签名失败时自动重试最多 10 次（基于官方建议）
- ✅ **Playwright 浏览器模拟**：使用 Chromium 无头浏览器
- ✅ **反检测技术**：集成 stealth.min.js 反爬虫检测
- ✅ **Cookie 动态更新**：支持用户自定义 Cookie
- ✅ **健康检查端点**：实时监控服务状态
- ✅ **详细日志记录**：方便调试和故障排查
- ✅ **高并发支持**：使用 gevent 提升性能

## 部署到 Railway

1. 将此项目推送到 GitHub
2. 访问 https://railway.app
3. 创建新项目 → Deploy from GitHub repo
4. 选择此仓库
5. Railway 会自动检测 Dockerfile 并构建
6. 构建完成后，进入 Settings > Networking
7. 点击 Generate Domain 获取公网域名

## 🚀 快速开始

### 方式 1：直接运行（推荐用于开发）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器
playwright install chromium
playwright install-deps chromium  # Linux 需要

# 3. 启动服务
python server.py
```

服务将在 `http://localhost:5005` 启动。

### 方式 2：使用 Docker

```bash
# 构建镜像
docker build -t xhs-sign-server .

# 运行容器
docker run -d -p 5005:5005 --name xhs-sign xhs-sign-server
```

### 测试服务

```bash
# 运行完整测试套件
python test_sign_service.py

# 或手动测试健康检查
curl http://localhost:5005/health
```

## 📖 API 接口文档

### 1. 根路径 - 服务信息

```bash
GET /
```

返回服务基本信息和可用端点列表。

### 2. 健康检查

```bash
GET /health
```

**响应示例**：
```json
{
  "status": "healthy",
  "browser_ready": true,
  "a1": "xxx...",
  "timestamp": 1234567890
}
```

### 3. 获取服务器 a1

```bash
GET /a1
```

**响应示例**：
```json
{
  "a1": "xxx..."
}
```

### 4. 生成签名（核心接口）

```bash
POST /sign
Content-Type: application/json
```

**请求体**：
```json
{
  "uri": "/api/sns/web/v1/note",
  "data": null,
  "a1": "your_cookie_a1_value",
  "web_session": "your_cookie_web_session_value"
}
```

**参数说明**：
- `uri` (必需)：API 路径，如 `/api/sns/web/v1/note`
- `data` (可选)：请求数据，通常为 `null`
- `a1` (必需)：从浏览器 Cookie 获取的 `a1` 值
- `web_session` (可选)：从浏览器 Cookie 获取的 `web_session` 值

**响应示例**：
```json
{
  "x-s": "XYZ1a2b3c4d5e6f7g8h9i0j...",
  "x-t": "1234567890123"
}
```

**重要提示**：
> 即便做了重试，还是有可能会遇到签名失败的情况，客户端应该实现重试机制。

## 📝 使用示例

详细的使用示例和代码参考，请查看 [USAGE_EXAMPLE.md](./USAGE_EXAMPLE.md)

### Python 快速示例

```python
import requests

SIGN_SERVER_URL = "http://localhost:5005"

def get_signature(uri, a1):
    response = requests.post(
        f"{SIGN_SERVER_URL}/sign",
        json={"uri": uri, "data": None, "a1": a1},
        timeout=15
    )
    return response.json()

# 使用
signs = get_signature("/api/sns/web/v1/note", "your_a1_value")
print(f"x-s: {signs['x-s']}")
print(f"x-t: {signs['x-t']}")
```

### 如何获取 Cookie

1. 访问 https://www.xiaohongshu.com 并登录
2. 打开浏览器开发者工具（F12）
3. 进入 `Application` → `Cookies` → `https://www.xiaohongshu.com`
4. 复制 `a1` 和 `web_session` 字段的值

## 🌐 生产环境部署

### 部署到 Railway（推荐）

1. 将此项目推送到 GitHub
2. 访问 https://railway.app
3. 创建新项目 → **Deploy from GitHub repo**
4. 选择此仓库
5. Railway 会自动检测 Dockerfile 并构建
6. 构建完成后，进入 **Settings** > **Networking**
7. 点击 **Generate Domain** 获取公网域名

**优势**：
- ✅ 自动识别 `PORT` 环境变量
- ✅ 免费额度充足
- ✅ 支持 Docker 部署
- ✅ 自动 HTTPS

### 部署到其他平台

本服务也支持部署到：
- **Render**：https://render.com
- **Fly.io**：https://fly.io
- **VPS**：任何支持 Docker 的服务器

### 配置 Vercel 主应用

签名服务部署完成后，在 Vercel 项目中配置环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `XHS_SIGN_SERVER_URL` | `https://your-sign-server.railway.app` | 签名服务的完整 URL |

**重要**：不要在 URL 末尾添加 `/`

## ⚙️ 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PORT` | `5005` | 服务监听端口 |

### 系统要求

- **内存**：≥ 512MB（运行 Chromium）
- **磁盘**：≥ 500MB（Playwright 依赖）
- **CPU**：1 核心即可

## 🔧 故障排查

### 问题 1：`window._webmsxyw is not a function`

**原因**：页面未完全加载或反检测脚本未生效

**解决方案**：
- 服务会自动重试（最多 10 次）
- 检查 `stealth.min.js` 是否正确下载
- 查看服务日志排查问题

### 问题 2：签名一直失败

**原因**：Cookie 不匹配或已过期

**解决方案**：
1. 确保 `a1` 值来自已登录的小红书账号
2. 重新获取最新的 Cookie
3. 检查 Cookie 是否包含特殊字符需要转义

### 问题 3：内存不足

**原因**：Chromium 占用内存较大

**解决方案**：
1. 升级服务器配置到至少 512MB 内存
2. 考虑使用 Chromium 的 `--disable-dev-shm-usage` 参数
3. 定期重启服务释放内存

### 查看日志

```bash
# 本地运行时查看实时日志
python server.py

# Docker 容器查看日志
docker logs xhs-sign -f

# Railway 查看日志
在 Railway Dashboard 中点击 Deployments > View Logs
```

## 📚 相关文档

- [使用示例和代码](./USAGE_EXAMPLE.md) - 详细的 API 使用示例
- [测试脚本](./test_sign_service.py) - 完整的测试套件
- [xhs 官方文档](https://github.com/ReaJason/xhs) - 官方库文档

## 📄 许可证

MIT License
