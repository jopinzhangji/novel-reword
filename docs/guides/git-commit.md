# 本仓库 Git 提交方法

## 一、推荐步骤（在项目根目录执行）

1. **进入项目根目录**（按实际路径调整）
   ```bash
   cd /root/novel-reword/novel-reword
   ```

2. **查看并暂存要提交的文件**
   ```bash
   git status
   git add <文件或目录>     # 例如：git add src/ docs/ config/
   # 或全部：git add -A
   ```

3. **执行提交**
   ```bash
   git commit -m "<提交说明>"
   # 或直接 git commit 打开编辑器填写
   ```

4. **按需推送**
   ```bash
   git push
   ```

## 二、常见问题排查

- **本机 Git 环境差异**：历史上有环境为 `git commit` 自动附加 `--trailer` 参数导致报错（`error: unknown option 'trailer'`）的情况，属于本机 Git 配置问题（模板、别名、包装脚本），与本仓库代码无关。排查：
  ```bash
  git config --list --show-origin | grep -i commit
  git config --list --show-origin | grep -i trailer
  ```
- **Git 版本过旧**时建议升级（`git --version` 确认）。

## 三、COMMIT_MSG.txt 与本文档的关系

- **COMMIT_MSG.txt**：可作为每次提交前的**本地草稿**（被 `.gitignore` 忽略，不入库）。
- **本文档（docs/guides/git-commit.md）**：只描述「怎么提交」与常见环境问题排查，不写具体某次提交内容。
