# AI 每日资讯邮件

每天抓取 OpenAI、Google AI、DeepMind、Hugging Face、Microsoft AI、NVIDIA AI、TechCrunch AI、MIT Technology Review 和 arXiv 的最新内容，进入文章页提取正文，生成无需点击原文即可阅读的中文简报邮件。

支持兼容 OpenAI Chat Completions 的模型接口，用于中文翻译、摘要、分类和“为什么值得关注”解读。没有模型密钥时，会自动使用免费翻译把英文标题和摘要转换为中文。

## 1. 本地运行

需要 Python 3.11 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填入邮箱和 SMTP 授权码。先生成预览：

```powershell
python -m ai_daily --preview
```

确认内容正常后发送：

```powershell
python -m ai_daily
```

## 2. 邮箱配置

### QQ 邮箱

- `SMTP_HOST=smtp.qq.com`
- `SMTP_PORT=465`
- `SMTP_USE_SSL=true`
- `SMTP_PASSWORD` 填写 QQ 邮箱设置中生成的 SMTP 授权码，不是 QQ 密码。

### 163 邮箱

- `SMTP_HOST=smtp.163.com`
- `SMTP_PORT=465`
- `SMTP_USE_SSL=true`
- `SMTP_PASSWORD` 填写客户端授权码。

### Gmail

- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=465`
- `SMTP_USE_SSL=true`
- `SMTP_PASSWORD` 填写 Google 应用专用密码。

`MAIL_TO` 可以填多个收件人，用英文逗号分隔。

## 3. 模型摘要（可选）

配置一个兼容 Chat Completions 的接口：

```dotenv
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

也可以替换成其他兼容接口的 `BASE_URL` 和模型名。

配置 DeepSeek 后，系统会把每篇文章最多 8000 个字符的正文分别交给模型，生成 180-320 字的中文小短文、中文标题和价值分析，再根据全部简报生成当日总览。模型请求失败时会自动回退到免费翻译摘要。

翻译模式由 `.env` 中的 `TRANSLATION_MODE` 控制：

- `auto`：默认。有模型密钥时用模型，否则自动使用免费翻译。
- `free`：始终使用免费翻译。
- `llm`：只使用配置的模型。
- `off`：不翻译，保留原文。

`FULL_ARTICLE_BRIEF=true` 会自动提取新闻正文作为简报素材；`BRIEF_MAX_CHARS=2200` 控制每条简报在翻译前的最大长度。原文链接仅作为邮件底部的信息核验入口。

## 4. Markdown 下载

每次运行会在 `output` 目录生成 `latest.md` 和按日期命名的 Markdown 简报，并将 Markdown 作为邮件附件发送。GitHub Actions 还会把文件部署到 GitHub Pages，邮件末尾会显示“下载 Markdown 简报”按钮。

首次部署前，在 GitHub 仓库进入 `Settings → Pages`，将 `Build and deployment → Source` 设置为 `GitHub Actions`。GitHub Free 的 Pages 需要使用公开仓库；私有仓库需要支持私有 Pages 的付费计划。

## 5. GitHub Actions 每天自动发送

将项目推送到 GitHub，然后进入：

`Settings → Secrets and variables → Actions → New repository secret`

添加以下 Secrets：

| Secret | 内容 |
|---|---|
| `SMTP_HOST` | 如 `smtp.qq.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USER` | 发件邮箱 |
| `SMTP_PASSWORD` | SMTP 授权码 |
| `MAIL_FROM` | 发件邮箱 |
| `MAIL_TO` | 收件邮箱 |
| `SMTP_USE_SSL` | `true` |
| `LLM_API_KEY` | 可选 |
| `LLM_BASE_URL` | 可选 |
| `LLM_MODEL` | 可选 |

工作流默认每天北京时间 08:00 和 22:00 运行，也可以在 Actions 页面手动触发。工作流显式使用 `Asia/Shanghai` 时区，无需手工换算 UTC。由于 GitHub Actions 的队列调度，实际邮件可能在计划时间后数分钟到达。如需改时间，编辑 `.github/workflows/daily-ai-news.yml` 中的 cron。

## 6. 自定义资讯源

编辑 `config/sources.json` 即可增删 RSS/Atom 源。`priority` 越大，在邮件中越靠前。单个资讯源失效不会阻止其他内容发送。

## 隐私与安全

- `.env` 已被 `.gitignore` 忽略，不要将授权码提交到 GitHub。
- GitHub Actions 使用 Repository Secrets，不在仓库中保存明文密钥。
- 邮件内容是自动摘要，重要信息请点击原文核实。
