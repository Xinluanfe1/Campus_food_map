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

第一至三步已于 2026-10-09 完成并通过验收，当前项目包括：

- 前端：React + TypeScript + Vite 工程，包含地图首页骨架、登录页、注册页与全局登录状态管理，并可以调用后端接口。
- 后端：FastAPI 应用，提供健康检查、注册、登录、退出、当前用户信息等接口，启动与测试均正常。
- 认证与权限：JWT + HttpOnly Cookie 登录状态、CSRF 双提交防护、登录注册频率限制、普通用户与管理员角色校验。
- 数据库：SQLite + SQLAlchemy 模型 + Alembic 迁移，包含 `campuses`、`users`、`shops`、`reviews`、`review_reactions`、`review_replies`、`reports` 七张业务表，配套中文数据字典与演示数据初始化脚本。
- 配置：`backend/.env.example` 环境变量示例、`config/campuses/swjtu_xipu.json` 示例校园配置。
- 依赖版本已固定：后端见 `backend/requirements.txt`，前端见 `frontend/package-lock.json`。

下一步：第四步“实现地图和校园配置”。

## 目录结构

```text
校园美食地图/
├── frontend/            前端工程（React + TypeScript + Vite）
│   ├── public/          静态资源
│   └── src/
│       ├── api/         后端接口调用
│       ├── auth/        登录状态管理
│       ├── components/  可复用组件
│       ├── hooks/       自定义组合式函数
│       ├── pages/       页面组件
│       ├── types/       TypeScript 类型定义
│       └── utils/       工具函数
├── backend/             后端工程（FastAPI）
│   ├── alembic.ini      Alembic 迁移配置
│   ├── app/
│   │   ├── api/         API 路由与权限依赖
│   │   ├── core/        配置与安全
│   │   ├── db/          数据库连接、会话与初始化脚本
│   │   ├── models/      SQLAlchemy 数据模型
│   │   ├── schemas/     API 输入输出结构
│   │   └── services/    业务逻辑
│   ├── migrations/      数据库迁移脚本
│   └── tests/           后端自动化测试
├── data/                本地数据目录（地图、店铺照片、SQLite 数据库文件）
├── config/campuses/     校园配置
├── docs/                项目文档（数据库字典等）
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

## 数据库初始化

首次使用或需要重建数据库时，在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -m app.db.init_db
```

脚本会通过 Alembic 创建或升级数据库结构，并写入演示校园、7 个用户（1 名管理员 + 6 名普通用户）、10 家示例店铺、16 条评价及相关互动数据。重复执行时会跳过已存在的记录，不会重复插入。

- 数据库文件位置：`data/campus_food.db`，可通过 `backend/.env` 中的 `DATABASE_URL` 修改。
- 管理员账号：`admin`。初始化密码优先取命令行参数 `--admin-password` 或环境变量 `ADMIN_INITIAL_PASSWORD`；两者都没有时自动生成随机密码并打印一次，不会使用演示密码。
- 单独创建或维护管理员：`python -m app.db.create_admin --username 平台管理员`；提升已有普通用户需要显式添加 `--promote-existing`，重置密码需要显式添加 `--reset-password`。
- 检查数据库状态：`python -m app.db.check_db`，输出表清单、记录数量、外键与索引。
- 演示普通用户（如“美食探索者”）统一使用演示密码 `demo-password-2026`，仅用于本地开发和界面测试。
- 示例店铺的名称、简介与坐标均为虚构演示数据，正式公开前必须替换为经过核实的数据。
- 完整字段、约束与删除策略见 [数据库字典](./docs/数据库字典.md)。

## 认证与安全

