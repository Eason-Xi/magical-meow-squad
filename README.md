# 魔法少女喵喵队

移动端 H5 横版自动奔跑小游戏：单指跳跃、踩怪弹跳连击、猫咪伙伴机关、关底魔法清场。

**在线试玩：** https://eason-xi.github.io/magical-meow-squad/ （手机请横屏；电脑点鼠标或按空格跳跃）

## 目录

| 路径 | 内容 |
|------|------|
| `魔法少女喵喵队_PRD_长期迭代版_v1.0.md` | 产品需求文档 |
| `demo/` | 试玩版：单文件 Canvas 游戏 + 精灵素材，含糖果森林前 3 关 |
| `art/concept/` | 角色、场景、HUD 概念图 |
| `art/raw/` | AI 生成的精灵原图 |
| `art/tools/cut_sprites.py` | 把精灵原图抠成透明底并切片到 `demo/assets/sprites/` |
| `art/tools/serve.py` | 本地预览服务器 |

## 本地预览

```bash
python3 art/tools/serve.py 8765 demo
```

然后打开 http://localhost:8765/ 。

## 部署

推送到 `main` 且改动涉及 `demo/` 时，GitHub Actions 会自动把试玩版发布到 GitHub Pages（见 `.github/workflows/pages.yml`）。
