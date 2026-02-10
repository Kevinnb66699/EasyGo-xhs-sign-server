# 小红书签名服务器

为部署在 Vercel 上的小红书发布 API 提供签名服务。

## 功能

- 生成小红书 API 请求签名（x-s, x-t）
- 使用 Playwright 模拟浏览器环境
- Docker 容器化部署
- 健康检查端点

## 部署到 Railway

1. 将此项目推送到 GitHub
2. 访问 https://railway.app
3. 创建新项目 → Deploy from GitHub repo
4. 选择此仓库
5. Railway 会自动检测 Dockerfile 并构建
6. 构建完成后，进入 Settings > Networking
7. 点击 Generate Domain 获取公网域名

## 本地测试

### 使用 Docker

```bash
docker build -t xhs-sign-server .
docker run -d -p 5005:5005 --name xhs-sign xhs-sign-server
```

### 直接运行

```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
python server.py
```

### 测试服务

```bash
python test_server.py http://localhost:5005
```

## API 接口

### 健康检查

```bash
GET /health
```

返回：
```json
{
  "status": "healthy",
  "browser_ready": true
}
```

### 生成签名

```bash
POST /sign
Content-Type: application/json

{
  "uri": "/api/sns/web/v2/note",
  "data": {...},
  "a1": "cookie_a1_value",
  "web_session": "cookie_web_session_value"
}
```

返回：
```json
{
  "x-s": "签名值",
  "x-t": "时间戳"
}
```

## 配置 Vercel

部署完成后，在 Vercel 项目中配置环境变量：

- **Key**: `XHS_SIGN_SERVER_URL`
- **Value**: 你的 Railway 域名（如 `https://xhs-sign-xxx.up.railway.app`）

## 许可证

MIT License
