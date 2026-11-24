"""Finish a simpligen lesson the edu-film-edit way: audio chain, captions, chapters, QA.

The edu-film-edit skill (.claude/skills/edu-film-edit/SKILL.md) assumes travel-film-edit's
film_edit.py. That isn't installed here, so this tool implements the parts that apply to a
narrated slide lesson (no presenter footage, no music):

  1. Voice chain    highpass 75 Hz -> 2.4:1 compression -> light de-ess
                    + thin pink-noise room-tone bed (no digital silence at cuts)
                    -> two-pass loudnorm to -14 LUFS, true peak -1.5 dBTP (sample peak <= -0.9)
  2. Captions       SRT + small animated captions burned in (ASS karaoke, word-by-word fill),
                    timed per sentence from the measured speech segments (.timeline.json)
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


def caption_chunks(text: str, max_chars: int = 46) -> list[str]:
    """Split a sentence into short single-line cues (small captions, one line each)."""
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > max_chars:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


# Kokoro reads "Q three"; captions should show the written form (skill: fix technical terms by hand)
CAPTION_FIXES = {"Q three": "Q3", "analyze": "analyse"}
SENTENCE = re.compile(r"(?<=[.!?:])\s+")  # same split as tools/kokoro_server.py


def caption_cues(timeline: list) -> list[tuple[float, float, str]]:
    """(start, end, text) per cue. Sentence times come from the measured speech segments of each
    scene (Kokoro pauses between sentences); cues inside a sentence share its time by length.
    Animated scenes that show their own text (the assignment) get no captions."""
    cues = []
    for sc in timeline:
        if sc.get("animate") == "assignment" or not sc["narration"].strip():
            continue
        text = sc["narration"]
        for a, b in CAPTION_FIXES.items():
            text = text.replace(a, b)
        sentences = [s for s in SENTENCE.split(text.strip()) if s]
        segs = sc.get("speech") or []
        if len(segs) == len(sentences):
            spans = [(sc["start"] + s, sc["start"] + e) for s, e in segs]
        else:  # fallback: share the spoken time by sentence length
            speak = sc["audio_seconds"] or (sc["end"] - sc["start"])
            total, t, spans = sum(len(s) for s in sentences), sc["start"], []
            for s in sentences:
                d = speak * len(s) / total
                spans.append((t, t + d))
                t += d
        for sent, (s0, s1) in zip(sentences, spans):
            chunks = caption_chunks(sent)
            total, t = sum(len(c) for c in chunks), s0
            for c in chunks:
                d = (s1 - s0) * len(c) / total
                cues.append((t, min(t + d, sc["end"]), c))
                t += d
    return cues


def write_srt(cues: list, dst: Path) -> int:
    dst.write_text("\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{c}\n"
                             for i, (a, b, c) in enumerate(cues, 1)))
    return len(cues)


def ass_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02}:{s:05.2f}"


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,34,&H00FFFFFF,&H00B4B4B4,&H00120C08,&H96000000,-1,0,0,0,100,100,0,0,1,3,2,2,80,80,96,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(cues: list, dst: Path) -> None:
    """Small animated captions: each cue fades and pops in, then fills word by word (karaoke)."""
    lines = [ASS_HEAD]
    for a, b, c in cues:
        words = c.split()
        dur_cs = max(1, int((b - a) * 100 * 0.92))
        weights = [len(w) + 1 for w in words]
        k = [max(1, round(dur_cs * w / sum(weights))) for w in weights]
        body = " ".join(f"{{\\kf{n}}}{w.replace('{', '(').replace('}', ')')}" for n, w in zip(k, words))
        anim = r"{\fad(140,90)\fscx92\fscy92\t(0,160,\fscx100\fscy100)}"
        lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,,{anim}{body}\n")
    dst.write_text("".join(lines))


def burn_captions(src: Path, ass: Path, dst: Path) -> None:
    ff("-i", str(src), "-vf", f"ass={ass}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
       "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(dst))


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
    stem = final_p.with_suffix("")
    voiced = Path(f"{stem}.voiced.mp4")
    audio = finish_audio(raw_p, voiced)
    cues = caption_cues(timeline)
    n_cues = write_srt(cues, Path(f"{stem}.srt"))
    write_ass(cues, Path(f"{stem}.ass"))
    burn_captions(voiced, Path(f"{stem}.ass"), final_p)
    voiced.unlink()
    ch = chapters(timeline)
    desc = [data.get("objective", ""), "", "Chapters"] + [f"{ts(t, False)} {n}" for t, n in ch] + [
        "", "Made locally: narration by Kokoro-82M (af_heart, kokoro-onnx int8 on CPU),",
        "slides drawn with Pillow, UML diagrams as SVG, background art generated procedurally on CPU.",
        "Captions are burned in; the SRT is included for platforms that want a caption track.",
        "No music used."]
    Path(f"{stem}.description.md").write_text("\n".join(desc) + "\n")
    report = qa(final_p, timeline, out_dir) | {"audio": audio, "srt_cues": n_cues,
               "sentence_timing": sum(len(sc.get("speech") or []) == len(
                   [s for s in SENTENCE.split(sc["narration"].strip()) if s]) for sc in timeline)}
    Path(f"{stem}.qa.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
