# AGENTS.md — digital-paper-parser

## 项目结构

- `src/main.rs` — Rust CLI：将 PDF 页面转为图片，调用 Kimi API 提取文章
- `webapp/app.py` — Flask Web 应用：管理 SQLite 中的解析文章、PDF 查看、热区编辑
- `monitor_daemon.py` — Python 守护进程：监控解析进度、卡住自动重启、飞书告警
- `check_*.py`、`report_today.py` — 数据库检查和日报工具脚本
- `daily.db` — SQLite 数据库，存储解析后的文章记录

## 构建/运行命令

### Rust（CLI 解析器）
```bash
cargo build              # Debug 构建
cargo build --release    # Release 构建
cargo run                # 直接运行 main.rs
cargo run --release      # 运行 Release 构建
cargo check              # 快速类型检查，不编译
```

### Python（Web 应用）
```bash
cd webapp
pip install -r requirements.txt
python app.py            # 启动 Flask 开发服务器
```

### Python（脚本）
```bash
python monitor_daemon.py  # 启动监控守护进程
python check_db.py        # 检查 SQLite 数据库
python check_today.py     # 检查今日解析状态
```

## 测试

当前未配置测试框架，无测试文件。
如需添加测试：
- **Rust**：使用 `#[cfg(test)]` 模块配合 `cargo test`。运行单个测试：`cargo test test_name`
- **Python**：使用 `pytest`。安装：`pip install pytest`。运行：`pytest tests/` 或 `pytest tests/test_file.py -k test_name`

## 代码检查 / 格式化

当前未配置 linter 和格式化工具。建议添加：
- **Rust**：`cargo clippy`（代码检查）、`cargo fmt`（格式化）
- **Python**：`ruff check .`（代码检查）、`ruff format .`（格式化）或 `black .` + `flake8 .`

## 代码风格

### Rust（`src/main.rs`）
- **Edition**：2024
- **导入**：标准库 → 外部 crate → 本地模块。本地模块使用 `use crate::`
- **错误处理**：使用 `thiserror` 定义自定义错误枚举。用 `#[from]` 自动转换。函数返回 `Result<T, CustomError>`
- **命名**：类型/枚举用 `PascalCase`，函数/变量/模块用 `snake_case`
- **类型**：数据结构体派生 `Debug`、`Serialize`、`Deserialize`。使用 `serde` 属性进行 JSON 映射（如 `#[serde(rename = "errMsg")]`）
- **异步**：使用 `tokio` 运行时配合 `#[tokio::main]`。I/O 密集型函数标记为 `async`
- **日志**：使用 `tracing` 的 `info!`、`debug!`、`error!` 宏。通过 `tracing-subscriber` 配合 `RUST_LOG` 环境变量配置
- **注释**：业务逻辑使用中文注释。行内注释用 `//`，分区用 `// ===`
- **缩进**：4 空格（rustfmt 默认）

### Python（`webapp/app.py`、脚本）
- **导入**：标准库 → 第三方库 → 本地模块。组间用空行分隔
- **错误处理**：使用 `try/except` 捕获具体异常。返回 JSON 错误响应并附带 HTTP 状态码（401、404、500）
- **命名**：函数/变量用 `snake_case`，常量用 `UPPER_CASE`
- **数据库**：直接使用 `sqlite3`，配合上下文管理器。务必关闭连接。使用 `sqlite3.Row` 获取字典式行访问
- **路由**：Flask 装饰器显式声明 HTTP 方法。受保护路由使用 `@login_required` 装饰器
- **模板**：使用 `render_template_string()` 内联 HTML，配合三引号字符串常量
- **缩进**：4 空格

### 通用约定
- **代码和提交信息中不使用 emoji**
- **UI 字符串、日志消息和注释使用中文**
- **代码中存在硬编码凭证**（API 密钥、密码）—— 不要提交新的密钥
- **文件路径**：Python 使用 `pathlib.Path`，Rust 使用 `std::path`。优先使用相对于项目根目录的相对路径
