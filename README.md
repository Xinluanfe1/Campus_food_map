# 校园美食地图（Unfinished）

以校园地图为核心、由用户共同贡献店铺数据，并通过评分评价与排行榜帮助用户发现校园美食的可配置平台。

- 默认示范校园：西南交通大学犀浦校区
- 第一阶段目标：完成本地可运行的网页版（已完成）
- 后续目标：公网部署、小程序复用后端 API、其他校园的数据接入

> **演示数据声明：** 仓库内的店铺名称、简介、坐标与评价均为虚构演示数据，不代表任何真实店铺；底图为自制的虚构示意图。正式公开前必须替换为经过核实与授权的内容。

---

## 一、项目介绍

### 1.1 项目定位

面向校园场景的美食发现与共建平台：地图负责“看见附近”，用户贡献负责“数据从哪里来”，评分、评价与排行榜负责“哪家值得去”。项目按阶段开发，第一阶段交付一个可以在本地完整运行、权限可靠、可通过配置更换校园的网页版。

### 1.2 功能一览

| 模块 | 说明 |
| --- | --- |
| 地图主页 | 图片底图、瓦片真实地图、百度地图 JSAPI（可选提供方）；点位按类型着色、店铺类型筛选、重置视图、店铺搜索、地图锚定的店铺详情信息卡片 |
| 账号与权限 | 用户名 + 密码注册登录、JWT + HttpOnly Cookie、CSRF 双提交防护、登录注册频率限制、游客/普通用户/管理员三级权限 |
| 店铺 | 登录用户提交店铺（名称、简介、类型、照片、地图点位）、管理员审核（通过/拒绝并填写原因）、修改核心信息后重新审核、公开数据过滤 |
| 评价与互动 | 1—5 星评分与文字评价、编辑与删除自己的评价、点赞点踩（幂等）、一级回复、举报评价 |
| 举报处理 | 管理员查看举报队列，可驳回（保留评价）或隐藏评价，处理人、处理时间与备注可追溯 |
| 榜单与搜索 | 加权评分排行榜（全部/商铺/摊贩、升降序、稳定同分排序、分页）、贡献榜与个人贡献统计、按名称与简介搜索公开店铺 |
| 运维与测试 | 数据库初始化、数据备份与恢复、数据一致性检查、106 项后端自动化测试、前端类型检查与生产构建 |
| 阶段范围 | 第一阶段只启用一个校园；多校园能力已预留但不启用（见 3.5） |

### 1.3 项目文档

| 文档 | 内容 |
| --- | --- |
| [技术路线与开发说明](./技术路线与开发说明.md) | 技术选型、权限矩阵、页面结构、数据模型、API 设计、九个开发步骤与验收清单 |
| [部署说明](./docs/部署说明.md) | 本地部署步骤、环境变量说明、地图提供方与百度地图 AK、运维脚本、公网部署注意事项 |
| [数据库字典](./docs/数据库字典.md) | 全部数据表、字段、类型、约束与删除策略 |
| [更新日志](./更新日志.md) | 各阶段的完成内容、验收结果与缺陷修复记录 |

---

## 二、使用说明

### 2.1 环境要求

- Python 3.12 及以上（本项目开发环境：Python 3.14.7）
- Node.js 20 及以上 LTS（本项目开发环境：Node.js 24.20.0，含 npm）
- 现代浏览器（Chrome、Edge 等）
- 本地核心功能不需要任何付费 API 或云服务；仅“百度地图提供方”需要联网并使用百度 AK

### 2.2 安装依赖

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
npm.cmd install
```

> 如果提示 `无法加载文件 ...\npm.ps1，因为在此系统上禁止运行脚本`，这是 Windows PowerShell 执行策略限制：用 `npm.cmd` 代替 `npm` 即可，或执行 `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` 后继续使用 `npm`。

### 2.3 初始化数据库

首次使用或需要重建数据库时，在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m app.db.init_db
```

脚本会通过 Alembic 创建数据库并写入演示数据（1 个校园、1 名管理员、6 名普通用户、10 家示例店铺及评价互动）。重复执行不会重复插入。

- 管理员账号：`admin`；初始化密码优先取 `--admin-password` 或环境变量 `ADMIN_INITIAL_PASSWORD`，都没有时自动生成随机密码并打印一次，不使用演示密码。
- 演示普通用户密码统一为 `demo-password-2026`，仅用于本地开发与界面测试。
- 单独创建或维护管理员：`python -m app.db.create_admin --username 平台管理员`。

