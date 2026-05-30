# Step 4: 构建 SFT 数据集

从 step-3 文字稿中提取 UP 主的多轮对话，构建 ShareGPT 格式 SFT 训练数据。

## 流程

```
文字稿 -> UP主标定 -> 提取多轮对话 -> dataset.jsonl
```

## UP 主标定

UP 主识别需要**人工判断**，基于对话内容分析：

- **标定依据**：谁在控场？谁在给建议？谁被称呼为"哥"/"老师"？谁说话带有权威感？
- **标定方式**：阅读 `transcripts/*.txt` 中的对话内容，判断每个音频中哪个 speaker ID 是 UP 主
- **映射格式**：在 `up_host_map.json` 中填写 `{"文件序号": "speaker编号"}`

也可以使用 **vibe coding**（让 AI 读取对话内容自动判断），思路：
1. 提取每个 speaker 的代表性发言
2. 发给 LLM，描述 UP 主的特征（控场者、给建议者、被称呼为"哥"）
3. LLM 返回 speaker ID

## 数据集格式

每个音频 = 一条完整多轮对话（ShareGPT / 火山方舟 SFT 格式）：

```json
{"messages": [
  {"role": "user", "content": "对方说的话"},
  {"role": "assistant", "content": "UP主的回复"},
  {"role": "user", "content": "对方下一句"},
  {"role": "assistant", "content": "UP主再回复"},
  ...
]}
```

规则：
- 连续同 speaker → 合并为一条
- 连续同 role → 合并为一条
- 非 UP 主 → `user`，UP 主 → `assistant`

## 使用方法

```bash
# 1. 先标定 UP主（编辑 up_host_map.json）
# 格式: {"0": "3", "1": "1", ...}  数字 = 文件按字母排序后的序号

# 2. 生成数据集
python run.py

# 指定路径
python run.py --transcript-dir ../step-3-speaker-separation/transcripts --output ./dataset.jsonl
```

## 输出

| 文件 | 说明 |
|------|------|
| `dataset.jsonl` | SFT 训练数据集 |
| `up_host_map.json` | UP 主 speaker 编号映射 |
