# 心之引力 · 粒子 ❤️

纯 Python + pygame 写的粒子爱心桌面小程序：全部由发光粒子构成，无任何贴图，画面里不显示一个字的 HUD。

- 开场：1200×800 画布底部，粒子像尘埃一样升起，汇聚成一颗**实心 3D 爱心**
- 之后自动进入**六种 3D 爱心形态**的粒子变换循环（形态之间是粒子就地流动变形，不是重新从边缘飞入）
- 鼠标靠近爱心时，会吸走一小撮粒子，在光标处聚成一颗**小爱心**；鼠标离开，粒子自动归位
- 自带音乐（程序内合成，无外部音频文件）

> **直接下载：** [Releases v1.0.0](https://github.com/DLXH-item/HeartParticles/releases/latest)
>
> - `HeartParticles-v1.0.0.zip` — 完整整合包（exe + 源码 + 截图 + 使用说明），解压即用
> - `爱心粒子.exe` — 单文件，双击即开

## 效果预览

### 1. 单个实心 3D 爱心

![单个 3D 爱心](1-单个3D爱心.png)

### 2. 两个中间相叠的爱心

![相叠双心](2-相叠双心.png)

### 3. 内外双层爱心

![内外双层爱心](3-内外双层爱心.png)

### 4. 一箭穿双心

![一箭穿双心](4-一箭穿双心.png)

### 5. 炸开成满天小爱心

![满天小爱心](5-满天小爱心.png)

### 6. 边缘粒子密、中央粒子稀疏，正中用粒子拼出大写 LOVE

![大写 LOVE 爱心](6-大写LOVE爱心.png)

### 主预览

![爱心粒子预览](爱心粒子预览.png)

## 运行方式

### 方式一：exe / 整合包直接运行（推荐，免安装）

- 单文件：直接双击 `爱心粒子.exe` 即可
- 整合包：下载 `HeartParticles-v1.0.0.zip` 解压，双击里面的 `爱心粒子.exe`

两种方式都**不需要装 Python、不需要任何配置**（单文件打包，已内嵌 Python 与 pygame）。

下载地址：<https://github.com/DLXH-item/HeartParticles/releases/latest>

### 方式二：py 源码运行

环境要求：**Python 3.9 及以上**（Windows / macOS / Linux 均可），pygame 无需手动安装——脚本启动时会检测，缺失则自动 `pip install pygame`。

```bash
# 1. 安装 Python 3（已有可跳过）
#    Windows：到 python.org 下载安装包，勾选 Add Python to PATH

# 2. 运行
python heart_particles.py
```

如果自动安装失败，手动装一次：

```bash
pip install pygame
python heart_particles.py
```

### 用 PyCharm / IDEA 运行

1. `File > Open` 打开本项目目录
2. `Settings > Project > Python Interpreter` 选一个 Python 3.9+ 解释器
3. 右键 `heart_particles.py` → `Run`

### 自己打包成 exe

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "爱心粒子" heart_particles.py
```

## 操作说明

| 操作 | 效果 |
| --- | --- |
| 鼠标靠近爱心 | 吸附少量粒子，在光标处聚成小爱心 |
| 鼠标移开 | 粒子归位，恢复原本形态 |
| 鼠标左键按住 | 粒子向光标聚成发光核心 |
| 松开左键 | 冲击波散开，粒子荡回原位 |
| 滚轮 | 画面轻微缩放呼吸 |
| 空格 | 开关氛围音乐 |
| ESC | 退出 |

## 技术要点

- 纯粒子渲染：约 4200 颗粒子，三层柔光叠加（4/6/8px），按深度自动区分大小与亮度
- 弹簧物理：`damp=0.885`、`k=0.085`，粒子之间靠目标点插值实现流动感
- 3D 投影：每颗粒子带 z 深度，转正面投影 + 俯视压缩，产生体积感与厚度
- 变换节奏：1.1 秒 / 次，每形态停留 2.1 秒
- 分辨率自适应：内部固定 1200×800 虚拟画布，按窗口尺寸平滑缩放
- 帧率：普通笔记本约 38–40 FPS

## 说明

- 本程序为纯本地桌面程序，不联网、不读取任何文件、不收集任何数据
- 音乐由程序内 wave 模块实时合成写入临时文件播放
- 仅供娱乐与学习使用，禁止商业售卖
