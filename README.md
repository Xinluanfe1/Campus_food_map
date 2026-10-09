# 校园美食地图

以校园地图为核心、由用户共同贡献店铺数据，并通过评分评价与排行榜帮助用户发现校园美食的可配置平台。

- 默认示范校园：西南交通大学犀浦校区
- 第一阶段目标：完成本地可运行的网页版
- 后续目标：支持公网部署、小程序复用后端 API，以及其他校园的数据接入
- 开发模式：AI 辅助开发，人工决策与验收

## 项目文档

- [技术路线与开发说明](./技术路线与开发说明.md)：技术选型、权限矩阵、页面结构、数据模型、API 设计、开发步骤与验收清单；店铺详情信息卡片的交互方式与验收标准已并入第 5.2 节

## 开发约定

- 提交信息（更新日志）、文档说明、界面文案和代码注释统一使用中文。
- 变量名、字段名、数据库表名与 API 路径等技术标识遵循英文命名规范。

## 当前进度

项目初始化（第一步）已于 2026-10-09 完成并通过验收，当前已有的可运行骨架包括：

- 前端：React + TypeScript + Vite 工程，提供第一阶段的骨架页面，并可以调用后端健康检查接口。
- 后端：FastAPI 应用，提供健康检查接口 `GET /api/v1/health`，启动与测试均正常。
- 配置：`backend/.env.example` 环境变量示例、`config/campuses/swjtu_xipu.json` 示例校园配置。
- 依赖版本已固定：后端见 `backend/requirements.txt`，前端见 `frontend/package-lock.json`。

下一步：第二步“设计数据库并完成初始化”（数据表、Alembic 迁移、初始化脚本与示例数据）。

## 目录结构

```text
校园美食地图/
├── frontend/            前端工程（React + TypeScript + Vite）
│   ├── public/          静态资源
│   └── src/
│       ├── api/         后端接口调用
│       ├── components/  可复用组件
│       ├── hooks/       自定义组合式函数
│       ├── pages/       页面组件
│       ├── types/       TypeScript 类型定义
│       └── utils/       工具函数
├── backend/             后端工程（FastAPI）
│   ├── app/
│   │   ├── api/         API 路由
│   │   ├── core/        配置与安全
│   │   ├── db/          数据库连接（第二步实现）
│   │   ├── models/      数据库实体（第二步实现）
│   │   ├── schemas/     API 输入输出结构
│   │   └── services/    业务逻辑
│   ├── migrations/      数据库迁移（第二步实现）
│   └── tests/           后端自动化测试
├── data/                本地数据目录（地图、店铺照片、数据库文件）
├── config/campuses/     校园配置
├── scripts/             本地脚本（后续步骤补充）
└── 技术路线与开发说明.md  项目开发文档
```

## 环境要求

- Python 3.12 及以上（本项目开发环境：Python 3.14.7）
- Node.js 20 及以上 LTS（本项目开发环境：Node.js 24.20.0，含 npm）
- 不需要任何付费 API 或云服务即可完成本地开发

## 安装依赖

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

前端：

```powershell
cd frontend
npm install
```

## 本地启动

后端（默认监听 `http://127.0.0.1:8000`）：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端（默认监听 `http://127.0.0.1:5173`，并把 `/api` 开头的请求代理到后端）：

```powershell
cd frontend
npm run dev
```

启动后可以访问：

- 前端页面：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8000/api/v1/health>
- 后端接口文档：<http://127.0.0.1:8000/docs>

## 测试与构建

```powershell
# 后端接口测试（在 backend 目录执行）
.\.venv\Scripts\python.exe -m pytest -q

# 前端类型检查与生产构建（在 frontend 目录执行）
npm run build
```

## 第一步验收结果

| 验收标准 | 结果 |
| --- | --- |
| 按 README 操作可以成功安装依赖 | 通过 |
| 前端可以正常启动 | 通过 |
| 后端可以正常启动 | 通过 |
| 前端可以请求后端健康检查接口 | 通过 |
| 前端页面无严重控制台错误 | 通过（类型检查、构建、页面加载与接口代理均无报错） |
| 后端无启动异常 | 通过 |
| 不需要付费 API 或云服务 | 通过 |
| Git 中不包含数据库文件、密钥或真实用户密码 | 通过（`.env`、数据库文件与依赖目录均已忽略） |
