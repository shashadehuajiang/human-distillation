import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from tqdm import tqdm


def get_ffmpeg() -> str:
    """Find ffmpeg executable, refreshing PATH if needed."""
    env = os.environ.copy()
    env["PATH"] = (
        os.environ.get("PATH", "")
        + ";"
        + os.environ.get("ProgramFiles", "") + "\\ffmpeg\\bin"
        + ";"
        + os.environ.get("LOCALAPPDATA", "") + "\\Microsoft\\WinGet\\Packages\\*\\ffmpeg-*\\bin"
    )
    path = shutil.which("ffmpeg", path=env["PATH"])
    if path:
        return path

    # Fallback: search common locations
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"),
        os.path.join(os.environ.get("ProgramFiles", ""), "ffmpeg"),
    ]
    for base in candidates:
        for root, dirs, files in os.walk(base):
            if "ffmpeg.exe" in files:
                return os.path.join(root, "ffmpeg.exe")
    return "ffmpeg"


FFMPEG = get_ffmpeg()

VIDEO_EXTS = {".mp4", ".flv", ".mkv", ".webm", ".avi", ".mov"}


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_audio(
    video_path: Path,
    audio_dir: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    fmt: str = "wav",
) -> Path:
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{video_path.stem}.{fmt}"

    if audio_path.exists():
        print(f"  [skip] {audio_path}")
        return audio_path

    print(f"  [extract] {video_path.name} -> {audio_path.name}")
    codec_map = {"wav": "pcm_s16le", "mp3": "libmp3lame", "flac": "flac"}
    codec = codec_map.get(fmt, "pcm_s16le")

    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-vn",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-acodec", codec,
        "-loglevel", "error",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True)
    return audio_path


def main():
    parser = argparse.ArgumentParser(description="Step 2: 从视频中提取音频")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--video-dir", default=None, help="视频目录")
    parser.add_argument("--audio-dir", default=None, help="音频输出目录")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] 配置文件不存在: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))

    video_dir = Path(args.video_dir or config["video_dir"]).resolve()
    audio_dir = Path(args.audio_dir or config["audio_dir"]).resolve()
    sr = config.get("sample_rate", 16000)
    ch = config.get("channels", 1)
    fmt = config.get("format", "wav")

    print(f"视频目录:   {video_dir}")
    print(f"音频目录:   {audio_dir}")
    print(f"采样率:     {sr} Hz")
    print(f"声道:       {ch}")
    print(f"格式:       {fmt}")
    print()

    if not video_dir.exists():
        print(f"[ERROR] 视频目录不存在: {video_dir}")
        sys.exit(1)

    videos = sorted([p for p in video_dir.iterdir() if p.suffix.lower() in VIDEO_EXTS])
    if not videos:
        print(f"[ERROR] 未找到视频文件 ({', '.join(VIDEO_EXTS)})")
        sys.exit(1)

    print(f"找到 {len(videos)} 个视频\n")

    success = 0
    for i, vp in enumerate(tqdm(videos, desc="提取进度"), 1):
        print(f"\n[{i}/{len(videos)}] {vp.name}")
        try:
            extract_audio(vp, audio_dir, sr, ch, fmt)
            success += 1
        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] FFmpeg 失败: {e}")
        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\n完成! 成功 {success}/{len(videos)}")


if __name__ == "__main__":
    main()
