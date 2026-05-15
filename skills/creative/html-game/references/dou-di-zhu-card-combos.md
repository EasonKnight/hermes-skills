# 斗地主 (Fight the Landlord) — Card Combination Reference

Full combination detection from the 斗地主 HTML game built in this session.

## Rank Order

```
3 4 5 6 7 8 9 10 J Q K A 2 SmallJoker BigJoker
```
Sort values: 3→3, 4→4, ... J→11, Q→12, K→13, A→14, 2→15, Small→16, Big→17

## Card Combinations

| Type | Cards | Example | Notes |
|------|-------|---------|-------|
| single | 1 | 5♠ | Any single card |
| pair | 2 | 7♠ 7♥ | Two same rank, not jokers |
| triple | 3 | K♠ K♥ K♦ | Three same rank |
| triple1 | 4 | KKK + 5 | Triple + any single kicker |
| triple2 | 5 | KKK + 77 | Triple + pair kicker |
| straight | 5-12 | 3-4-5-6-7 | Consecutive singles, no 2 or jokers |
| consecPairs | 6-20 | 33-44-55 | 3+ consecutive pairs, no 2 or jokers |
| airplane | 6+ | 333-444 | 2+ consecutive triples |
| airplane1 | 4+3k | 333-444 + 5-6 | Airplane + 1 kicker per triple |
| airplane2 | 5+3k | 333-444 + 55-66 | Airplane + 1 pair per triple |
| four2 | 6 | 4444 + 5 + 6 | Four + 2 singles |
| four22 | 8 | 4444 + 55 + 66 | Four + 2 pairs |
| bomb | 4 | 8888 | Four of a kind, beats everything except rocket/bigger bomb |
| rocket | 2 | Small + Big | Both jokers, beats everything |

## Combo Detection Algorithm

```javascript
function getCombination(cards) {
  let n = cards.length;
  if (!n) return null;

  // Get rank counts
  let rankCounts = {};
  for (let c of cards) rankCounts[c.sortValue] = (rankCounts[c.sortValue] || 0) + 1;

  // Check each combo type from simplest to most complex:
  // 1. rocket (n===2, ranks=[16,17])
  // 2. single (n===1)
  // 3. pair (n===2, one rank, < 16)
  // 4. triple (n===3, one rank)
  // 5. bomb (n===4, one rank, < 16)
  // 6. triple1 (n===4, counts=[3,1])
  // 7. triple2 (n===5, counts=[3,2])
  // 8. straight (n>=5, all counts===1, consecutive, last rank < 15)
  // 9. consecPairs (n>=6 && n%2===0, all counts===2, consecutive)
  // 10. airplane variants (tripleRanks, consecutive, kicker matching)
  // 11. four2 (n===6, counts=[4,1,1])
  // 12. four22 (n===8, counts=[4,2,2])
}
```

## Can Beat Logic

```javascript
function canBeat(combo, current) {
  if (!combo) return false;
  if (!current) return true;        // leading
  if (combo.type === 'rocket') return true;
  if (combo.type === 'bomb') {
    if (current.type === 'rocket') return false;
    if (current.type === 'bomb') return combo.rank > current.rank;
    return true;                    // bomb beats any non-rocket
  }
  if (current.type === 'rocket' || current.type === 'bomb') return false;
  // Same type, same length, higher rank
  return combo.type === current.type && combo.len === current.len && combo.rank > current.rank;
}
```

## Game Flow

```
Dealing (17 each + 3 reserve)
    ↓
Bidding (random starter, counter-bid on next players)
    ↓
Landlord gets 3 reserve cards (shown face-up)
    ↓
Landlord leads (lastPlay = null)
    ↓
Play → next player → play or pass
    ↓
2 consecutive passes → last active player leads again
    ↓
[repeat until someone runs out of cards]
    ↓
Win: first empty hand wins
    • Landlord wins alone
    • Farmers win together (either farmer empties hand first)
```

## Turn Flow State Machine

```
playCards(player, cards):
  • Remove cards from hand
  • Set lastPlay, lastActivePlayer, consecutivePasses=0
  • Clear all played displays
  • Render new cards in player's area
  • Check win condition (hand empty → endGame)
  • Show type name in status
  • Set next player timer

passTurn(player):
  • Show "⏭ 不要" in player's area
  • Increment consecutivePasses
  • If consecutivePasses >= 2 AND lastActivePlayer >= 0:
    → Reset: lastPlay = null, consecutivePasses = 0
    → lastActivePlayer leads again
  • Else: next player's turn

botTurn(player):
  • If lastPlay exists and played by another: follow (beat it)
  • If lastPlay is null or self: lead
  • aiChoosePlay → playCards or passTurn

Human turn:
  • Enable selection UI + timer (30s)
  • Play button: validate combo, check canBeat
  • Pass button: only if currentPlay exists (can't pass when leading)
  • Hint button: cycle through valid plays
```
