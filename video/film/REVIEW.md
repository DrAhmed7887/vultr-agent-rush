# Review: Teach Ahmes film, draft 1 (4 Nov 2026)

Output: `video/out/teach-ahmes-film.mp4`. 2:31.5, 1920×1080, 30 fps, 32 MB. It replaces the 2:47 cut that joined two films.

## Creative calls
- **Storyline:** A, "Ahmes's school day" (see STORYLINES.md). B (inside his head) and C (case file) were not built.
- **One world all the way through.** Every sandbox claim is the real Playwright recording on the tablet, or a stamp quoting the real receipt.
- **Each beat is told once.** The cartoon sets it up, and the tablet proves it.
- **Ahmes stays on screen the whole time.** While the tablet is full, he watches from the corner.
- **Ahmes's voice:**
  - on the tablet, his real in-app clips;
  - in the cartoon, the same Charlie voice through ElevenLabs.
- **No captions:** the child's words appear as typed bubbles, and the narration is not captioned.

## Measured
- `check`: passes.
- The mix: −14.5 LUFS integrated, −2.7 dB peak, with no silences over 2.5 s.
- The sound was measured, not heard.

## Kept warnings
- `nested_media_start_basis_ambiguous`: the video start times are local to each chapter, on purpose.
- `text_below_floor` on the "out of 40" badge: it is small only during the 0.5 s while the tablet exits.

## Weakest parts, and what I'd change with more time
- **57–100 s is about 43 s of tablet footage in a row**, with Ahmes small in the corner. This is the evidence section; with more time I'd add one cartoon beat between the break-him tests and Thoth.
- **The footage text is small on a phone.** It reads fine on a laptop.

## How to change it
Edit `build.py`, then run `python3 build.py`, `hyperframes check` and `hyperframes render`. Edits made in the desktop app are overwritten the next time `build.py` runs.
