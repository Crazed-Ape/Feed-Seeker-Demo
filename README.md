# Feed-Seeker-Demo

A made-up archive that Feed Seeker plays as a live demo: a week at a small board-game studio, told a message at a time, with a fresh cast and world on every run.

Everything in it is fiction. No real person, company or place is named.

## What's here

1. `source/`: the demo's source: the storylines, the cast slots, the name lists, the tips, the skills, and the assets (one folder per asset, `source/assets/<asset id>/<file name>`).
2. `demo/bundle.json` and `demo/assets/`: what Feed Seeker loads, built from `source/` by the Feed Keeper demo compiler. Never edited by hand.
3. `archive.json`, `files/` and `quests/`: a plain snapshot of one storyline, so a Seeker without demo mode still shows a real archive.

## Changing the demo

Edit `source/`, then rebuild with the compiler (`tools/demo/compile.py <this repo>` in Feed Keeper), which also checks the result. Every change goes through a pull request.
