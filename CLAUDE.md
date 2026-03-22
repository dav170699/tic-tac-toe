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

Everything lives in `tictactoe.html` as a single self-contained file:

- **HTML** — minimal structure (board div, scoreboard, mode toggle, restart button)
- **CSS** — dark theme, grid layout, animations (all inline in `<style>`)
- **JS** — game logic inline in `<script>`:
  - `board[]` — 9-element array representing the grid state
  - `makeMove(i)` — places current player's mark, checks win/draw, switches turn
  - `checkWin()` — tests all 8 winning combos from the `WINS` constant
  - `minimax()` — recursive minimax for the unbeatable CPU opponent
  - `bestMove()` — entry point for AI, picks the highest-scoring move
  - `setMode('pvp'|'ai')` — switches game mode and resets
  - `resetGame()` — clears board without resetting scores; `init()` also resets scores
