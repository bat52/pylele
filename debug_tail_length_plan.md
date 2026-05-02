# Debug Plan: LeleTail.stl Length Mismatch

## Problem Summary

When running `pytravelele.sh`, the generated `LeleTail.stl` piece is longer than expected and does not fit properly into the hole in the body. The tail piece extends too far forward (toward the neck), overlapping with the body area instead of fitting neatly into the tail-end cutout.

## Root Cause Analysis

### Key Configuration Values (from debug output)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `scaleLen` | 330.0 mm | Scale length (TRAVEL scale) |
| `wallTck` | 6.0 mm | Wall thickness |
| `chmFront` | 126.0 mm | Chamber front length |
| `chmBack` | 15.75 mm | Chamber back length |
| `tnrFront` | 11.0 mm | Tuner front dimension |
| `tnrBack` | 11.0 mm | Tuner back dimension |
| `bodyBackLen` | 37.75 mm | Body back length (TRAVEL: no wallTck added) |
| `tailX` | 367.75 mm | End of body (scaleLen + bodyBackLen) |
| `chmBackX` | 345.75 mm | Chamber back X position (scaleLen + chmBack) |
| `tailLen` | 22.0 mm | Distance from chamber back to end |
| `endWth` | 65.0 mm | End flat width |
| `rimWth` | 3.0 mm | Rim width (wallTck/2) |
| `flat_body_thickness` | 20.0 mm | Body thickness |

### The Bug: `2*tailLen` in `tail.py`

In `tail.py`, the inner box (`inrTop`) is created with:

```python
inrTop = self.api.box(2*tailLen, tail_width, midBotTck)\
    .mv(tailX - rimWth - tailLen, 0, -midBotTck/2)
```

This creates a box with **width = 2 * tailLen = 44.0 mm**, positioned so its right edge is at `tailX - rimWth = 364.75`.

**Resulting x-range of the inner box: [320.75, 364.75]**

But the chamber back is at **x = 345.75**. This means the inner box extends **25 mm past the chamber back** into the body area!

### What the Tail Should Be

The tail should only span from the chamber back to the end of the body:

- **Expected inner box x-range: [345.75, 364.75]** (width = 19.0 mm = tailLen - rimWth)
- **Expected inner box width: tailLen - rimWth = 19.0 mm** (not `2*tailLen = 44.0 mm`)

### Why This Happened

The `2*tailLen` multiplier appears to be a bug. The inner box should span from `chmBackX` to `tailX - rimWth`, which is a distance of `tailLen - rimWth`, not `2*tailLen`.

The same `2*tailLen` pattern is also used for the rounded bottom cylinders (`inrBot`), which would cause the same issue for non-flat body types.

## Debug Steps

### Step 1: Add Debug Prints to `tail.py`

Add print statements to `LeleTail.gen()` to output:
- `tailX`, `chmBackX`, `tailLen`
- `endWth`, `rimWth`, `tail_width`
- `midBotTck`
- Box positions and x-ranges for `extTop` and `inrTop`

### Step 2: Add Debug Prints to `config.py`

Add print statements to `LeleConfig.__init__()` to output:
- `scaleLen`, `wallTck`
- `chmFront`, `chmBack`
- `tnrFront`, `tnrBack`
- `bodyBackLen`, `tailX`
- `rimWth`, `extMidBotTck`, `bodyWth`
- `neckLen`, `neckWth`, `neckWideAng`

### Step 3: Add Debug Prints to `body.py`

Add print statements to `genBodyPath()` to output:
- `scaleLen`, `neckLen`, `neckWth`
- `bodyWth`, `bodyBackLen`, `endWth`
- `bBkLen`, `eWth`
- Body path end position

### Step 4: Generate STL Files

Run both body and tail generation with the travelele configuration parameters:

```bash
# Generate tail
python3 src/pylele/pylele2/tail.py \
  -bt travel -wt 6 -cbar 0.125 -s TRAVEL \
  -t turnaround -e 65 -cbr 1.5 -fbt 20 -fbsr 0.6 \
  -wah -wsl 35 -i mock -E

# Generate body
python3 src/pylele/pylele2/body.py \
  -bt travel -wt 6 -cbar 0.125 -s TRAVEL \
  -t turnaround -e 65 -cbr 1.5 -fbt 20 -fbsr 0.6 \
  -i mock -E
```

### Step 5: Analyze Output

Compare the tail's x-range with the body's end position:
- Body path ends at `x = scaleLen + bBkLen = 367.75`
- Tail inner box spans from `x = 320.75` to `x = 364.75`
- Chamber back is at `x = 345.75`
- The tail extends 25 mm past the chamber back into the body

## Proposed Fix

### Fix 1: Correct the inner box width in `tail.py`

Change the inner box from `2*tailLen` width to `tailLen - rimWth` width, and adjust the position to span from `chmBackX` to `tailX - rimWth`:

```python
# Current (buggy):
inrTop = self.api.box(2*tailLen, tail_width, midBotTck)\
    .mv(tailX - rimWth - tailLen, 0, -midBotTck/2)

# Proposed fix:
inrTop = self.api.box(tailLen - rimWth, tail_width, midBotTck)\
    .mv((chmBackX + tailX - rimWth) / 2, 0, -midBotTck/2)
```

### Fix 2: Apply the same fix to the rounded bottom cylinders

For non-flat body types, the same `2*tailLen` pattern is used for `inrBot`:

```python
# Current (buggy):
inrBot = self.api.cylinder_x(2*tailLen, endWth/2 - rimWth)\
    .scale(1, 1, botRat)\
    .mv(tailX - rimWth - tailLen, 0, -midBotTck)

# Proposed fix:
inrBot = self.api.cylinder_x(tailLen - rimWth, endWth/2 - rimWth)\
    .scale(1, 1, botRat)\
    .mv((chmBackX + tailX - rimWth) / 2, 0, -midBotTck)
```

### Fix 3: Verify the cut tail also uses correct dimensions

The cut version (`isCut=True`) uses `10` instead of `rimWth` for the outer box width. This should also be verified for correctness.

## Verification

After applying the fix:
1. Re-run both body and tail generation
2. Verify the tail x-range is now `[345.75, 364.75]` (19 mm wide)
3. Verify the tail fits within the body's end cutout
4. Run the full `pytravelele.sh` script to verify the assembly works correctly