- 认证方式：登录成功后由后端签发 JWT 并写入 HttpOnly Cookie，前端不读取认证 Cookie；会话默认有效期 24 小时（`ACCESS_TOKEN_EXPIRE_MINUTES`）。
- JWT 密钥：优先读取环境变量 `JWT_SECRET`。开发环境未配置时使用进程内临时密钥（重启后端后需要重新登录）；生产环境未配置会直接拒绝启动。
- CSRF 防护：采用双提交 Cookie 方案。前端从可读的 `csrf_token` Cookie 取值，并在所有写操作中通过 `X-CSRF-Token` 请求头回传；注册与登录接口没有登录状态，不参与校验。
- 频率限制：注册每个来源 15 分钟最多 5 次，登录 5 分钟最多 10 次，超出返回 429 中文提示（单实例内存实现，多实例部署需改用共享存储方案）。
- 权限规则：未登录访问受保护接口返回 401，普通用户访问管理员接口返回 403；管理员只能通过初始化脚本或 `python -m app.db.create_admin` 创建，注册接口不允许提交角色字段。
- 生产环境（`APP_ENV=production`）会自动关闭 `/docs` 交互式文档并要求配置 `JWT_SECRET`；HTTPS 部署时请把 `COOKIE_SECURE` 设为 `true`。

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

## 第二步验收结果

| 验收标准 | 结果 |
| --- | --- |
| 可以创建数据库 | 通过（Alembic 迁移创建 SQLite 数据库） |
| 数据库中存在全部规定的表 | 通过（7 张业务表，另有 `alembic_version`） |
| 表和字段均有中文说明 | 通过（模型 comment 属性、迁移脚本中文说明与数据字典三处齐全） |
| 重复执行初始化不会重复插入数据 | 通过（第二次执行插入 0 条、跳过 43 条） |
| 用户名唯一约束生效 | 通过（重复用户名被数据库拒绝） |
| 评价唯一约束生效 | 通过（同一用户对同一家店铺只能保留一条主评价） |
| 店铺、评价及互动外键有效 | 通过（连接启用外键，非法引用被拒绝，删除评价级联清理互动、回复与举报） |
| 普通用户不能自行创建管理员角色 | 通过（角色检查约束生效，管理员只能由初始化脚本或受控命令创建） |
| 数据库重建后可以通过初始化脚本恢复测试数据 | 通过（删除数据库文件后重新初始化，43 条演示数据完整恢复） |
| 不使用前端 JSON 代替正式数据库 | 通过（店铺、评价等业务数据全部入库；前端仅保留校园配置文件） |

数据库结构与初始化测试：17 项全部通过（`backend/tests/test_schema.py`、`backend/tests/test_init_db.py`）。

## 第三步验收结果

| 验收标准 | 结果 |
| --- | --- |
| 可以注册普通账号 | 通过（`POST /api/v1/auth/register`，注册用户固定为 `user` 角色） |
| 重复用户名被拒绝 | 通过（返回 409 与中文提示） |
| 数据库不保存明文密码 | 通过（Argon2id 哈希存储，接口响应不包含密码字段） |
| 可以正常登录和退出 | 通过（登录写入 HttpOnly Cookie，退出清除登录状态并支持 CSRF 校验） |
| 登录后能够获取当前用户信息 | 通过（`GET /api/v1/auth/me`） |
| 未登录用户调用受保护接口时返回 401 | 通过（`/auth/me`、`/users/me/shops` 等） |
| 普通用户调用管理员接口时返回 403 | 通过（`GET /api/v1/admin/shops/pending`） |
| 普通用户无法通过修改请求参数获得管理员权限 | 通过（注册请求携带额外字段直接 422；使用错误密钥伪造的 JWT 被拒绝） |
| 用户无需头像、邮箱或手机号即可使用系统 | 通过（注册只需用户名和密码） |
| 错误提示全部使用中文 | 通过（接口错误、输入校验错误与页面提示均为中文） |

第三步自动化测试 31 项全部通过（含认证与权限 14 项）；前端类型检查与生产构建通过；端到端联调（注册 → 登录 → 获取当前用户 → 缺少 CSRF 被拒 → 退出 → 退出后 401）通过。
