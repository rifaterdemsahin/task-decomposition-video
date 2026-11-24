"""Finish a simpligen lesson the edu-film-edit way: audio chain, captions, chapters, QA.

The edu-film-edit skill (.claude/skills/edu-film-edit/SKILL.md) assumes travel-film-edit's
film_edit.py. That isn't installed here, so this tool implements the parts that apply to a
narrated slide lesson (no presenter footage, no music):

  1. Voice chain    highpass 75 Hz -> 2.4:1 compression -> light de-ess
                    + thin pink-noise room-tone bed (no digital silence at cuts)
                    -> two-pass loudnorm to -14 LUFS, true peak -1.5 dBTP (sample peak <= -0.9)
  2. Captions       SRT from the narration + per-scene timing (render's .timeline.json)
  3. Chapters       YouTube chapters (0:00 first, >= 3, each >= 10 s) + description.md
  4. QA             LUFS / sample peak / flashes per second / words per minute -> qa.json,
                    and qa_sheet.jpg (one frame every 12 s) for the eye check

usage: python3 tools/edu_finish.py video/task-decomposition.json video/out/task-decomposition-raw.mp4 video/out/task-decomposition.mp4
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

LUFS_TARGET, TP_TARGET = -14.0, -1.5
ROOM_TONE_DB = -62  # pink noise level under everything


def ff(*args: str, capture: bool = False) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return r.stderr if capture else ""


VOICE = "highpass=f=75,acompressor=threshold=-20dB:ratio=2.4:attack=10:release=150:makeup=2,deesser=i=0.3"


def finish_audio(src: Path, dst: Path) -> dict:
    """Voice chain + room tone, then two-pass loudnorm; video stream copied untouched."""
    amp = 10 ** (ROOM_TONE_DB / 20)
    graph = (f"[0:a]{VOICE}[v];anoisesrc=color=pink:amplitude={amp:.6f}:sample_rate=44100[n];"
             f"[v][n]amix=inputs=2:duration=first:normalize=0,aformat=channel_layouts=stereo[m]")
    # pass 1: measure
    log = ff("-i", str(src), "-filter_complex",
             graph + f";[m]loudnorm=I={LUFS_TARGET}:TP={TP_TARGET}:LRA=11:print_format=json[o]",
             "-map", "[o]", "-f", "null", "-", capture=True)
    m = json.loads(log[log.rindex("{"):log.rindex("}") + 1])
    ln = (f"loudnorm=I={LUFS_TARGET}:TP={TP_TARGET}:LRA=11:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    # pass 2: apply
    ff("-i", str(src), "-filter_complex", graph + f";[m]{ln},aresample=44100[o]",
       "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", str(dst))
    return {"measured_before": {"lufs": float(m["input_i"]), "true_peak": float(m["input_tp"])}}


def ts(t: float, srt: bool = True) -> str:
    h, rem = divmod(t, 3600)
    mnt, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02}:{int(mnt):02}:{int(s):02},{int(round((s % 1) * 1000)) % 1000:03}"
    return f"{int(mnt)}:{int(s):02}" if h == 0 else f"{int(h)}:{int(mnt):02}:{int(s):02}"


def caption_chunks(text: str, max_chars: int = 84) -> list[str]:
    """Sentences, split further at commas/words so a cue is at most 2 lines of ~42 chars."""
    out = []
    for sent in re.split(r"(?<=[.!?:])\s+", text.strip()):
        words, cur = sent.split(), ""
        for w in words:
            if cur and len(cur) + 1 + len(w) > max_chars:
                out.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            out.append(cur)
    return out


def two_lines(s: str, width: int = 42) -> str:
    if len(s) <= width:
        return s
    cut = s.rfind(" ", 0, len(s) // 2 + 6)
    return s[:cut] + "\n" + s[cut + 1:] if cut > 0 else s


# Kokoro reads "Q three"; captions should show the written form (skill: fix technical terms by hand)
CAPTION_FIXES = {"Q three": "Q3", "analyze": "analyse"}


def write_srt(timeline: list, dst: Path) -> int:
    cues, n = [], 0
    for sc in timeline:
        text = sc["narration"]
        for a, b in CAPTION_FIXES.items():
            text = text.replace(a, b)
        chunks = caption_chunks(text)
        if not chunks:
            continue
        speak = sc["audio_seconds"] or (sc["end"] - sc["start"])
        total = sum(len(c) for c in chunks)
        t = sc["start"]
        for c in chunks:
            d = speak * len(c) / total
            n += 1
            cues.append(f"{n}\n{ts(t)} --> {ts(min(t + d, sc['end']))}\n{two_lines(c)}\n")
            t += d
    dst.write_text("\n".join(cues))
    return n


def chapters(timeline: list) -> list[tuple[float, str]]:
    ch = [(sc["start"], sc["chapter"]) for sc in timeline if sc.get("chapter")]
    if not ch or ch[0][0] > 0:
        ch.insert(0, (0.0, "Intro"))
    return ch


def qa(video: Path, timeline: list, out_dir: Path) -> dict:
    # loudness + sample peak
    log = ff("-i", str(video), "-af", "ebur128=peak=sample", "-f", "null", "-", capture=True)
    summary = log[log.rindex("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    # flashes: big frame-to-frame luma jumps, counted per second
    log = ff("-i", str(video), "-vf", "scale=320:-1,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
             "-f", "null", "-", capture=True)
    yavg = [float(v) for v in re.findall(r"YAVG=([\d.]+)", log)]
    jumps = [i for i in range(1, len(yavg)) if abs(yavg[i] - yavg[i - 1]) > 40]  # of 255
    per_sec: dict[int, int] = {}
    for i in jumps:
        per_sec[i // 30] = per_sec.get(i // 30, 0) + 1
    # words per minute over the time the voice is actually speaking
    words = sum(len(sc["narration"].split()) for sc in timeline)
    speak = sum(sc["audio_seconds"] for sc in timeline)
    # contact sheet for the eye check
    ff("-i", str(video), "-vf", "fps=1/12,scale=384:-1,tile=5x5", "-frames:v", "1",
       "-q:v", "3", str(out_dir / "qa_sheet.jpg"))
    ch = chapters(timeline)
    total = timeline[-1]["end"]
    ch_lens = [b[0] - a[0] for a, b in zip(ch, ch[1:] + [(total, "")])]
    hook_end = next((sc["start"] for sc in timeline[1:] if sc.get("chapter")), total)
    checks = {
        "lufs_in_window": -16.5 <= lufs <= -12,
        "sample_peak_ok": peak <= -0.9,
        "max_flashes_per_sec_ok": max(per_sec.values(), default=0) <= 3,
        "wpm_in_140_170": 140 <= words / speak * 60 <= 170,
        "chapters_ok": ch[0][0] == 0 and len(ch) >= 3 and min(ch_lens) >= 10,
        "hook_le_30s": hook_end <= 30,
        "one_cta_at_end": sum("Skool" in sc["narration"] for sc in timeline) == 1
                          and "Skool" in timeline[-1]["narration"],
    }
    return {"lufs": lufs, "sample_peak_dbfs": peak,
            "max_flashes_per_sec": max(per_sec.values(), default=0),
            "words": words, "speaking_seconds": round(speak, 1), "wpm": round(words / speak * 60, 1),
            "video_seconds": round(total, 2), "hook_seconds": round(hook_end, 2),
            "chapters": [{"at": ts(t, False), "name": n, "seconds": round(L, 1)}
                         for (t, n), L in zip(ch, ch_lens)],
            "color_p2_p98": "n/a (no presenter footage)",
            "checks": checks, "pass": all(checks.values())}


def main(scene_file: str, raw: str, final: str) -> None:
    data = json.loads(Path(scene_file).read_text())
    raw_p, final_p = Path(raw), Path(final)
    timeline = json.loads(Path(f"{raw}.timeline.json").read_text())
    out_dir = final_p.parent
    audio = finish_audio(raw_p, final_p)
    stem = final_p.with_suffix("")
    n_cues = write_srt(timeline, Path(f"{stem}.srt"))
    ch = chapters(timeline)
    desc = [data.get("objective", ""), "", "Chapters"] + [f"{ts(t, False)} {n}" for t, n in ch] + [
        "", "Made locally with simpligen: narration by Kokoro-82M (af_heart, kokoro-onnx int8 on CPU),",
        "slides drawn with Pillow, diagrams as SVG, background art generated procedurally on CPU.",
        "No music used."]
    Path(f"{stem}.description.md").write_text("\n".join(desc) + "\n")
    report = qa(final_p, timeline, out_dir) | {"audio": audio, "srt_cues": n_cues}
    Path(f"{stem}.qa.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
