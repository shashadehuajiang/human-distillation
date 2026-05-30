# Step 2: 提取音频

使用 FFmpeg 将视频文件批量转换为纯音频。

```
.mp4 / .flv / .mkv  -->  FFmpeg  -->  .wav (16kHz, 单声道)
```

## 使用方法

### 1. 安装 FFmpeg

```bash
# Windows
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
apt install ffmpeg
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 配置路径

编辑 `config.yaml`：

```yaml
video_dir: "../videos"      # step-1 下载的视频目录
audio_dir: "./audios"       # 音频输出目录
sample_rate: 16000          # 采样率
channels: 1                 # 单声道
format: "wav"               # 输出格式: wav / mp3 / flac
```

### 4. 运行

```bash
# 默认读取 config.yaml
python run.py

# 覆盖路径
python run.py --video-dir "D:\videos" --audio-dir "D:\audios"
```

### 5. 输出

`audios/` 目录下生成与视频同名的 `.wav` 文件，16kHz 单声道，供下一步 ASR 使用。
