---
name: html-game
description: Build interactive, playable HTML games as single self-contained files — card games, board games, turn-based games with AI opponents, and visual game UIs using plain HTML/CSS/JavaScript.
platforms: [windows, macos, linux]
category: creative
---

# HTML Game Development

Build complete, playable HTML games as single files (no build tools, no frameworks, no dependencies). Open directly in any browser. This covers card games, board games, turn-based strategy, puzzle games, and other interactive experiences with AI opponents.

## Architecture Pattern

Every game follows this structure in a single HTML file:

```
┌─────────────────────────────────────┐
│ Game Engine (pure JS)               │
│  • Data: cards, board, state        │
│  • Logic: rules, combo detection    │
│  • AI: opponent strategy            │
│  • Lifecycle: init, turn, end       │
├─────────────────────────────────────┤
│ UI Layer (CSS + DOM)                │
│  • Layout: player areas, controls   │
│  • Rendering: cards, board, tokens  │
│  • Interaction: click, select, drag │
│  • Feedback: status, timer, scores  │
├─────────────────────────────────────┤
│ HTML Structure                      │
│  • Game container (#app)            │
│  • Player areas                     │
│  • Controls & overlays              │
│  • Timer & status bar               │
└─────────────────────────────────────┘
```

### Why Single File

- Zero setup: user double-clicks and plays
- No build, no server, no install
- Easy to share: one file, everything included
- Works offline, works on any browser

## Development Workflow

### Step 1: Plan the Game

Define before coding:
- Rules (card types, win conditions, turn order)
- Number of players vs AI
- UI layout (players positioning)
- AI strategy depth

For Chinese card games like 斗地主, also define:
- Bidding phase (who starts, forced landlord rules)
- Card combinations (single, pair, triple, straight, bomb, rocket, etc.)
- Pass/reset logic (consecutive passes reset to last active player)

### Step 2: Build the Engine First

Write the game engine as pure functions with no DOM dependencies:

```javascript
// Card representation
class Card {
  constructor(suit, rank, id) { ... }
  get sortValue() { ... }  // for sorting
}

// Deck creation and shuffling
function createDeck() { ... }
function shuffle(arr) { ... }
function sortCards(cards) { ... }

// Combination detection
function getCombination(cards) { ... }
function canBeat(combo, current) { ... }

// Find valid plays from a hand
function findPlays(hand, currentPlay) { ... }

// AI strategy
function aiChoosePlay(hand, currentPlay, gameState) { ... }
```

Key invariants:
- All functions return data (no DOM)
- Card objects have unique IDs for selection tracking
- Sort values enable numeric comparison (3→3, 4→4, ... J→11, Q→12, K→13, A→14, 2→15)
- Jokers get their own sort values (Small=16, Big=17)

### Step 3: Build the UI

CSS layout patterns for card games:

- **Card rendering**: Use `.card` divs with absolute positioning, styled with CSS gradients for the face
- **Card selection**: Toggle `.selected` class → CSS transform `translateY(-22px)`
- **Player layout**: Three-player card games use bottom (human), top-left (bot), top-right (bot)
- **Face-down cards**: Use gradient background with a placeholder icon
- **Played cards area**: Overlay in center or adjacent to each player
- **Timer bar**: Bottom edge of game area, width shrinks over time
- **Overlay**: Full-screen semi-transparent for game-over state

```css
.card.selected { transform: translateY(-22px) !important; }
.card.face-down { background: linear-gradient(135deg, #1a4a8a, #2a6aba); }
.played-cards .card { animation: playCard 0.25s ease-out; }
```

### Step 4: Wire Game State

The game object holds all mutable state:

```javascript
let game = {
  phase: 'dealing',     // dealing → bidding → playing → ended
  players: [[], [], []], // 0=human, 1=bot1, 2=bot2
  currentPlayer: 0,
  lastPlay: null,        // {cards, player, combo}
  lastActivePlayer: -1,  // who actually played cards last (not passed)
  consecutivePasses: 0,  // reset on each play, triggers lead-back on 2
  playerCardCounts: [17, 17, 17],
  landlord: -1,
  reserveCards: [],
  waitingForHumanAction: false,
  selectedCards: new Set(),
};
```

### Step 5: Iterate with `patch`

After the initial `write_file`, use `patch` for fixes rather than rewriting the whole file. This preserves context and is more efficient.

Common patches during game development:
- Fixing pass/reset logic (consecutive pass tracking)
- Fixing AI strategy (play selection, bomb usage)
- Fixing combo detection (edge cases in airplane, four-with-two)

## AI Strategy Patterns

For turn-based games, a simple but effective AI:

