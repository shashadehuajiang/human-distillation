# Human Distillation

通过 SFT 蒸馏 B 站 UP 主的人格与说话风格。

## 项目概述

**下载目标 UP 主的视频 -> 提取音频 -> ASR + 说话人分离 -> 构建对话数据集 -> SFT 微调 -> Web Demo 部署**。

最终产物：一个能够模仿特定 UP 主语气、口头禅、思维方式的 AI 对话机器人。

## 整体流程

```
Step 1           Step 2          Step 3              Step 4           Step 5           Step 6
┌─────────┐    ┌─────────┐    ┌──────────────┐    ┌─────────┐    ┌─────────┐    ┌───────────┐
│ 下载视频 │ -> │ 提取音频 │ -> │ ASR+说话人分离│ -> │ 构建    │ -> │ SFT微调 │ -> │ Web Demo  │
│         │    │         │    │              │    │ 数据集  │    │  模型   │    │ 部署测试  │
└─────────┘    └─────────┘    └──────────────┘    └─────────┘    └─────────┘    └───────────┘
```

## 目录结构

```text
human-distillation/
├── README.md                    # 项目说明
├── LICENSE                      # MIT License
├── step-1-download/             # 下载 B 站视频
├── step-2-extract-audio/        # FFmpeg 提取音频
├── step-3-speaker-separation/   # 火山引擎 ASR + 说话人分离
├── step4-build-dataset/         # LLM 标定 UP主 + 构建 SFT 数据集
├── step-5-sft-training/         # SFT 微调（待实现）
└── step-6-web-demo/             # Web Demo 部署（待实现）
```

## 各步骤说明

### Step 1 - 下载视频

使用 BilibiliDown 批量下载目标 UP 主的视频。

- **输入**：UP 主主页 URL / UID
- **输出**：`downloads/<up_name>/` 下的 `.mp4` 文件
- **工具**：[BilibiliDown](https://github.com/nICEnnnnnnnLee/BilibiliDown)

### Step 2 - 提取音频

使用 FFmpeg 将视频批量转为 16kHz 单声道 WAV。

- **输入**：step-1 下载的视频
- **输出**：`audios/` 目录下的 `.wav` 文件
- **工具**：FFmpeg
- **运行**：`cd step-2-extract-audio && python run.py`

### Step 3 - ASR + 说话人分离

使用**火山引擎 BigModel ASR** 云端 API，一步完成语音识别 + 说话人分离。

- **输入**：step-2 的 `.wav` 音频
- **输出**：`transcripts/` 下每音频对应的 `.json`（结构化）+ `.txt`（可读）
- **能力**：中文高精度识别，每个 utterance 标注 speaker ID
- **运行**：`cd step-3-speaker-separation && python run.py`
- **注意**：需火山引擎 ASR 服务的 appKey / accessKey，在 `key.py` 中配置

### Step 4 - 构建数据集

通过对话内容分析标定 UP 主，提取完整多轮对话，生成 ShareGPT 格式 SFT 数据集。

- **UP 主标定**：阅读对话内容，判断谁在控场、给建议、被称呼为"哥"/"老师"
- **数据集格式**：每条 = 一个音频的完整对话，包含 `system` + 多轮 `user/assistant`
- **输出**：`dataset.jsonl`（每行一条完整对话）
- **运行**：`cd step4-build-dataset && python run.py`

```json
{"messages": [
  {"role": "system", "content": "你要扮演UP主大冰哥，给别人心理分析，答疑解惑。"},
  {"role": "user", "content": "对方说的话..."},
  {"role": "assistant", "content": "UP主的回复..."}
]}
```

### Step 5 - SFT 微调

使用构建好的数据集对基座大模型进行监督微调（待实现）。

- **输入**：`dataset.jsonl`
- **输出**：微调后的 LoRA / 全量模型权重
- **工具**：LLaMA-Factory / Firefly / HuggingFace TRL

### Step 6 - Web Demo 部署

搭建前端对话界面，加载微调模型，实现可交互的 UP 主风格对话（待实现）。

- **输入**：微调后的模型
- **输出**：可访问的 Web 服务
- **栈**：Gradio / Streamlit / Next.js + vLLM / Ollama

## 快速开始

```bash
git clone https://github.com/shashadehuajiang/human-distillation.git
cd human-distillation

# Step 1: 下载视频 (BilibiliDown)
# Step 2: 提取音频
cd step-2-extract-audio && pip install -r requirements.txt && python run.py

# Step 3: ASR + 说话人分离 (需配置火山引擎 key)
cd ../step-3-speaker-separation && pip install -r requirements.txt && python run.py

# Step 4: 标定 UP主 + 构建数据集
cd ../step4-build-dataset && python run.py
```

## 依赖

- Python 3.10+
- FFmpeg
- 火山引擎 ASR 服务 (step-3)
- 详见各步骤 `requirements.txt`

## License

MIT © shashadehuajiang
