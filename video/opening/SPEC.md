# Teach Ahmes: animated opening (about 26 s)

GOAL:    In 26 s a judge gets the whole idea: a child's words become a robot's code, and a bad rule is stopped by a sandbox without breaking anything. Then the film cuts to the real app.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    26.3 s x 30 = 789 frames. The voices are the clock. The music (ElevenLabs, 104 bpm) sits under them.
LOOK:    The app's own medium: an exercise book.
         - Ground: #F7FAFD with a #D9E6F3 grid line every 60 px.
         - Ink: #16224A.
         - Lapis #2449A8 and gold #E0A526 belong to Ahmes.
         - Gold also marks the child's words, and nothing else.
         - Red #C6432A marks wrong answers only. Faience #12857D marks right answers and the sandbox only.
         - Type: Nunito 800/900 (numbers at 150 px, speech at 46 px, the title at 132 px). Code is JetBrains Mono at 30 px on #16224A.
         - No shadows, glow or grain.
OBJECTS: - Ahmes is the in-app SVG robot (web/index.html), drawn 700 px wide and fills 76% of the frame height.
         - The homework card is a white index card with a 2 px #C9D7EA edge and a 28 px radius.
         - The child is off screen. Her words are a speech bubble whose tail points down out of the frame, towards the viewer.
         - The sandbox is a faience box with an 8 px edge that drops over Ahmes. Its tab says "Sandbox" and shows a timer.
MOTION:  - Arrivals: expo.out. Drops and exits: power3.in. Character springs: back.out(1.6) on position and scale only.
         - Glyphs fly 0.55 s, 0.06 s apart.
         - The spin is power2.in to 1440 degrees, then a damped wobble.
SHOTS:   1. 0.0–6.6, the bug: Ahmes points and circles 0.45 (voice a1); a red ✗ stamps it at 5.2; Ahmes does a confused take.
         2. 6.6–13.3, teaching: the bubble rises; "Look at the tenths first." types in word by word (c1); the words fly into his antenna and become code in the same slot; he circles 0.5 in faience (a2) and hops.
         3. 13.3–23.4, the dizzy rule: the card swaps to 1/2 + 1/3; the bubble shows c2; the words become a while loop; the sandbox drops; he spins while the bottoms double faster and faster; at 3.0 s the box stops him ("Stopped" stamp), lifts away, and the card resets to his old brain (a3).
         4. 23.4–26.3, the name: "Teach Ahmes" lands letter by letter, then "Children teach. A sandbox keeps it safe."
BANNED:  The defaults in spec.md, plus: a dark ground, a drawn child's face, real children's voices, any studio-named anime style, and text that moves while it is read.
QA:      Frames at 2.0, 5.4, 7.8, 9.6, 11.5, 15.5, 18.8, 20.5, 22.5 and 25.5 s. Each must read as its shot without the voice.
