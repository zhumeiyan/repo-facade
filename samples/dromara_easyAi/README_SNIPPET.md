# easyAi

easyAi — 一套可复现的实验与自检材料



> 视觉母题：Lattice field / 晶格场 · DNA `2bce9b195fa7`
> 形象由仓库标识哈希确定性派生，同一仓库永远同一张脸。

<p align="center">
  <img src="assets/identity.svg" width="600" alt="identity">
</p>

## 状态

| 状态 | 节奏 | 含义 |
|---|---|---|
| 静置 · `idle` | 4s 慢呼吸 | 冷色低亮度 |
| 推演 · `thinking` | 0.8s 快脉冲 | 琥珀偏移 |
| 执行 · `busy` | 持续旋转 | 亮度拉高 |
| 受阻 · `blocked` | 脉冲冻结 | 低饱和红 |
| 失败 · `error` | 红色 | 一次抽动后静止 |
| 达成 · `success` | 短暂暖脉冲 → 回落 idle | 短暂暖脉冲 → 回落 idle |

## 技术约束

- 不跑 JavaScript，动画只用 SVG 内嵌 CSS `@keyframes`
- 不依赖外部库与运行时接口
- SVG 可版本化、可回滚
- 无面：没有人脸 / 拟人动物 / 表情包


