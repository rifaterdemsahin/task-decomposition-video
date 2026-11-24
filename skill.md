edu-film-edit — Educational Film Edit Skill
24 Nov 2026 · @Erdem
Overview
edu-film-edit edits teaching videos (tutorials, explainers, course lessons, AI how-tos) so the viewer understands and remembers one thing. It is the teaching companion to travel-film-edit. It reuses that skill's scripts, LUTs, title systems and QA loop, but swaps spectacle for clarity.
---
name: edu-film-edit
description: Edit educational videos (tutorials, explainers, course lessons, AI how-tos) in a calm cinematic style built for understanding and retention. Reuses the travel-film-edit scripts.
---
The principles come from multimedia-learning research (Mayer: coherence, signaling, segmenting, redundancy) and common YouTube retention practice. Treat every number as a starting default to tune by ear and by retention graphs. None of them were measured from reference films.
Every video runs through three modes in order, with a chapter card between them:
1.  Hook & Promise (15-30s): the problem, a preview of the result, and what the viewer will be able to do.
2.  Teach (repeated once per concept): explain, show, confirm, then a takeaway.
3.  Recap & Practice (30-60s): what the viewer can do now, plus one next step.
Core rules
1.  One learning objective per video. Write it before cutting, as "After this, the viewer can ___." Cut anything that doesn't serve it and save it for another video.
2.  Promise early, pay off visibly. In the first 15-30s, show the end result, then say what the viewer will be able to do. No long intro or logo sting.
3.  Segment. Split the lesson into 3-7 chapters, one concept each, each opening with a chapter card and closing with a one-line takeaway.
4.  Signal, don't decorate. Every on-screen element points at what is being said: a key term, a highlight box, an arrow on a diagram node. No decorative B-roll during hard ideas.
5.  Don't duplicate narration as a paragraph. Short captions are fine. Show key terms only (1-4 words), one at a time.
6.  Cut dead air, keep thinking pauses. Remove ums and retakes. Keep about 0.5-1.0s of pause after a key idea or before a reveal.
7.  Make screens legible. Text should read at roughly 24px or more at 1080p. Punch in 130-200% on the active region and highlight the cursor.
8.  Show it working. Every concept gets a demo or worked example: explain, show, confirm the result.
9.  Calm, consistent look. studio_warm on the presenter; screen recordings ungraded. Hard cuts only, with at most a 35mm film burn between major chapters.
10.  Music stays out of the way. None under dense explanation or code. A quiet bed (-22 to -24 dB under voice) only under the hook, chapter cards and recap.
Mode 1: Hook & Promise (15-30s)
Structure: problem (1 line), then a result preview (2-5s of the finished thing), then the promise ("by the end you'll be able to…"), then chapter card 1.
• Cut it last, once you know what the payoff shot is.
• A short travel_match or strobe_open montage of result shots works, but keep it under 8s and land on a held hero frame with the title.
• Title with film_titles.py --style split (e.g. RAG|IN 10 MIN) or --style stacked for a series name.
python3 scripts/film_edit.py montage "<result_clips>" \
  --music "<bed.wav>" --out out/hook.mp4 \
  --preset travel_match --title "BUILD|AN AGENT" --city "IN 10|MINUTES" \
  --look studio_warm --len 8 --vibe calm
Mode 2: Teach (repeat per concept)
Each chapter is a mini-lesson with five beats:
Beat
Shot
Graphics
Length
Chapter card
still or wide room shot
--style stacked (STEP / TWO / RETRIEVAL) or --style a24_stamp (STEP 2/5 top-left)
2-3s
Explain
wide 11-12mm or 24-70mm talking head
editorial_talk key terms, one PNG per word, timed to the syllable
20-60s
Show
screen recording, diagram or whiteboard
highlight box, punch-in zoom, cursor highlight
30-120s
Confirm
result on screen (output, passing test, finished diagram)
small check stamp or key term
3-8s
Takeaway
back to the presenter
one-line key term
5-10s
Run talking parts through the existing talk pipeline:
python3 scripts/film_edit.py talk "<raw_talk.mp4>" "<out/ch2_talk.mp4>" \
  --look studio_warm --srt "<captions.srt>" \
  --stamp "Lesson 2|retrieval basics" --stamp-style journal
