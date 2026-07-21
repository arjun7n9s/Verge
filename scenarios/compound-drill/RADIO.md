# Compound drill — radio recording guide

Fictional plant copy only: **Meridian Process Unit**. Speak bay codes **B-04** / **B-05** — never real site names.

## Setup

- Close mic, quiet room, natural radio pace (not theatrical).
- Melia plant langs: `en`, `hi`, `ta`, `ur`, plus one of `bn` or `mr`.
- Say **B-04**, **gas** / **smell**, **LEL**, and **hold** clearly so fusion lexicon hits (Latin codes OK inside Hindi/Tamil/Urdu/Bengali).
- Save as 16-bit PCM WAV (or any common WAV), mono or stereo, ~16–48 kHz.
- Place files under `scenarios/compound-drill/radio/` with the exact names below.

Until files land, the demo injects the English `text` fallbacks from `scenario.yaml` into the live voice path (degraded; Melia multilingual is the summit win).

## Scripts

### 1. `r01_en_permit.wav` — W-202 Permit desk · EN · ~12s

> Permit desk to bay B-04 — hot work is active, keep the area clear of unnecessary personnel.

### 2. `r02_hi_smell.wav` — W-101 Field tech · HI · ~15s

Hindi: report a **smell of gas** near **B-04**, ask control to check **LEL**. Keep `B-04` and `LEL` clearly spoken (Latin is fine).

Example English sense (do not record this English version if recording Hindi):

> Near B-04 there is a smell of gas — control, please check LEL.

### 3. `r03_ta_busy.wav` — W-102 Welder · TA · ~12s

Tamil: still finishing the weld / job in B-04, ask to wait — **people still in bay**. Include **B-04**.

### 4. `r04_ur_concern.wav` — W-103 Helper · UR · ~12s

Urdu: smell stronger near the line, request check. Include **B-04** / gas / smell.

### 5. `r05_en_hold.wav` — W-201 Control · EN · ~12s

> Control to B-04 — hold hot work, clear the bay, confirm LEL.

### 6. `r06_bn_or_mr_clear.wav` — W-301 Rover · BN or MR · ~10s

Short confirm leaving / bay clearing. Include **B-04**.

## Playback order (orchestrator)

| Cue | File | Beat |
|-----|------|------|
| ~0:45 | r01 | Hot-work permit chatter |
| ~1:25 | r02 | Weak smell / LEL check |
| ~1:55 | r03 | People still in bay |
| ~2:10 | r04 | Smell stronger |
| ~2:30 | r05 | Hold work / clear bay |
| ~2:55 | r06 | Confirm clearing |
