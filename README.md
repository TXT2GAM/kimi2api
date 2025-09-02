## 安装步骤

### 方法1：Docker部署
```bash
git clone https://github.com/TXT2GAM/kimi2api.git
cd kimi2api

docker build -t kimi2api .

docker run -d -p 8000:8000 kimi2api
```

---

### 方法2：Docker Compose部署

```bash
git clone https://github.com/TXT2GAM/kimi2api.git
cd kimi2api

# 默认映射到 8000 端口
docker compose up -d
```

#### 更新容器

```bash
cd kimi2api

git pull origin main
# or
# git fetch origin && git reset --hard origin/main

docker compose down
docker compose build --no-cache
docker compose up -d
```

---
### 说明

#### 前端管理

http://localhost:8000/admin

#### 支持模型

`Kimi-K2`

---
