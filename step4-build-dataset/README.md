# Step 4: 构建 SFT 数据集

从 step-3 的文字稿中提取 UP 主的对话，构建 ShareGPT 格式的 SFT 训练数据。

## 做了什么

```
step-3 文字稿 --> 识别 UP主 (后50%音频说话最多) --> 提取对话对 --> dataset.jsonl
```

## UP 主识别规则

- 取音频 **后 50%** 时间段内的所有说话片段
- 累计每个 speaker 的说话总时长
- **时长最长的人 = UP 主**

直觉：UP 主通常在视频后半段总结、收尾，说话占比更高。

## 数据集格式

ShareGPT / 火山方舟 SFT 格式：

```json
{"messages": [{"role": "user", "content": "对方说的话"}, {"role": "assistant", "content": "UP主的回复"}]}
```

## 使用方法

```bash
python run.py

# 指定路径
python run.py --transcript-dir ../step-3-speaker-separation/transcripts --output ./dataset.jsonl

# 手动纠正 UP 主映射
# 1. 先跑一遍生成 up_host_map.json
# 2. 修改 up_host_map.json 中不对的 UP 主
# 3. 再跑一遍
python run.py --up-map ./up_host_map.json
```

## 输出

| 文件 | 说明 |
|------|------|
| `dataset.jsonl` | SFT 训练数据集 (ShareGPT 格式) |
| `up_host_map.json` | 每个音频识别的 UP 主 speaker 编号 |

## 对话对构建逻辑

1. 合并连续同说话人的片段（间隔 < 3s 视为同一轮）
2. 非 UP 主说话 -> 紧跟着的 UP 主回复 -> 构成一条数据
3. 过滤掉过短的对话（任意一方 < 3 字）