### 2.4 启动项目

推荐使用一键脚本（双击即可，不依赖 PowerShell 执行策略）：

```powershell
# 双击运行，或在项目根目录执行
scripts\一键启动.cmd

# 停止服务
scripts\一键停止.cmd
```

分步启动（脚本方式，各自打开一个窗口）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1
powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1
```

手动启动（等价命令）：

```powershell
# 后端
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

启动后可以访问：

- 前端页面：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8000/api/v1/health>
- 后端接口文档：<http://127.0.0.1:8000/docs>（生产环境自动关闭）

### 2.5 本地调试部署（可选）

需要在不影响主项目的情况下做本机调试时，可以复制一份独立部署目录：

1. 复制项目（排除 `.git`、`node_modules`、`.venv`、`dist`、`backups`）；
2. 在副本的 `backend` 建虚拟环境并安装 `requirements.txt`，在 `frontend` 执行 `npm.cmd install`；
3. 在副本的 `backend/.env` 配置数据库地址与 `BAIDU_MAP_AK`（副本不纳入版本管理，AK 只保存在本机）；
4. 使用副本内的 `scripts\一键启动.cmd` 启动。

完整步骤、环境变量说明与公网部署注意事项见 [部署说明](./docs/部署说明.md)。

### 2.6 常用运维命令

```powershell
# 以下命令均在 backend 目录执行

# 备份（数据库快照 + 校园底图 + 店铺照片 + 校园配置，输出到项目 backups 目录）
.\.venv\Scripts\python.exe -m app.db.backup

# 恢复（覆盖数据库前自动生成带时间戳的安全副本；--dry-run 只校验）
.\.venv\Scripts\python.exe -m app.db.restore --input ..\backups\campus_food_backup_xxx.zip

# 数据一致性检查（外键、孤立记录、坐标体系、审核记录）
.\.venv\Scripts\python.exe -m app.db.check_consistency

# 初始化或补写演示数据（幂等）
.\.venv\Scripts\python.exe -m app.db.init_db

# 从配置文件导入或更新校园
.\.venv\Scripts\python.exe -m app.db.import_campuses
```

### 2.7 目录结构

```text
校园美食地图/
├── frontend/            前端工程（React + TypeScript + Vite + Leaflet）
│   ├── public/          静态资源
│   ├── scripts/         前端自检脚本（坐标换算、卡片定位、页面截图验证）
│   └── src/
│       ├── api/         后端接口调用
│       ├── auth/        登录状态管理
│       ├── components/  可复用组件（地图、详情卡片、评价、点位选择器等）
│       ├── hooks/       自定义组合式函数
│       ├── pages/       页面组件（地图、排行榜、贡献榜、提交、管理后台等）
│       ├── types/       TypeScript 类型定义
│       └── utils/       工具函数（坐标换算、卡片定位、百度 SDK 加载）
├── backend/             后端工程（FastAPI）
│   ├── alembic.ini      Alembic 迁移配置
│   ├── app/
│   │   ├── api/         API 路由与权限依赖
│   │   ├── core/        配置、安全、限流、CSRF
│   │   ├── db/          数据库连接、初始化、备份恢复、一致性检查
│   │   ├── models/      SQLAlchemy 数据模型
│   │   ├── schemas/     API 输入输出结构
│   │   └── services/    业务逻辑（校园、店铺、评价、举报、榜单等）
│   ├── migrations/      数据库迁移脚本
│   └── tests/           后端自动化测试
├── data/                本地数据目录（data/maps 底图、店铺照片、SQLite 数据库）
├── config/campuses/     校园配置（JSON，导入数据库生效）
├── docs/                项目文档（数据库字典、部署说明）
├── scripts/             本地脚本（启动、停止、演示底图生成）
├── 技术路线与开发说明.md  项目开发文档
└── 更新日志.md           更新记录
```

### 2.8 常见问题

