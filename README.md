# Repo Facade

**给任意仓库生成一套「活的状态立面」。**

一条命令，从仓库地址到成品：

```bash
python3 facade.py --repo owner/name --out ./assets
```

产出 6 个文件：`social-preview.png`(1280×640) · `identity.svg`(1200×420) ·
`states.svg`（六状态）· `index.html`（一页式演示站）· `README_SNIPPET.md` · `dna.json`

## 它跟素材库贴图的区别

| | 本工具 | 通用做法 |
|---|---|---|
| 动画 | SVG 内嵌 CSS `@keyframes`，**GitHub README 里真的会动** | `<script>`，被 GitHub 剥掉后变静态 |
| 形象 | 由仓库标识哈希确定性派生，同一仓库永远同一张脸 | 每次重画，版本间漂移 |
| 母题 | 从仓库结构签名生成：渗流 / 枝晶 / 晶格 | 通用科技背景 |
| 人脸 | **无面**：不画人脸、拟人动物、表情包 | 常见吉祥物 |
| 可回滚 | 全是文本（SVG/HTML/MD），能 diff | 二进制 |

## 六状态

| 状态 | 节奏 | 含义 |
|---|---|---|
| idle | 4s 慢呼吸 | 冷色低亮度 |
| thinking | 0.8s 快脉冲 | 琥珀偏移 |
| busy | 持续旋转 | 亮度拉高 |
| blocked | 冻结 | 低饱和红 |
| error | 一次抽动后静止 | 红 |
| success | 短暂暖脉冲后回落 idle | 暖 |

## 自检

```bash
python3 facade.py --repo owner/name --out ./assets
python3 verify.py ./assets owner_name
```

三遍检查：存在性 / 内容性（无 script、图形数、keyframes、PNG 色数与着墨率）/ 确定性复现。
任一项 FAIL 就不许交付。

## 接单

见 [GIG.md](GIG.md)——英文与中文商品页文案，可直接挂 Fiverr / Upwork / 猪八戒。
样例见 `samples/`，全部来自真实公开仓库。
