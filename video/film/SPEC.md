# Teach Ahmes: the film (storyline A, "Ahmes's school day")

GOAL:    A judge finishes knowing three things: a child's words become real code; a sandbox on Vultr stops bad words without breaking anything; and every claim was shown on the live site.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    151.5 s x 30 = 4545 frames. The voices are the clock. The ElevenLabs score (104 bpm) sits under them at 0.16.
LOOK:    The app's exercise book, the same as the opening.
         - Ground: #F7FAFD with a 60 px #D9E6F3 grid.
         - Ink: #16224A. Lapis and gold belong to Ahmes. Gold also marks the child's words.
         - Red marks wrong answers only. Faience marks the sandbox only.
         - Type: Nunito 800/900. Code is JetBrains Mono at 30 px with ligatures off.
OBJECTS: - Ahmes: the in-app SVG robot.
         - The homework card and the speech bubble, as in the opening.
         - The tablet: a lapis device, 1500 x 844, whose 1460 x 822 screen plays the real Playwright recordings.
         - The sandbox box.
         - Real receipt stamps.
         - The 24/40 and 40/40 badges.
MOTION:  - Arrivals: expo.out. Exits: power3.in. Character springs: back.out(1.6).
         - The tablet goes from off-screen to the right column (0.5 s, expo.out), then to full (0.55 s, power2.inOut).
         - While the tablet is full, Ahmes shrinks to 0.35 in the bottom-left corner and watches.
SHOTS:   Each beat is told once. The cartoon sets it up, and the real footage on the tablet proves it.
         1. 0–19: the bug (0.45), the ✗, then "Look at the tenths first." flies into his head and becomes code.
         2. 19–34: the tablet shows the real retry ("0.5 is bigger!") and the real quiz; a 24/40 badge.
         3. 34–42: "Keep doubling both bottoms…" becomes a while loop; the box drops; he spins; the timer reaches 3.0 s; "Stopped".
         4. 42–57: the box becomes the tablet: the real dizzy stop and his real line.
         5. 57–75: the real "This turn on Vultr" list, then the break-him tests, with the "Killed at 64 MB" and "Network unreachable" stamps.
         6. 75–100: Thoth's real hint card and voice; "the answer is 0.61"; his real "tell me the rule, not the answer".
         7. 100–112: back to the cartoon: 0.943 vs 0.96; the full rule flies in as code.
         8. 112–124: the tablet shows the real 0.96 and the real 40/40 quiz; a 40/40 badge; "I got every one right!"
         9. 124–147: six real lessons, the Vultr architecture, the real parent report.
         10. 147–151.5: "Teach Ahmes", the URL, "Built on Vultr for Agent Rush".
BANNED:  The defaults in spec.md, plus:
         - a drawn child's face, or real children's voices;
         - a drawn sandbox claim with no real footage behind it;
         - two films cut together;
         - text that moves while it is read.
QA:      Frames at 2, 9, 15, 22.5, 27.8, 39, 41, 43, 60, 68.5, 72, 85, 96, 104, 110.6, 117.6, 126, 133, 142 and 149 s.
