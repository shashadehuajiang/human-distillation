# Human Distillation

通过 SFT 蒸馏 B 站 UP 主的人格与说话风格。

## 项目概述

本项目的目标是：**下载目标 UP 主的视频 -> 提取音频 -> 分离 UP 主本人的声音 -> 构建对话数据集 -> 使用 SFT 微调 LLM -> 部署可对话的 Web Demo**。

最终产物是一个能够模仿特定 UP 主语气、口头禅、思维方式的 AI 对话机器人。

## 整体流程

```
Step 1           Step 2          Step 3           Step 4          Step 5          Step 6
┌─────────┐    ┌─────────┐    ┌───────────┐    ┌─────────┐    ┌─────────┐    ┌───────────┐
│ 下载视频 │ -> │ 提取音频 │ -> │ 区分UP主  │ -> │ 构建    │ -> │ SFT微调 │ -> │ Web Demo  │
│         │    │         │    │   声音    │    │ 数据集  │    │  模型   │    │ 部署测试  │
└─────────┘    └─────────┘    └───────────┘    └─────────┘    └─────────┘    └───────────┘
```

## 目录结构

```text
human-distillation/
├── README.md                    # 项目说明
├── LICENSE                      # MIT License
├── step-1-download/             # 下载目标 UP 主的视频
├── step-2-extract-audio/        # 从视频中提取音频
├── step-3-speaker-separation/   # 区分 UP 主本人声音
├── step-4-build-dataset/        # 构建 SFT 训练数据集
├── step-5-sft-training/         # 对大模型进行 SFT 微调
└── step-6-web-demo/             # Web Demo 部署与测试
```

> 每个步骤的文件夹命名格式为 `step-{序号}-{目标}`，内部包含该步骤的脚本、配置和说明文档。

## 各步骤说明

### Step 1 - 下载视频

根据目标 UP 主的 UID 或主页链接，批量下载其发布的视频。

- 输入：UP 主主页 URL / UID
- 输出：`videos/` 目录下的 `.mp4` / `.flv` 视频文件
- 工具：bilibili API / you-get / yt-dlp

### Step 2 - 提取音频

将下载的视频文件转换为纯音频格式，便于后续处理。

- 输入：`videos/` 目录下的视频文件
- 输出：`audios/` 目录下的 `.wav` / `.mp3` 音频文件
- 工具：FFmpeg

### Step 3 - 区分 UP 主声音

从音频中分离出 UP 主本人的声音（剔除 BGM、其他说话人、环境噪音等）。

- 输入：原始音频文件
- 输出：仅包含 UP 主声音的干净音频
- 方法：说话人日志（Speaker Diarization）+ 语音分离 / UVR (Ultimate Vocal Remover)

### Step 4 - 构建数据集

将 UP 主的语音转为文本，清洗整理为 SFT 可用的对话数据集。

- 输入：UP 主纯音频
- 输出：Alpaca / ShareGPT 格式的 JSON / JSONL 数据集
- 流程：ASR 语音转文字 -> 文本清洗 -> 对话格式转换 -> 质量审核

### Step 5 - SFT 微调

使用构建好的数据集对基座大模型进行监督微调。

- 输入：对话数据集
- 输出：微调后的 LoRA / 全量模型权重
- 工具：LLaMA-Factory / Firefly / HuggingFace TRL

### Step 6 - Web Demo 部署

搭建前端对话界面，加载微调模型，实现可交互的 UP 主风格对话。

- 输入：微调后的模型
- 输出：可访问的 Web 服务
- 栈：Gradio / Streamlit / Next.js + vLLM / Ollama

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/shashadehuajiang/human-distillation.git
cd human-distillation

# 按顺序执行各步骤
# 具体用法见各 step 文件夹下的 README
```

## 依赖

- Python 3.10+
- FFmpeg
- CUDA (推荐)
- 详见各步骤 `requirements.txt`

## License

MIT © shashadehuajiang
