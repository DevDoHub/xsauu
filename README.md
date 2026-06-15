# 开发指南（有摄像头）

本文档介绍 xsau 项目的本地开发启动流程，分为**后端侧**与**边缘端侧**两部分。

---

## 〇、整体流程流转图

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              边 缘 端 侧 (Linux/Jetson)                          │
│                                                                                 │
│                        ┌──────────────┐                                         │
│                        │  IP 摄像头    │                                          │
│                        │  (rtsp://)   │                                          │
│                        └──┬────────┬──┘                                         │
│                           │        │                                            │
│                  ① RTSP 直拉│        │ ③ RTSP 拉流                                │
│             (OpenCV取帧做检测)│        │   (按注册的 path 主动拉)                    │
│                           ▼        ▼                                            │
│                ┌──────────────┐  ┌──────────────────┐                           │
│                │  边缘端程序   │  │   边缘 mediamtx   │                            │
│                │  tripod_pro  │  │  :19997 / :18554 │                           │
│                │   run.py     │  └──────────────────┘                           │
│                └──────┬───────┘           ▲                                     │
│                       │                   │                                     │
│                       │ ② 注册 path        │                                     │
│                       │   (REST :19997)   │                                     │
│                       └───────────────────┘                                     │
│                                                                                 │
│                       │ Socket.IO 上报                  │ RTSP 中转               │
│                       │ (检测/告警/心跳)                 │ (供后端 mediamtx 拉)     │
└───────────────────────┼─────────────────────────────────┼───────────────────────┘
                        │                                 │
                        │ (公网/内网)                      │
                        ▼                                 ▼
┌───────────────────────┼─────────────────────────────────┼───────────────────────┐
│                       │       后 端 侧 (Win/Linux)       │                       │
│                       │                                 │                       │
│                       │ socket.io-client  emit           │                       │
│                       │ (WebSocket/长连接)               │                       │
│                       ▼                                  ▼                      │
│                ┌──────────────┐                  ┌──────────────────┐           │
│                │ 后端 FastAPI  │  动态注册 path     │   后端 mediamtx   │           │
│                │ + Socket.IO  ├─────────────────>│  :9997 (REST)    │           │
│                │   服务端      │  POST            │  :8554 (RTSP)    │           │
│                │  app.main    │  /v3/config/paths│  :8889 (WebRTC)  │           │
│                │   :5020      │                  │  :8888 (HLS)     │           │
│                └──────┬───────┘                  └────────┬─────────┘           │
│                       │                                   │                     │
│                       │                                   │ WebRTC/WHEP         │
│                       │ REST + SSE + Socket.IO            │ (重流，< 500ms)      │
│                       │ (轻流：广播给浏览器)                 │                     │
│                       ▼                                  ▼                      │
│             ┌──────────────────────────────────────────────────────┐            │
│             │                前端 Vite (浏览器)                      │            │
│             │       frontend/  npm run dev   :5173                 │            │
│             │   ┌──────────────────┐    ┌─────────────────────┐    │            │
│             │   │ REST + SSE +     │    │ <video> 标签         │    │            │
│             │   │ Socket.IO 客户端  │    │  播放 WebRTC 视频流   │    │            │
│             │   └──────────────────┘    └─────────────────────┘    │            │
│             └──────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘

数据分层：
  ─── 重流 (视频)  ：摄像头 ─RTSP→ 边缘 mediamtx ─RTSP→ 后端 mediamtx ─WebRTC→ 浏览器
                    （边缘端程序仅"注册 path"，不经手视频字节）
  ─── 检测面 (AI) ：摄像头 ─RTSP→ 边缘端程序 (OpenCV 取帧 → 推理)
  ─── 轻流 (业务)  ：边缘端 ─Socket.IO(emit)→ 后端 FastAPI ─SSE/Socket.IO/REST→ 前端
                    （后端内嵌 Socket.IO 服务端，边缘端 / 前端均为客户端）
  ─── 控制面       ：① 边缘端 ─REST(:19997)→ 边缘 mediamtx 注册摄像头 path
                    ② 后端   ─REST(:9997) → 后端 mediamtx 动态增删中转 path
```

---

## 一、后端侧开发流程

后端侧包含三个组件，按顺序启动：**mediamtx → 后端服务 → 前端服务**。

### 1. 启动 mediamtx（视频流媒体服务器）（涉及端口 9997/8554/8888/8889/8189）

> 作用：负责重流的 WebRTC / WHEP 转发。
> 官网下载连接：https://github.com/bluenviron/mediamtx/releases

#### 1.1 Windows 版本

1. 解压 `mediamtx_v1.19.1_windows_amd64.zip` 到任意目录（自行记住路径，建议跟代码目录同级）。
2. 将 `deploy/mediamtx.yml` 复制到 `mediamtx.exe` 同目录下，**覆盖**原有配置文件。
3. 启动：双击 `mediamtx.exe`，或在命令行中执行。

#### 1.2 Linux 版本

**方式一：直接运行二进制包**

```bash
# 解压（建议放在易于查找的目录，跟代码目录同级）
tar -zxvf mediamtx_v1.19.1_linux_amd64.tar.gz

# 将 deploy/mediamtx.yml 复制到 mediamtx 同目录下，覆盖原配置
# 启动
./mediamtx mediamtx.yml
```

**方式二：使用 Docker Compose**

```bash
docker-compose up -d
```

---

### 2. 启动后端（FastAPI）

> 作用：提供轻流的 REST API + SSE + Socket.IO。

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（使用 Python 3.11，详见末尾说明）
python3.11 -m venv .venv

# 3. 激活虚拟环境
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行后端
# 开发模式（使用模拟数据）
uvicorn app.main:app --host 0.0.0.0 --port 5020

# 生产模式（使用真实数据）
ENVIRONMENT=production uvicorn app.main:app --reload --host 0.0.0.0 --port 5020
```

> ⚠️ **模式区别**：开发模式使用模拟数据，生产模式使用真实数据。

---

### 3. 启动前端（Vite）

> 作用：UI 展示和用户交互。

```bash
cd frontend
npm install
npm run dev
```

---

## 二、边缘端侧开发流程

边缘端只在 **Linux** 上部署运行，包含两个组件：**mediamtx → 边缘端程序**。

### 1. 启动 mediamtx（边缘端转发）（涉及端口19997/18554）

> 作用：转发摄像头视频流。生产环境中后端侧的 mediamtx 无法直接拉取摄像头，需通过边缘端机器中转。

```bash
# 1. 解压（建议与边缘端代码同级目录，方便管理）
tar -zxvf mediamtx_v1.19.1_linux_amd64.tar.gz

# 2. 将 tripod_pro/middle_deploy/mediamtx.yml.template 复制为
#    mediamtx 同目录下的 mediamtx.yml（覆盖原配置）

# 3. 启动
./mediamtx mediamtx.yml
```

---

### 2. 启动边缘端程序（Python）

> 作用：拉取摄像头视频流并推送到后端侧的 mediamtx。

```bash
# 1. 进入边缘端目录
cd tripod_pro

# 2. 创建虚拟环境（参考边缘端部署手册）
# 3. 配置 tripod_pro/system_config.json

# 4. 启动边缘端
python run.py --no-ui    # 无窗口模式
python run.py            # 有窗口模式
```


## 无摄像头-额外操作(需要模拟一个RTSP流的摄像头)
1. 单独启动一个mediamtx（涉及端口19998/18555）（推荐二进制或者exe的方式启动）
```sh
./mediamtx deploy/mediamtx-no-camera.yml
```

2. ffmpeg开启推送(推送电脑摄像头或者视频)
```sh
# 推送电脑摄像头(windows终端执行)
ffmpeg -thread_queue_size 1024 -rtbufsize 100M `
    -f dshow -framerate 30 -video_size 1280x720 -i video="Integrated Camera" `
    -c:v libx264 -preset veryfast -tune zerolatency `
    -profile:v main -pix_fmt yuv420p -g 60 -b:v 2M `
    -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:18555/0CCCHS6AZ3173341
# 推送视频
cd videos
ffmpeg -re -stream_loop -1 -i dcff88728dc9fb9f856eed0aa927e60d.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency -g 60 -b:v 2M \
  -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:18555/cam1
# 反转
ffmpeg -re -stream_loop -1 -i dcff88728dc9fb9f856eed0aa927e60d.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency -g 60 -b:v 2M -vf "hflip,vflip" \
  -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:18555/0CCCHS6AZ3173341
```

3. 启动边缘端
```sh
SAFESAU_RTSP_URL=rtsp://127.0.0.1:18555/0CCCHS6AZ3173341 python run.py
SAFESAU_RTSP_URL=rtsp://127.0.0.1:18555/cam1 python run.py
SAFESAU_RTSP_URL=rtsp://127.0.0.1:18555/0CCCHS6AZ3173341 python run.py --no-ui
```


## 三、技术选型说明

### 1. 为什么使用 Python 3.11？

主要从**生态兼容性**和**性能/特性**两方面考虑：

- **依赖兼容性最稳**
  - 后端核心栈 `FastAPI 0.115+` / `pydantic 2.10+` / `SQLModel 0.0.22+` / `uvicorn[standard]` / `paho-mqtt` / `python-socketio[asyncio]` 在 3.11 上是**官方主测试矩阵**，社区踩坑信息最多，二进制 wheel 也最齐全（`bcrypt`、`cryptography`、`pydantic-core` 等都有现成轮子，无需本地编译）。
  - 3.10 下 `pydantic v2` 的部分类型推断（如 `Self`、`StrEnum`）需要回退导入，3.11 原生支持。

- **性能 & 异步特性**
  - CPython 3.11 整体性能比 3.10 提升 **10–60%**（"Faster CPython" 项目首发版本），后端是 IO 密集型，但 SSE / Socket.IO 的高频小包场景同样获益。
  - 原生 `asyncio.TaskGroup`、`Exception Groups`，对当前后端 MQTT + SSE + Socket.IO 三路并发的错误传播更友好。

- **不选 3.12 / 3.13 的原因**
  - 3.12 删除了 `distutils`，部分老依赖（包括边缘端 PyTorch 老版本）安装失败。
  - 3.13 默认禁用 GIL 选项尚不成熟，AI 生态轮子覆盖不全。

> 一句话：**3.11 = 性能拐点 + 生态最齐 + Jetson/AI 轮子最全**，是当前后端 + 边缘端能共用的"最大公约数"。

---

### 2. 为什么使用 mediamtx？

项目视频链路的核心需求是：**把 N 路 RTSP 摄像头实时转成浏览器可直接播放的低延迟流**，并且要支持**动态增删摄像头**。mediamtx 几乎是唯一一个开箱即用、零代码满足全部需求的开源方案。

| 需求 | mediamtx 提供能力 |
| --- | --- |
| 浏览器低延迟播放 | **WebRTC / WHEP**（`:8889`），`<video>` 标签直连，端到端 < 500ms |
| 兜底 / 弱网播放 | **HLS LL-Latency**（`:8888`），纯 HTTP 透防火墙 |
| 摄像头接入 | **RTSP**（`:8554`），同时支持 mediamtx 主动拉流 + 边缘端推流两种模式 |
| 动态增删摄像头 | **REST API**（`:9997`），后端通过 `POST /v3/config/paths/add/{name}` 动态注册 path，无需改配置文件、无需重启 |
| 边缘代理转发 | 同一份二进制即可在边缘端跑（`:19997 / :18554`），把弱网/内网摄像头中转到后端 |
| 鉴权 / ACL | 内置 `authInternalUsers`，可按 path、action（publish/read/api）做权限 |
| 部署成本 | **单文件二进制**（Win/Linux/ARM），无依赖、无需 JVM/Node，Jetson 直接跑 |

**对比其他方案**：

- **SRS / ZLMediaKit**：功能也强，但 WHEP 支持/REST API 风格不如 mediamtx 成熟，配置心智更重。
- **Janus / Kurento**：需要写信令层和 SFU 业务代码，对"只是想把 RTSP 转 WebRTC"过度复杂。
- **FFmpeg + 自研服务**：每路流要自己拉进程、做生命周期管理、做 WebRTC 协议栈，工作量巨大。
- **Nginx-RTMP**：无 WebRTC，延迟在 RTMP/HLS 级别（2–5s），不满足监控场景。

> 一句话：**mediamtx = "RTSP 进、WebRTC/HLS 出"的最短路径**，单二进制 + REST API 让我们能把视频链路当成"基础设施"来用，而不是当成"要自研的服务"。