| 现象 | 处理方式 |
| --- | --- |
| `无法加载文件 ...\npm.ps1，因为在此系统上禁止运行脚本` | 用 `npm.cmd` 代替 `npm`；或执行 `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| 端口 8000 / 5173 被占用 | 运行 `scripts\一键停止.cmd`，或修改启动命令中的端口参数 |
| 页面能打开但地图空白 | 图片底图模式检查 `data/maps` 中是否有对应底图；百度地图模式检查 `BAIDU_MAP_AK` 是否配置、AK 的 Referer 白名单是否包含本机地址 |
| 忘记了管理员密码 | 使用 `python -m app.db.create_admin --username admin --reset-password` 重置 |
| 需要恢复演示数据 | 删除 `data/campus_food.db` 后重新执行 `python -m app.db.init_db`（会重新生成演示数据与新的管理员密码） |

---

## 三、技术相关

### 3.1 技术栈

| 层级 | 选型 |
| --- | --- |
| 前端 | React 18 + TypeScript + Vite + React Router + Leaflet（图片底图 / 瓦片地图）+ 百度地图 JSAPI（可选） |
| 后端 | Python + FastAPI + Pydantic + SQLAlchemy 2.x + Alembic |
| 数据库 | SQLite（单实例、本地开发与小规模使用；结构变更全部通过迁移管理） |
| 认证 | JWT + HttpOnly Cookie、Argon2id 密码哈希、CSRF 双提交校验、进程内频率限制 |
| 图片存储 | 本地目录（`data/maps`、`data/shop_photos`），UUID 命名，扩展名/内容/尺寸/大小四重校验 |
| 测试 | pytest + FastAPI TestClient（httpx2）；前端 TypeScript 类型检查与 Vite 构建 |

### 3.2 后端结构与接口分层

- `app/api/`：路由层，负责接收请求、身份识别与调用业务服务；全部接口统一前缀 `/api/v1`。
- `app/services/`：业务层，负责校园配置、点位过滤、店铺审核、评价与互动规则、榜单计算、举报处理。
- `app/models/` 与 `app/db/`：数据访问层，负责模型定义、连接管理、迁移与脚本。
- `app/core/`：配置、认证、安全与限流。
- `app/schemas/`：请求与响应结构，全部使用 Pydantic 校验并返回中文错误。

主要接口分组：健康检查、认证（注册/登录/退出/当前用户）、校园与地图（校园列表、地图配置、公开点位、搜索、排行榜、贡献榜）、店铺（提交/修改/详情/审核/照片上传）、评价与互动（评价增改删、点赞点踩、回复、举报）、管理员（校园配置、店铺审核、举报处理）、静态资源（`/assets/maps/...`、`/media/shop_photos/...`）与个人贡献统计。完整清单见《技术路线与开发说明》第七章。

### 3.3 数据库与迁移

- 7 张业务表：`campuses`、`users`、`shops`、`reviews`、`review_reactions`、`review_replies`、`reports`；字段全部为英文 `snake_case`，均带中文注释。
- 结构变更通过 Alembic 迁移（当前 head：`20261009_0003`），启动时不自动建表。
- 时间统一按 UTC 存储与返回；外键、唯一约束、检查约束与高频查询索引齐备。
- 完整字段、约束与删除策略见 [数据库字典](./docs/数据库字典.md)。

### 3.4 认证、权限与安全

- 登录成功后签发 JWT 并写入 HttpOnly Cookie（默认 24 小时），前端不读取认证 Cookie。
- 生产环境必须通过 `JWT_SECRET` 提供密钥，否则拒绝启动；开发环境使用临时密钥（重启后需重新登录）。
- CSRF 采用双提交 Cookie：前端读取可读的 `csrf_token` 并在写操作中通过 `X-CSRF-Token` 回传。
- 频率限制：注册 15 分钟 5 次、登录 5 分钟 10 次（单实例内存实现，多实例部署需替换为共享存储）。
- 权限：未登录访问受保护接口返回 401，普通用户访问管理员接口返回 403；管理员只能由初始化脚本或受控命令创建。
- 上传校验：仅允许 PNG/JPEG/WebP，扩展名与真实格式一致、单文件不超过 5 MB、宽高 200—8000 像素；上传文件不可直接执行。
- 接口不返回密码哈希、密钥或服务器绝对路径。

### 3.5 地图方案

| 模式 | 说明 | 是否依赖密钥 |
| --- | --- | --- |
| 图片底图 | Leaflet `CRS.Simple` + 归一化坐标（`map_x`、`map_y` 为 0 至 1），更换高清底图后点位比例不变 | 否 |
| 瓦片真实地图 | Leaflet + 可配置瓦片地址模板（默认演示为 OpenStreetMap，需遵守其使用政策与署名要求） | 否 |
| 百度地图 JSAPI | 可选提供方，通过 `map_provider = baidu` 启用；`tile_url_template` 存 SDK 地址，AK 由 `BAIDU_MAP_AK` 提供 | 是 |

坐标体系：图片模式使用归一化坐标，真实地图模式使用经纬度（百度地图为 BD09）；接口按校园的地图类型只返回对应的一套坐标，避免混用。

多校园：第一阶段只启用一个校园，界面不显示切换入口；`campuses` 表的配置字段、校园导入脚本与按 `campus_id` 的查询隔离全部保留，启用校园数量大于 1 时前端会自动显示切换入口。

### 3.6 评分与排行榜规则

- 采用贝叶斯加权评分：`S = v/(v+m)·R + m/(v+m)·C`，其中 `R` 为店铺有效评价平均分，`v` 为有效评价数，`C` 为当前校园全部有效主评价平均分，`m = 5`。
- 只有审核通过且至少有一条可见评价的店铺进入评分排行榜；隐藏或删除评价后评分与排名立即更新。
- 排序使用未舍入的加权评分；同分时先按有效评价数量从高到低，再按店铺 ID 从小到大。
- 贡献榜只统计审核通过的店铺，同数量时按更早达到该数量的时间优先，再按用户名升序。

### 3.7 测试与构建

```powershell
# 后端测试（在 backend 目录执行）
.\.venv\Scripts\python.exe -m pytest -q

