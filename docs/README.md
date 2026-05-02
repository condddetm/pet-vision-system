# 使用手册编译说明

本目录包含智能宠物视觉系统的 **LaTeX 使用手册** 源码。

## 文件清单

- `usage_manual.tex` — 主文档源码（中文，含封面、目录、12 章正文、3 章附录）
- `README.md` — 本编译说明

## 编译要求

- TeX 发行版：**TeX Live 2022+** 或 **MiKTeX 2022+**
- 编译引擎：**XeLaTeX**（必须，用于中文支持）
- 必需宏包：`ctex` · `tcolorbox` · `fontawesome5` · `listings` · `hyperref` · `booktabs` · `geometry`

> 上述宏包均为 TeX Live / MiKTeX 标准发行版默认包含，无需额外安装。

## 编译命令

在本目录（`docs/`）下执行：

```bash
xelatex usage_manual.tex
xelatex usage_manual.tex
```

> **运行两次** 是为了让目录、交叉引用、页码正确生成。

输出文件：`usage_manual.pdf`（约 25–30 页 A4）。

## 在 VS Code 中编译

安装 **LaTeX Workshop** 扩展，配置默认编译命令为 XeLaTeX：

```json
"latex-workshop.latex.recipes": [
  {
    "name": "xelatex ×2",
    "tools": ["xelatex", "xelatex"]
  }
],
"latex-workshop.latex.tools": [
  {
    "name": "xelatex",
    "command": "xelatex",
    "args": ["-synctex=1", "-interaction=nonstopmode", "-file-line-error", "%DOC%"]
  }
]
```

打开 `usage_manual.tex`，按 `Ctrl+Alt+B` 编译即可。

## 在 Overleaf 中编译

1. 创建新项目 → 上传 `usage_manual.tex`
2. 菜单 → Settings → Compiler → 选择 **XeLaTeX**
3. 点击 Recompile 即可

## 清理中间文件

```bash
del *.aux *.log *.out *.toc *.synctex.gz
```

## 自定义说明

如需修改文档内容：

| 修改位置 | 对应章节 |
|---|---|
| 标题 / 副标题 / 版本号 | 第 \begin{titlepage} 块（约第 165 行）|
| 系统简介 | 第 1 章（`\chapter{系统简介}`）|
| 安装步骤 | 第 2 章 |
| 启动方式 | 第 3 章 |
| 各页面使用指南 | 第 4–8 章 |
| 高级功能 | 第 9 章 |
| FAQ | 第 10 章 |
| API / 性能 / 加分项 | 附录 A / B / C |

## 常见编译错误

### 找不到 ctex 宏包

```
! LaTeX Error: File `ctex.sty' not found.
```

**解决方案**：使用完整版 TeX Live（`scheme-full`）或在 MiKTeX 下手动安装 `ctex` 宏包。

### 找不到中文字体

```
! Package fontspec Error: The font "..." cannot be found.
```

**解决方案**：`ctex` 默认使用系统中文字体（Windows: 宋体 / Mac: 华文）。如缺失字体，
在 `\documentclass` 后添加：

```latex
\usepackage[fontset=windows]{ctex}    % Windows
\usepackage[fontset=mac]{ctex}        % macOS
\usepackage[fontset=fandol]{ctex}     % Linux (无需系统字体)
```

### tcolorbox 报错

如果系统的 tcolorbox 版本较旧，注释掉 `\tcbuselibrary{skins, breakable}` 中的 `skins` 即可。
