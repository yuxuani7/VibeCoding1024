# VibeSnake 1024

一个基于 `pygame` + `numpy` 的创意贪吃蛇小游戏：  
你需要在 64x64 网格中控制蛇，规避风险豆子、吃掉收益豆子，并冲击 `1024` 分目标。
**这是2025百度“1024程序员节VibeCoding比赛”前三名，谨以此纪念一段实习时光。**

## 项目特性

- 经典贪吃蛇玩法 + 1024 主题目标分数
- 全屏自适应窗口（支持拖拽缩放）
- 菜单页带动态霓虹 `1024` Shader 背景
- 游戏中集成代码雨（CodeWall）视觉效果，分数越高成功词条占比越高
- 三类豆子机制，推动风险与收益决策
- 达成条件后触发 `PERFECT 1024` 彩蛋结算页

## 玩法规则

- 棋盘大小：`64 x 64`
- 初始分数：蛇初始长度（开局为 `8`）
- 分数规则（本质上等于蛇长度变化）：
  - 绿色豆（Success）：长度 `+2`
  - 黄色豆（Warning / Orange）：长度 `-1`
  - 红色豆（Error）：长度 `-5`
- 失败条件：
  - 撞墙
  - 撞到自己（非尾巴安全位）
  - 被连续扣长度至蛇体为空
- 彩蛋触发（代码逻辑）：
  - 分数 `>= 1024`
  - 场上红豆数量为 `0`
  - 场上黄豆数量 `<= 256`

## 操作说明

- `↑ ↓ ← →` 或 `W A S D`：移动
- `R`：死亡/彩蛋后重新开始
- `ESC`：返回菜单（或在菜单退出）
- 菜单页中：
  - `Enter` / `Space`：开始游戏
  - `ESC`：退出程序

## 运行环境

- Python `3.10+`
- 依赖：
  - `pygame==2.6.1`
  - `numpy==2.3.4`

## 快速开始

```bash
# 1) 克隆仓库
git clone https://github.com/yuxuani7/VibeCoding1024.git
cd VideCoding1024

# 2) 创建并激活虚拟环境（可选但推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) 安装依赖
pip install -r requirements.txt

# 4) 启动游戏
python main.py
```

## 项目结构

```text
.
├── main.py           # 程序入口：菜单 -> 指南 -> 游戏主循环
├── menu.py           # 主菜单与动态背景动画
├── guide.py          # 游戏规则说明页
├── game.py           # 核心玩法逻辑（移动、碰撞、生成、渲染、结算）
├── codewall.py       # 代码雨效果（随分数变化词条权重）
├── shader.py         # 1024 霓虹 Shader 背景生成（numpy）
└── requirements.txt  # 依赖列表
```