# 前端类型检查与生产构建（在 frontend 目录执行）
npm.cmd run build

# 前端辅助自检脚本（在 frontend 目录执行）
node scripts\check-map-coordinates.mjs
node scripts\check-card-placement.mjs
```

当前状态：后端 106 项测试全部通过；前端类型检查与生产构建通过；各阶段的验收记录见 [更新日志](./更新日志.md)。

### 3.8 依赖安全说明

- 2026-10-09 将 Vite 升级到 6.4.4、React Router DOM 升级到 6.30.6（同大版本安全修复，技术栈不变）。
- `npm audit` 仍报告 React Router 的 2 个中危问题（开放重定向、SSR hydration），目前只在 7.x 大版本修复。本项目未使用 SSR，也没有把用户输入直接作为跳转地址；是否升级到 React Router 7 待确认（见 4.3）。

---

## 四、其他杂项

### 4.1 开发约定

- 提交信息（更新日志）、文档说明、界面文案和代码注释统一使用中文。
- 变量名、字段名、数据库表名与 API 路径等技术标识遵循英文命名规范。
- 每次更新在 [更新日志](./更新日志.md) 中登记：日期、内容与验收结果。

### 4.2 当前功能限制

- 第一阶段只启用一个校园，界面不显示校园切换入口；多校园能力已预留。
- 百度地图为可选提供方：启用后需要联网并消耗百度开放平台的免费额度，使用前请确认其服务条款与流量限制。
- 免费公网部署存在文件系统临时化、SQLite 并发能力有限等限制，详见《部署说明》第六节。

### 4.3 待确认事项

1. **校园范围字段**：为满足开发文档“真实地图的校外范围控制不能只依赖前端视野”的要求，`campuses` 表新增了可选字段 `boundary_radius_meters`（迁移 `20261009_0002`）。如需改用多边形边界或其他方案，请说明。
2. **React Router 版本**：`npm audit` 提示的 2 个中危问题只能在 React Router 7.x（大版本）修复，当前保持 6.30.6；确认后再升级。
3. **百度地图正式使用**：上线前需要把 Referer 白名单从开发用的通配符改为具体域名，并确认免费额度是否满足预期流量。

### 4.4 更新日志

本 README 不保留更新记录。所有更新内容、验收结果与缺陷修复记录统一维护在 [更新日志](./更新日志.md)。

### 4.5 安全提醒

- `backend/.env`、数据库文件、上传目录与备份文件均已加入 `.gitignore`，不要把真实密钥、管理员密码或用户数据提交到公开仓库。
- 百度地图 AK 会随前端页面下发，属于可公开但需要保护的凭据：只写入本地 `.env`，并务必配置 Referer 白名单。
- 演示账号与演示密码仅供本地开发使用，正式部署前必须替换并停用。
