# InfoEmpire Battlecard - 部署指南

**更新时间**：2026-03-26 12:07

## 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| 本地服务 | ✅ | `python async_api_server.py --port 8082` |
| Battlecard代码 | ✅ | `tools/battlecard_generator.py` |
| 竞品监控 | ✅ | `tools/competitor_monitor.py` |
| 本地Dashboard | ✅ | `http://localhost:8082/` |
| 公网访问 | ❌ | 需部署到云 |

**公网部署是唯一出路，10分钟完成**

---

---

## ⚡ 方案A：Railway（推荐，不要信用卡）

Railway免费试用$5额度，不用信用卡，够用1个月。

### 步骤：

1. 打开 👉 **https://railway.app** → 用GitHub账号登录
2. Dashboard点 **"New Project"** → **"Deploy from GitHub repo"**
3. 选择仓库：`kangshijie8/infoempire-battlecard`
4. Railway会自动检测Python，配置：
   - **Start Command**: `python serve_intel_dashboard.py --port $PORT`
   - **Health Check Path**: `/api/intel/health`
5. 点 **"Add Variables"** 添加环境变量：
   - `MINIMAX_API_KEY` = `sk-cp-u41neK4opNpopBFRmhuHKAdQ2QpSj3dW5ziFrSJcyztEAGFQjm3RHRNaguRkLVo31oeBTT-DuxXF7AtIF4d2E65Pvyog1izC_i18dRSUrk013XSRC8K9sZY`
   - `MINIMAX_BASE_URL` = `https://api.minimaxi.com/anthropic/v1`
   - `MINIMAX_MODEL` = `MiniMax-M2.7`
6. Railway自动部署，完成后给你URL

> 💡 提示：Railway默认新加坡节点，延迟低

---

## 方案B：Render（免费，需信用卡）

⚠️ Render免费版需要绑定信用卡（美国平台惯例）

1. 打开 👉 **https://dashboard.render.com** → 连接GitHub
2. 选择仓库：`kangshijie8/infoempire-battlecard`
3. 创建Web Service：
   - **Name**: `infoempire-battlecard`
   - **Region**: Singapore
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python serve_intel_dashboard.py --port $PORT`
   - **Plan**: Free
4. 添加环境变量（同上）
5. Create → 等待部署

### 第一步：创建GitHub仓库（2分钟）

打开 https://github.com/new 创建公开仓库：
- 仓库名：`infoempire-battlecard`
- 选择 **Public**

### 第二步：上传代码到仓库（3分钟）

打开仓库 → "uploading an existing file" → 上传以下4个文件：

**requirements.txt**（新建，内容如下）：
```
httpx
aiohttp
aiofiles
```

**serve_dashboard.py** → 来自 `D:\信息帝国\tools\serve_dashboard.py`

**battlecard_generator.py** → 来自 `D:\信息帝国\tools\battlecard_generator.py`

**async_api_server.py** → 来自 `D:\信息帝国\async_api_server.py`

（如果async_api_server.py不存在，用 `serve_dashboard.py` 代替）

### 第三步：创建Render服务（3分钟）

1. 打开 https://dashboard.render.com
2. 点 **"Connect a GitHub repo"** → 选择你刚创建的仓库
3. 点 **New +** → **Web Service**
4. 配置：
   - **Name**: `infoempire-battlecard`
   - **Region**: Singapore
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python serve_intel_dashboard.py --port $PORT`
   - **Plan**: Free
5. 点 **Create**

### 第四步：添加环境变量（1分钟）

在Environment页面添加：
- `MINIMAX_API_KEY` = `sk-cp-u41neK4opNpopBFRmhuHKAdQ2QpSj3dW5ziFrSJcyztEAGFQjm3RHRNaguRkLVo31oeBTT-DuxXF7AtIF4d2E65Pvyog1izC_i18dRSUrk013XSRC8K9sZY`
- `MINIMAX_BASE_URL` = `https://api.minimaxi.com/anthropic/v1`
- `MINIMAX_MODEL` = `MiniMax-M2.7`

点 **Save Changes** → Render自动部署

完成后访问：`https://infoempire-battlecard.onrender.com`

---

## 核心功能验证

部署后测试：

```bash
# Health检查
curl https://infoempire-battlecard.onrender.com/api/intel/health

# 生成Battlecard（30秒）
curl -X POST https://infoempire-battlecard.onrender.com/api/intel/report \
  -H "Content-Type: application/json" \
  -d '{"sources":["toutiao"],"industry":"AI工具"}'
```

---

## 产品定价

| 套餐 | 价格 | 说明 |
|------|------|------|
| 单次 | ¥99/竞品 | 48小时交付 |
| 月度 | ¥699/月 | 无限竞品+监控 |
| 企业 | ¥1999/月 | API+多团队 |

## 联系方式

微信：huyecio
