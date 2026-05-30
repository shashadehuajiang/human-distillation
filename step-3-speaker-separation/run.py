"""
Step 3: 火山引擎 BigModel ASR 批量转录 + 说话人分离
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import yaml
from tqdm import tqdm

from demo import recognize_task, file_to_base64

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a"}


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def recognize(file_path: Path) -> dict:
    """调用 demo.py 的 recognize_task，返回 JSON 结果"""
    resp = recognize_task(file_path=str(file_path))
    status = resp.headers.get("X-Api-Status-Code", "")
    if status != "20000000":
        msg = resp.headers.get("X-Api-Message", "unknown")
        raise RuntimeError(f"API 错误: {status} - {msg}")
    return resp.json()


def parse_result(result: dict) -> dict:
    utterances = result.get("result", {}).get("utterances", [])
    segments = []
    speaker_turns: Counter = Counter()

    for utt in utterances:
        text = utt.get("text", "").strip()
        if not text:
            continue

        # speaker 在 additions.speaker 里
        speaker = utt.get("additions", {}).get("speaker", "")
        if not speaker:
            speaker = utt.get("speaker", "")
        if not speaker:
            words = utt.get("words", [])
            if words:
                votes = Counter(w.get("speaker", "") for w in words)
                votes.pop("", None)
                speaker = votes.most_common(1)[0][0] if votes else ""

        segments.append({
            "start": round(utt.get("start_time", 0) / 1000, 2),
            "end": round(utt.get("end_time", 0) / 1000, 2),
            "text": text,
            "speaker": speaker,
        })
        speaker_turns[speaker] += 1

    up_speaker = speaker_turns.most_common(1)[0][0] if speaker_turns else ""
    for seg in segments:
        seg["is_up"] = (seg["speaker"] == up_speaker)

    return {
        "duration_ms": result.get("audio_info", {}).get("duration", 0),
        "up_speaker": up_speaker,
        "speaker_stats": dict(speaker_turns.most_common()),
        "segments": segments,
    }


def save_output(data: dict, audio_path: Path, transcript_dir: Path, up_label: str = ""):
    transcript_dir.mkdir(parents=True, exist_ok=True)
    json_path = transcript_dir / f"{audio_path.stem}.json"
    txt_path = transcript_dir / f"{audio_path.stem}.txt"

    if up_label:
        data["up_speaker"] = up_label
        for seg in data["segments"]:
            seg["is_up"] = (seg["speaker"] == up_label)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    lines = []
    for seg in data["segments"]:
        tag = "[UP]" if seg.get("is_up") else "     "
        lines.append(f"[{seg['start']:7.2f}-{seg['end']:7.2f}] {tag} S{seg['speaker']}: {seg['text']}")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Step 3: 火山引擎 ASR + 说话人分离")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--audio-dir", default=None)
    parser.add_argument("--transcript-dir", default=None)
    parser.add_argument("--up-speaker", default=None)
    parser.add_argument("--single", default=None)
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(str(config_path)) if config_path.exists() else {}

    audio_dir = Path(args.audio_dir or config.get("audio_dir", "../step-2-extract-audio/audios")).resolve()
    transcript_dir = Path(args.transcript_dir or config.get("transcript_dir", "./transcripts")).resolve()
    up_speaker = args.up_speaker or config.get("up_speaker", "")

    if not audio_dir.exists():
        print(f"[ERROR] 音频目录不存在: {audio_dir}")
        sys.exit(1)

    if args.single:
        audios = [Path(args.single).resolve()]
    else:
        audios = sorted([p for p in audio_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS])

    if not audios:
        print(f"[ERROR] 未找到音频文件")
        sys.exit(1)

    skip = [p for p in audios if (transcript_dir / f"{p.stem}.json").exists()]
    todo = [p for p in audios if not (transcript_dir / f"{p.stem}.json").exists()]

    print(f"音频目录:     {audio_dir}")
    print(f"文字稿目录:   {transcript_dir}")
    print(f"API:          火山引擎 BigModel ASR (说话人分离)")
    print(f"总数:         {len(audios)}, 已完成: {len(skip)}, 待处理: {len(todo)}")
    print()

    if not todo:
        print("全部已处理完毕")
        return

    for i, ap in enumerate(tqdm(todo, desc="处理进度"), 1):
        print(f"\n[{i}/{len(todo)}] {ap.name} ({ap.stat().st_size / 1024 / 1024:.1f} MB)")
        try:
            raw = recognize(ap)
            data = parse_result(raw)
            save_output(data, ap, transcript_dir, up_speaker)
            stats = data['speaker_stats']
            up = data['up_speaker']
            print(f"  {len(stats)} 人: {dict(list(stats.items())[:4])} -> UP主: S{up}")
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(2)

    print("\n完成!")


if __name__ == "__main__":
    main()
