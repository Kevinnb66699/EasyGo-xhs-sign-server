# 签名服务器上传到 GitHub

## ✅ 准备就绪

8 个文件已准备完毕，可以上传！

---

## 📦 将要上传的文件

### 核心文件（6个）✅
1. `server.py` - 签名服务器主程序（252 行）
2. `requirements.txt` - Python 依赖
3. `Dockerfile` - Docker 构建配置
4. `railway.json` - Railway 配置
5. `.dockerignore` - Docker 忽略规则
6. `.gitignore` - Git 忽略规则

### 文档和测试（2个）✅
7. `README.md` - 项目说明
8. `test_server.py` - 测试脚本

---

## 🚀 上传步骤

### 1. 在 GitHub 创建新仓库

访问 https://github.com/new

配置：
- **仓库名称**: `xhs-sign-server`
- **类型**: Public 或 Private（推荐 Private）
- **不要勾选**: "Initialize this repository with a README"

点击 **Create repository**

### 2. 上传代码

```bash
# 进入签名服务器目录
cd d:\Desktop\Code\Cursor\EasyGo_XHS_publish\xhs-sign-server

# 初始化 Git
git init

# 查看文件列表（应该看到 8 个文件）
git status

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: XHS signature server for Railway"

# 连接远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/xhs-sign-server.git

# 设置主分支
git branch -M main

# 推送到 GitHub
git push -u origin main
```

### 3. 验证上传

访问你的 GitHub 仓库页面，确认：
- ✅ 看到 8 个文件
- ✅ README.md 正常显示
- ✅ Dockerfile 存在

---

## 🌐 部署到 Railway

上传成功后，立即部署：

### 方式 1：从 GitHub 部署（推荐）

1. 访问 https://railway.app
2. 登录（使用 GitHub 账号）
3. 点击 **New Project**
4. 选择 **Deploy from GitHub repo**
5. 选择 `xhs-sign-server` 仓库
6. 等待构建（5-10 分钟）
7. Settings > Networking > Generate Domain
8. 复制域名

### 方式 2：使用官方镜像（快速）

如果你想快速测试：

1. Railway → New Project
2. Deploy from Docker Image
3. 输入：`reajason/xhs-api:latest`
4. 生成域名

---

## 🧪 测试部署

构建完成后：

```bash
# 测试签名服务（在主项目目录）
cd ..
python xhs-sign-server/test_server.py https://your-railway-domain.up.railway.app

# 应该看到：
# ✅ API 信息: 通过
# ✅ 健康检查: 通过
# ✅ 签名生成: 通过
```

---

## 🔧 配置 Vercel

部署成功后，配置 Vercel 环境变量：

1. 登录 Vercel Dashboard
2. 进入主项目 > Settings > Environment Variables
3. 添加：
   - **Key**: `XHS_SIGN_SERVER_URL`
   - **Value**: `https://your-railway-domain.up.railway.app`
4. 保存
5. 重新部署：`vercel --prod`

---

## ✅ 完成标志

- [ ] GitHub 仓库创建成功
- [ ] 8 个文件已上传
- [ ] Railway 部署成功
- [ ] 健康检查通过
- [ ] 测试脚本全部通过
- [ ] Vercel 环境变量已配置

---

## 📋 快速命令汇总

```bash
# 1. 上传到 GitHub
cd d:\Desktop\Code\Cursor\EasyGo_XHS_publish\xhs-sign-server
git init
git add .
git commit -m "Initial commit: XHS signature server for Railway"
git remote add origin https://github.com/YOUR_USERNAME/xhs-sign-server.git
git branch -M main
git push -u origin main

# 2. 测试（等 Railway 部署完成后）
cd ..
python xhs-sign-server/test_server.py https://your-domain.railway.app
```

---

**准备好了吗？开始上传签名服务器吧！** 🚀
