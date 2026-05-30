"""
Step 4: 构建 SFT 数据集

UP主标定: 通过对话内容分析判断哪个 speaker 是 UP主。
用户可手动标定或使用 LLM (vibe coding) 自动标定。
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm


def load_transcripts(transcript_dir: Path) -> list[dict]:
    results = []
    for jf in sorted(transcript_dir.glob("*.json")):
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["_source_file"] = str(jf)
            results.append(data)
    return results


def load_up_map(map_path: str, transcripts: list[dict]) -> dict[str, str]:
    """加载 UP主映射，支持两种格式:
    1. 文件名 -> speaker: {"xxx.json": "1"}
    2. 序号 -> speaker: {"0": "3"}  # 按排序后的序号
    """
    with open(map_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    result = {}
    keys = list(raw.keys())
    if keys and keys[0].isdigit():
        # 序号模式
        for idx, t in enumerate(transcripts):
            key = str(idx)
            if key in raw:
                result[t["_source_file"]] = raw[key]
    else:
        # 文件名模式
        result = raw
    return result


def build_multi_turn_conversation(transcript: dict, up_speaker: str) -> list[dict] | None:
    segments = transcript.get("segments", [])
    segments = sorted(segments, key=lambda s: s.get("start", 0))

    # 合并连续同说话人
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

    # 构建 messages
    messages = []
    for m in merged:
        speaker = m.get("speaker", "")
        text = m.get("text", "").strip()
        if len(text) < 3:
            continue
        role = "assistant" if speaker == up_speaker else "user"
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += text
        else:
            messages.append({"role": role, "content": text})

    # 显式合并连续同角色
    final = []
    for m in messages:
        if final and final[-1]["role"] == m["role"]:
            final[-1]["content"] += m["content"]
        else:
            final.append(m)
    messages = final

    has_user = any(m["role"] == "user" for m in messages)
    has_assistant = any(m["role"] == "assistant" for m in messages)
    if not has_user or not has_assistant:
        return None

    if messages[0]["role"] == "assistant":
        messages.insert(0, {"role": "user", "content": "你好"})

    return messages


def main():
    parser = argparse.ArgumentParser(description="Step 4: 构建 SFT 数据集")
    parser.add_argument("--transcript-dir", default="../step-3-speaker-separation/transcripts")
    parser.add_argument("--output", default="./dataset.jsonl")
    parser.add_argument("--up-map", default="./up_host_map.json")
    args = parser.parse_args()

    transcript_dir = Path(args.transcript_dir).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    map_path = Path(args.up_map).resolve()

    if not transcript_dir.exists():
        print(f"[ERROR] 文字稿目录不存在: {transcript_dir}")
        sys.exit(1)

    transcripts = load_transcripts(transcript_dir)
    print(f"加载 {len(transcripts)} 个文字稿")

    # 加载 UP主映射
    up_speaker_map = {}
    if map_path.exists():
        up_speaker_map = load_up_map(str(map_path), transcripts)
        print(f"UP主映射: {len(up_speaker_map)} 个\n")
    else:
        print("[WARN] 未找到 up_host_map.json，将跳过所有文件")
        print("请先标定 UP主，格式: {\"0\": \"1\", \"1\": \"3\", ...}\n")

    # 构建数据集
    dataset = []
    for idx, t in enumerate(transcripts):
        source = t["_source_file"]
        fname = Path(source).stem
        up = up_speaker_map.get(source, "")
        if not up:
            print(f"  [skip] 未标定 UP主: {fname[:40]}")
            continue

        messages = build_multi_turn_conversation(t, up)
        if messages is None or len(messages) < 2:
            print(f"  [skip] 无有效对话: {fname[:40]}")
            continue

        dataset.append({"messages": messages})

    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n数据集: {output_path} ({len(dataset)} 条)")

    print("\n--- 各音频对话轮数 ---")
    for idx, item in enumerate(dataset):
        msgs = item["messages"]
        u = sum(1 for m in msgs if m["role"] == "user")
        a = sum(1 for m in msgs if m["role"] == "assistant")
        total = sum(len(m["content"]) for m in msgs)
        up_sp = ""
        for t in transcripts:
            if t.get("_source_file", "") == up_speaker_map.get(list(up_speaker_map.keys())[idx] if idx < len(up_speaker_map) else "", ""):
                pass
        print(f"  [{idx}] {u+a:3d}轮 (U:{u} A:{a})  {total}字")


if __name__ == "__main__":
    main()
