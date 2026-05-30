"""
Step 4: 构建 SFT 数据集
- 规则识别 UP主：音频后50%时间段内，说话时长最多的人
- 提取 UP主 对话数据，构建 ShareGPT 格式 SFT 数据集
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm


def load_transcripts(transcript_dir: Path) -> list[dict]:
    """加载所有 step-3 产出的 JSON 文字稿"""
    results = []
    for jf in sorted(transcript_dir.glob("*.json")):
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["_source_file"] = str(jf)
            results.append(data)
    return results


def identify_up_host(transcript: dict) -> str:
    """在音频后50%时间段内，累计说话时长最多的人 = UP主"""
    segments = transcript.get("segments", [])
    duration_ms = transcript.get("duration_ms", 0)
    if not segments or duration_ms <= 0:
        return ""

    half_time = duration_ms / 2  # 毫秒
    # 用秒为单位计算
    half_time_s = half_time / 1000

    speaker_duration: defaultdict[str, float] = defaultdict(float)
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        speaker = seg.get("speaker", "")
        if start >= half_time_s and speaker:
            speaker_duration[speaker] += (end - start)

    if not speaker_duration:
        # 降级：全时段统计
        for seg in segments:
            speaker = seg.get("speaker", "")
            if speaker:
                speaker_duration[speaker] += (seg.get("end", 0) - seg.get("start", 0))

    return max(speaker_duration, key=speaker_duration.get) if speaker_duration else ""


def build_multi_turn_conversation(transcript: dict, up_speaker: str) -> list[dict] | None:
    """
    将一个音频构建为完整的多轮对话:
    [user, assistant, user, assistant, ...]
    非UP主 = user, UP主 = assistant
    """
    segments = transcript.get("segments", [])
    segments = sorted(segments, key=lambda s: s.get("start", 0))

    # 1. 合并连续同说话人片段
    merged = []
    for seg in segments:
        speaker = seg.get("speaker", "")
        text = seg.get("text", "")
        if not text:
            continue
        if merged and merged[-1]["speaker"] == speaker:
            gap = seg.get("start", 0) - merged[-1].get("end", 0)
            if gap < 3:
                merged[-1]["text"] += text
                merged[-1]["end"] = seg.get("end", 0)
                continue
        merged.append(dict(seg))

    # 2. 构建 messages 列表: non-UP = user, UP = assistant
    messages = []
    for m in merged:
        speaker = m.get("speaker", "")
        text = m.get("text", "").strip()
        if len(text) < 3:
            continue
        if speaker == up_speaker:
            role = "assistant"
        else:
            role = "user"
        # 连续同角色合并
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += text
        else:
            messages.append({"role": role, "content": text})

    # 3. 显式合并连续同角色消息
    final_messages = []
    for m in messages:
        if final_messages and final_messages[-1]["role"] == m["role"]:
            final_messages[-1]["content"] += m["content"]
        else:
            final_messages.append(m)
    messages = final_messages

    # 至少要有一次 user->assistant 交互
    has_user = any(m["role"] == "user" for m in messages)
    has_assistant = any(m["role"] == "assistant" for m in messages)
    if not has_user or not has_assistant:
        return None

    return messages


def build_sft_dataset(transcripts: list[dict], up_speaker_map: dict = None) -> tuple[list[dict], dict]:
    """构建 SFT 数据集，每个音频一条完整多轮对话"""
    dataset = []
    up_hosts: dict[str, str] = {}

    for t in transcripts:
        source = t.get("_source_file", "")
        up_speaker = identify_up_host(t)
        up_hosts[source] = up_speaker

        if up_speaker_map and source in up_speaker_map:
            up_speaker = up_speaker_map[source]

        if not up_speaker:
            print(f"  [WARN] 未识别到 UP主: {Path(source).name}")
            continue

        messages = build_multi_turn_conversation(t, up_speaker)
        if messages is None:
            print(f"  [WARN] 无有效对话: {Path(source).name}")
            continue

        # 确保以 user 开头
        if messages[0]["role"] == "assistant":
            messages.insert(0, {"role": "user", "content": "你好"})

        dataset.append({"messages": messages})

    return dataset, up_hosts


def main():
    parser = argparse.ArgumentParser(description="Step 4: 构建 SFT 数据集")
    parser.add_argument("--transcript-dir", default="../step-3-speaker-separation/transcripts")
    parser.add_argument("--output", default="./dataset.jsonl")
    parser.add_argument("--up-map", default=None, help="手动指定 UP 主的 JSON 文件")
    args = parser.parse_args()

    transcript_dir = Path(args.transcript_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not transcript_dir.exists():
        print(f"[ERROR] 文字稿目录不存在: {transcript_dir}")
        sys.exit(1)

    # 加载手动映射
    up_speaker_map = {}
    if args.up_map:
        with open(args.up_map, "r", encoding="utf-8") as f:
            up_speaker_map = json.load(f)

    transcripts = load_transcripts(transcript_dir)
    print(f"加载 {len(transcripts)} 个文字稿")

    dataset, up_hosts = build_sft_dataset(transcripts, up_speaker_map)

    # 输出
    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 输出映射文件
    map_path = output_path.parent / "up_host_map.json"
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(up_hosts, f, ensure_ascii=False, indent=2)

    print(f"\n数据集: {output_path} ({len(dataset)} 条)")
    print(f"UP主映射: {map_path}")

    # 统计
    print(f"\n--- 各音频对话轮数 ---")
    for item in dataset:
        msgs = item["messages"]
        turns = [(msgs[i]["role"], msgs[i+1]["role"]) for i in range(0, len(msgs)-1, 2)]
        user_turns = sum(1 for m in msgs if m["role"] == "user")
        assistant_turns = sum(1 for m in msgs if m["role"] == "assistant")
        total_chars = sum(len(m["content"]) for m in msgs)
        print(f"  {user_turns+assistant_turns:2d}轮 (U:{user_turns} A:{assistant_turns})  {total_chars}字")

    print(f"\n--- 对话示例 (第1条前6轮) ---")
    msgs = dataset[0]["messages"]
    for i, m in enumerate(msgs[:6]):
        role = "UP主" if m["role"] == "assistant" else "对方"
        print(f"  [{role}] {m['content'][:120]}...")
    print()


if __name__ == "__main__":
    main()