```javascript
function aiChoosePlay(hand, currentPlay, gameState) {
  let plays = findPlays(hand, currentPlay);
  if (!plays.length) return null;  // must pass

  // Following: pick smallest winning play
  if (currentPlay) {
    let sorted = [...plays].sort((a,b) => compareCombos(a,b));
    // Avoid wasting bombs unless critical
    if (hand.length > 6 && opponentHasManyCards) {
      let nonBombs = plays.filter(p => !isBomb(p));
      if (nonBombs.length) return nonBombs[0];
    }
    return sorted[0];
  }

  // Leading: prefer efficient clear patterns
  // 1. Straights/consecutive pairs (clear many cards)
  // 2. Triples with kickers
  // 3. Pairs
  // 4. Singles
  // 5. Bombs (last resort when leading)
}
```

### Hand Strength Evaluation

For bidding decisions (who becomes landlord in 斗地主):

```javascript
function evaluateHand(hand) {
  let score = 0;
  let rankCounts = {};
  for (let c of hand) rankCounts[c.sortValue] = (rankCounts[c.sortValue] || 0) + 1;
  for (let [r, cnt] of Object.entries(rankCounts)) {
    let rn = parseInt(r);
    if (cnt === 4) score += 30;    // bomb
    if (rn === 17) score += 20;    // Big Joker
    if (rn === 16) score += 15;    // Small Joker
    if (rn >= 14) score += (rn - 13) * 5;  // A=+5, 2=+10
  }
  let highCards = Object.keys(rankCounts).filter(r => parseInt(r) >= 12).length;
  score += highCards * 3;
  return score;
}
```
- Threshold ~42 to bid, ~55+ for counter-bid (raising threshold on counter-bid avoids overpaying for weak hands)
- Default landlord (no one bid): the starting bidder is forced

## Pitfalls

### Pass/Reset Logic
The most common bug. In a 3-player game:
- Player A plays → lastActivePlayer = A, consecutivePasses = 0
- Player B passes → consecutivePasses = 1
- Player C passes → consecutivePasses = 2 → **RESET**: A leads again
- On reset: set `lastPlay = null`, `consecutivePasses = 0`, next turn = `lastActivePlayer`

### Selection Tracking
- Use a `Set` of card IDs for selections (fast add/delete/clear)
- Clear selection on play/pass
- Update positions with `selected` class for visual feedback

### Timer Management
- Only show timer bar during human turn
- Clear interval on play/pass
- Auto-play on timeout (play smallest valid combo or pass)

### Card Rendering Overlap — Avoid `position: absolute` Layout

**Do NOT use `position: absolute` + calculated `left` for card overlap.** This caused a bug on Windows where cards rendered blank until the user clicked (triggering a re-render). The browser's initial absolute-position layout didn't paint correctly.

**✅ Use flexbox + negative margin instead:**

```css
#human-cards {
  display: flex;
  flex-wrap: nowrap;
  align-items: flex-start;
  justify-content: center;
}

.card {
  display: inline-flex;
  flex-shrink: 0;
  vertical-align: top;
}
```

```javascript
// In render function — negative margin creates overlap
let overlap = n > 7 ? Math.max(6, Math.min(50, 520 / n)) : 50;
div.style.cssText = `position:relative;display:inline-flex;margin-left:${i===0?'0':'-'+overlap+'px'};top:${isSelected?'0px':'22px'};z-index:${n-i};`;
```

This approach:
- Lets the browser handle positioning naturally
- Uses `z-index: (n-i)` so later cards stack on top of earlier ones
- Uses `top` for selection lift (no CSS `transform` needed)
- First card has no negative margin, rest overlap by calculated amount

**Selection visual**: Raise selected cards by changing `top` from `22px` to `0px` (no CSS transform). Remove `.card.selected { transform: translateY(-22px) }` to avoid double-position conflicts.

**For bot face-down cards**: Keep `position: absolute` inside a `position: relative` container — these are just stacked rectangles with no interaction, so absolute positioning is fine. Use `cursor: default`.

**Sort cards** by descending rank (`b.sortValue - a.sortValue`) for natural display order — highest cards (Big Joker, Aces) on the left.

**Avoid styling conflicts**: Don't mix `position: absolute` with `display: flex` on the same element. Use inline `cssText` to override class styles when switching between human cards (flex) and bot cards (absolute).

### Turn Flow Race Conditions
- Use `setTimeout` delays (800-1000ms) between bot turns so animations render
- Always check `game.phase !== 'playing'` to prevent actions after game end
- Set `waitingForHumanAction = false` immediately on play/press, not in setTimeout

### Bidding Phase (Chinese Card Games)
- Track `bidRound` (who started bidding) to detect full-circle (= forced landlord)
- Bot bidding uses hand strength evaluation + randomness threshold
- Human bidding shows UI overlay with buttons, not game cards

## Related Skills

- `sketch` — Rapid HTML mockups for design comparison (complement: sketch for layout exploration, this skill for full game implementation)
- `p5js` — p5.js-based interactive sketches and generative art
- `claude-design` — One-off HTML artifacts (landing pages, decks)
