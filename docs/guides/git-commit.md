# 本仓库 Git 提交方法

## 一、为何你可能无法在本仓库直接 `git commit`

在部分 Windows / Git 版本或本机 Git 配置环境下，执行 `git commit` 可能直接报错：

`error: unknown option 'trailer'`

这通常意味着你的本机环境中有某个配置（例如模板、别名、脚本包装器、或外部工具）在调用 `git commit` 时附加了 `--trailer` 参数，但你当前的 git 版本不支持该参数。**该问题与本仓库代码本身无关**，属于本机 Git 环境差异。

另外：本仓库默认可能会通过 `.gitignore` 忽略 `COMMIT_MSG.txt`，因此它更适合作为“本地提交说明草稿”，而不是仓库内必须追踪的文件。

## 二、推荐步骤（在系统终端执行）

1. **进入项目根目录**
   ```bash
   cd f:\learn\min-autobook
   ```

2. **查看并暂存要提交的文件**
   ```bash
   git status
   git add <文件或目录>     # 例如：git add src/ docs/ config/
   # 或全部：git add -A
   ```

3. **执行提交（优先推荐：直接打开编辑器写提交信息）**
   ```bash
   git commit
   ```
   在弹出的编辑器里粘贴/填写提交说明，保存并退出即可。

4. **若仍报 `unknown option trailer`，按以下方式排查**

- **检查是否有别名/脚本包装了 git commit**
  - `git config --list | findstr alias`
- **检查是否有模板或 commit 相关配置注入了不兼容参数**
  - `git config --list --show-origin | findstr commit`
  - `git config --list --show-origin | findstr trailer`
- **升级 Git**
  - 若你的 git 版本过旧，建议升级到较新的 Git for Windows，再重试 `git commit`。

## 三、COMMIT_MSG.txt 与本文档的关系

- **COMMIT_MSG.txt**：可作为每次提交前的**本地草稿**（不保证被 git 追踪）。
- **本文档（docs/guides/git-commit.md）**：只描述「怎么提交」与常见环境问题排查，不写具体某次提交内容。

下次需要提交时：先改 COMMIT_MSG.txt 写清本次内容，再在终端按上述步骤执行即可。
