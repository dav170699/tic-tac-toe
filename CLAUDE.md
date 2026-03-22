# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Single-file web game: `tictactoe.html` — no build step, no dependencies, no package manager.

To play: open `tictactoe.html` directly in a browser, or run:
```
powershell -command "Start-Process 'C:\Users\david\Documents\claude projets\tictactoe.html'"
```

## Git & GitHub

**Commit and push after every meaningful change** — do not batch up work. This ensures nothing is lost and the GitHub history always reflects current progress.

```bash
git add <files>
git commit -m "concise description of what changed and why"
git push
```

Commit message rules:
- Use the imperative mood ("Add", "Fix", "Update", not "Added" or "Fixes")
- First line ≤ 72 characters, describes *what* and *why*, not *how*
- No vague messages like "update" or "fix stuff"

Remote: https://github.com/dav170699/tic-tac-toe

## Architecture

Everything lives in `tictactoe.html` as a single self-contained file (no build step, no dependencies).

### Screens
The UI is split into named screen divs toggled by `showScreen(id)`. Only one is visible at a time (`.screen.active`):
- `#game-screen` — the main 2-player / vs-CPU game
- `#training-hub` — level select (Beginner / Advanced / Expert)
- `#lesson-screen` — slide-based tips with demo boards
- `#puzzle-screen` — find-the-correct-move challenges
- `#cpu-battle-screen` — full game vs level-appropriate CPU
- `#level-complete` — congrats + unlock next level

### Core game state (global)
- `board[]`, `current`, `gameOver`, `mode`, `scores` — standard game state
- `makeMove(i)` — places mark, checks win/draw, switches turn
- `checkWin()` — tests all 8 combos from `WINS` constant
- `minimax()` / `bestMove()` — unbeatable AI (reused by Expert CPU battle)
- `setMode('pvp'|'ai')` — switches mode and resets

### Training state (global)
- `trainingLevel`, `slideIndex`, `puzzleIndex`, `puzzlesPassed`
- `trainingProgress` — `{ 1: {unlocked, completed}, 2: ..., 3: ... }` — persisted to `localStorage` key `ttt_training`
- `loadProgress()` / `saveProgress()` — read/write localStorage

### Training data (constants)
- `LESSONS[1|2|3]` — array of slides per level, each with `board[]`, `highlight[]`, `priority{}`, `title`, `text`
- `PUZZLES[1|2|3]` — array of puzzles per level, each with `board[]`, `player`, `correctMoves[]`, `instruction`

### Training flow functions
- `openTraining()` → `renderHub()` → `startLesson(lvl)` → `renderSlide()` → `nextSlide()` → `startPuzzleTest(lvl)` → `renderPuzzle()` → `checkPuzzleAnswer(i)` → `startCPUBattle(lvl)` → `completeLevel(lvl)`
- CPU difficulty: `randomMove()` (Beginner), `greedyMove()` (Advanced), `bestBattleMove()` using `battleMinimax()` (Expert)