Screen and diagram segments
• Record at 1920x1080 or 2560x1440 with a clean desktop, notifications off, and a 16-20pt editor font on a dark theme.
• Frame diagrams (FigJam, Excalidraw) on #0B0B0D dark carbon with rounded corners and a 4:3 presenter PiP bottom-left.
• Build diagrams progressively: one node or arrow per spoken idea, never the finished diagram at once.
• Punch-in zooms are hard cuts or slow (~0.5s) eased scales. No whip zooms.
• Speed up typing and installs 2-8x with a small 2x corner stamp, or cut to the before/after.
Key-term graphics (--style editorial_talk): a small sans lead over the big term (what is an / embedding), with the term accented in #F6BA98. Show at most one term at a time and hide the bottom captions while it's showing.
Mode 3: Recap & Practice (30-60s)
• Recap the chapter takeaways as a stacked list, revealed line by line on the voice (--style stacked).
• Give one concrete practice task or next step ("try it on your own PDF", "change the chunk size and compare"). One call to action, not five.
• Optional close: a --style postcard seal with the series or academy name over a calm final shot, with the ambient bed rising after the last word.
• End within about 5s of the last useful sentence. No long outro.
Audio, captions and chapters
Audio
• Voice chain: highpass 75 Hz, gentle 2.4:1 compression, light de-ess, then normalize to about -14 LUFS integrated for YouTube (inside the QA window of -16.5 to -12, sample peak ≤ -0.9 dBFS).
• Keep a thin room-tone bed under cuts so jump cuts never drop to digital silence. Crossfade 10-20ms at every audio cut.
• Music only under the hook, chapter cards and recap, ducked -22 to -24 dB under voice. Use licence-safe tracks only (travel-film-edit, "Choosing the Music", section 4).
• About 140-170 words per minute reads as clear teaching. If a take runs fast, add pauses at idea boundaries rather than slowing the clip.
Captions
• Ship an accurate SRT and fix technical terms by hand (product names, code identifiers, acronyms).
• Burn in understated captions for Shorts and social cuts. Upload the SRT as a separate track for the main YouTube video.
Chapters and description
• YouTube chapters: the first timestamp is 0:00, with at least 3 chapters, each at least 10s long.
• Name chapters after the outcome, not the topic ("Make the bot remember" beats "Memory").
• Description: the learning objective in one line, the chapters, links to code or resources, and any music credit the licence asks for.
Workflow, QA and setup
Workflow
1.  Objective & outline: write the one-sentence objective and 3-7 chapter takeaways.
2.  Rough cut from the transcript: delete tangents, retakes and filler in the text first, then cut the video to match.
3.  Structure: place the hook and chapter cards; check every chapter has explain, show and confirm.
4.  Signal: add key terms, highlight boxes, zooms and progressive diagram reveals.
5.  Grade & audio: film_edit.py grade --look studio_warm on presenter shots only, then the voice chain, with music only where allowed.
6.  Assemble: chapters into edit_plan.json, then python3 scripts/film_edit.py assemble edit_plan.json --out out/lesson_v1.mp4.
7.  QA, then export chapters, SRT and description.
Automated QA
Run python3 scripts/film_edit.py qa out/lesson_v1.mp4 with whichever non-montage mode qa --help lists (onset sync doesn't apply to lessons). It should pass:
• LUFS in [-16.5, -12], sample peak ≤ -0.9 dBFS
• color_p2 in [6, 25] and color_p98 in [160, 242] on presenter shots
• max_flashes_per_sec ≤ 3
Check by eye and ear (qa_sheet.jpg, plus one full watch at 1x on a phone)
[ ] Objective stated and result shown in the first 30s
[ ] Every chapter has a demo or worked example and a visible result
[ ] All on-screen text and code readable on a phone
[ ] No titles over faces or over the code being discussed
[ ] No narration duplicated as a paragraph; at most one key term at a time
[ ] No music under dense explanation
[ ] Captions correct for every technical term
[ ] One call to action at the end
[ ] Someone new to the topic could do the practice task after watching
Setup
Needs the travel-film-edit scripts and presets (film_edit.py, film_titles.py, film_grade.py, depth_title.swift, presets/*.cube), installed as in that skill's Setup section: ffmpeg with libvpx-vp9, python3, and pip install numpy opencv-python librosa soundfile pyloudnorm pillow.
