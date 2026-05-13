# MindPulse 开发指南

> 本文档包含开发流程、测试策略、AI 辅助规范等。

---

## 一、开发流程

### 功能开发流程

```
1. 需求阶段
   ├── 明确功能边界（做什么 / 不做什么）
   ├── 识别已知风险和需要验证的假设
   └── 分解为可独立交付的子任务

2. 设计阶段
   ├── 写 Spec（包含架构、数据流、接口）
   ├── human review spec（你自己要读）
   └── 识别与现有代码的边界

3. 实现阶段
   ├── TDD（先写测试，再实现）
   ├── 小步提交（每个 commit 可独立理解）
   └── 本地跑测试验证

4. 验收阶段
   ├── 你做人工测试
   ├── 检查是否破坏了现有功能
   └── 合并前跑完整测试套件
```

### Bug 修复流程

```
1. 复现阶段
   ├── 明确复现步骤
   ├── 识别触发条件
   └── 确认预期行为 vs 实际行为

2. 调查阶段
   ├── 理解相关代码（不要只看 bug 周围）
   ├── 追溯根本原因（不是只修症状）
   └── 提出 2-3 个可能的修复方案

3. 修复阶段
   ├── 选择最小改动方案
   ├── 写测试防止 regression
   └── 验证修复有效

4. 确认阶段
   ├── 跑完整测试套件
   ├── 确认没有引入新问题
   └── 写清楚 commit message
```

---

## 二、测试策略

### 分层测试

```
E2E 测试 (Playwright)
├── 覆盖核心用户流程
├── 不追求 100% 覆盖
└── 关键路径必须通过

集成测试 (pytest)
├── 覆盖 API、WebSocket、数据层
├── 每个接口至少一个测试
└── 测试真实交互（不 mock 数据库）

单元测试 (pytest + Vitest)
├── 覆盖独立函数、组件
├── 快速执行
└── 关注边界情况
```

### 运行测试

```bash
# 运行所有测试
uv run pytest        # Python 后端测试
npm test            # 前端测试

# 运行 E2E
npx playwright test

# 带覆盖率
uv run pytest --cov
npm test -- --coverage
```

### 测试何时写

- 新功能：**先写测试再实现**（TDD）
- Bug 修复：**先写能复现 bug 的测试，再修**
- 重构：**确保测试覆盖再动**

---

## 三、AI 辅助规范

### 让 AI 做什么

| 任务 | AI 适合度 |
|------|-----------|
| 代码生成 | 高 |
| 代码审查 | 高 |
| 测试生成 | 高 |
| 技术调研 | 高 |

### 让人类做什么

| 任务 | 必须参与 |
|------|----------|
| 架构决策 | 是 |
| 安全相关 | 是 |
| 业务逻辑 | 是 |
| Code Review | 是 |

### Skill 触发时机

| 场景 | 应该用的 Skill |
|------|---------------|
| 想实现一个功能，不知道怎么做 | **brainstorming** |
| 需要写详细的实现计划 | **planner** |
| 开发新功能或修复 Bug | **tdd-guide** |
| 写完了代码，需要 review | **code-reviewer** |
| Build 失败了 | **build-error-resolver** |
| 需要运行 E2E 测试 | **e2e-runner** |

---

## 四、Worktree 使用规范

### 正确流程

**创建实验 worktree：**
```bash
# 从 master 创建实验分支
git worktree add .claude/worktrees/feature-x feature-x

# 实验完成后删除 worktree
git worktree remove .claude/worktrees/feature-x
git worktree prune
```

### 使用场景判断

| 场景 | 推荐方式 |
|------|---------|
| 开发新功能 | 单 worktree + branch |
| Bug 修复 | 单 worktree + branch |
| 技术方案验证 | Worktree（临时） |
| 危险的重构 | Worktree（临时） |
| 并行开发多个功能 | **禁止** |

---

## 五、常用命令

```bash
# 启动开发
npm run dev              # 同时启动前后端
npm run dev:server        # 仅后端
npm run dev:client        # 仅前端

# 代码质量
uv run ruff check .       # Lint
uv run ruff format .      # Format
uv run pyright            # Type check

# 测试
uv run pytest tests/      # 后端测试
npx playwright test       # E2E 测试

# 部署
cp deploy/.env.docker .env && docker compose -f deploy/docker-compose.yml up --build
```

---

## Change Log

- 2026-05-13: 整合 AI-software-engineering-guide.md 和 e2e-testing.md