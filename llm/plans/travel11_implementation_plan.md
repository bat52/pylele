# Implementation Plan

## [Overview]

Create a new ukulele configuration `travel11` with a travel-style flat body and integrated concealed worm gear tuners sized for the standalone WormGear/WormDrive parts (11 teeth, carved gear, friction shaft), and a corresponding `pytravel11.sh` script that generates both the body assembly and standalone printable STL files.

The existing `-cfg travel` uses the internal `FATWORM` worm mechanism (pylele2's own `LeleWorm` with fatworm dimensions). The new `travel11` will instead use holes/cutouts sized for the external `WormGear`/`WormDrive` parts from `pylele.parts/` (which are derived from "Guitar Tuners that actually work" Thingiverse models), while retaining the travel body shape (solid flat body with oval chamber). The tuners remain concealed in the body volume, matching the travel design philosophy. A new `TunerType.WORM11` entry and `WORM11_TUNER_CFG` will bridge the two worlds by providing dimension metadata for positioning while relying on the existing `WormGear` class for actual cut geometry.

## [Types]

Add one new `TunerType` member and its dimension configuration to `config_common.py`.

### New WormConfig: WORM11_TUNER_CFG

Approximate the bounding dimensions of the WormGear/WormDrive assembly (11 teeth, `carved_gear=True`, `friction_shaft_enable=True`) for positioning calculations in `configure_tuners()`:

| Parameter  | Value | Source / Rationale |
|------------|-------|-------------------|
| `slitHt`   | 31    | Default (unused for cut, placeholder) |
| `slitLen`  | 5     | Small value (unused for cut, placeholder) |
| `slitWth`  | 3     | Default (unused for cut, placeholder) |
| `diskTck`  | 8     | `gear_h = worm_diam = 8` (carved_gear) |
| `diskRad`  | 8.5   | `gear_out_rad = gear_diam/2 + gear_teeth = 5.5 + 3` |
| `axleRad`  | 1.5   | Half of `worm_axle_diameter` default (3.0) |
| `axleLen`  | 6     | Default from WormConfig |
| `driveRad` | 5.3   | `worm_diam/2 + drive_teeth_l/2 + tol = 4 + 0.98 + 0.3` |
| `driveLen` | 11    | `drive_h = worm_diam + gear_teeth = 8 + 3` |
| `driveOffset` | 0  | Not used in same way as LeleWorm |
| `gapAdj`   | 1.5   | Matching FATWORM scaling |
| `tailAdj`  | 0     | No tail adjustment |
| `code`     | `'W11'` | Short identifier |

### New TunerType enum member

```python
class TunerType(Enum):
    # ... existing members ...
    WORM11 = WORM11_TUNER_CFG
```

### New CONFIGURATIONS entry in config.py

```python
'travel11': TRAVEL + WORM11 + [
    '-t', 'worm11',
    '-cbr', '1.2',
    '-nsr', '0.45',
    '-fbsr', '0.55',
    '-fbt', '30',
]
```

Where `WORM11 = ['-t','worm11','-e','90','-g','11'] + WORM_SLIT`

### New script structure

`pytravel11.sh` will:
1. Run `all_assembly.py -cfg travel11` with all separation flags + additional features
2. Generate standalone `WormDrive` (mirrored) with `--teeth 11`
3. Generate standalone `WormGear` (mirrored) with `--teeth 11 --carved_gear --friction_shaft_enable --minkowski_en`

## [Files]

Modify three existing files and create two new files.

### Modified Files

**1. `src/pylele/config_common.py`**
- Add `WORM11_TUNER_CFG = WormConfig(...)` after existing WormConfig definitions (~line 295)
- Add `WORM11 = WORM11_TUNER_CFG` to `TunerType` enum (after line 309)

**2. `src/pylele/pylele2/config.py`**
- Add `WORM11` arg list constant (similar to existing FATWORM, WORM, etc.)
- Add `'travel11'` entry to CONFIGURATIONS dict
- Add reference volume for `'travel11'` in `all_assembly.py` refv dict (but that's in all_assembly.py)
- Update `LeleBodyType` / travel-body handling if needed for new body dimensions

**3. `src/pylele/pylele2/tuners.py`**
- Add import: `from pylele.parts.worm_gear import WormGear`
- Add import: `from pylele.parts.worm_drive import WormDrive`
- In `LeleTuners.gen()`, add `WORM11` case alongside existing `is_worm()` / `is_turnaround()` branches
- New helper method `gen_worm11_tuner(isCut)` that generates a single WORM11 cutout or positive shape using WormGear/WormDrive

**4. `src/pylele/pylele2/all_assembly.py`**
- Add `'travel11'` entry to the `refv` dict with its reference volume

### New Files

**5. `src/pytravel11.sh`**
New shell script following the pattern of `pytravelele.sh`, calling `all_assembly.py -cfg travel11` plus standalone WormDrive and WormGear generation.

## [Functions]

### New Functions

**`LeleTuners.gen_worm11_tuner(isCut: bool = False) -> Shape`** | `tuners.py`
- Creates a `WormGear(isCut=isCut, args=[...])` with parameters: `--teeth 11 --drive_enable --carved_gear --friction_shaft_enable --minkowski_en`
- When `isCut=True`, extends the gear cylinder height to match the flat body thickness so the cut fully pierces the body
- When not isCut, also adds worm key or other details
- Returns the combined shape (gear cylinder + drive worm cut/positive)

**`LeleTuners.gen_worm11_tuners() -> Shape`** | `tuners.py`
- Iterates over `self.cfg.tnrXYZs` and places `gen_worm11_tuner()` at each position
- Applies mirroring based on the position's Y sign (left/right side of body)
- Returns combined shape of all tuner cuts/positives

### Modified Functions

**`LeleTuners.gen()`** | `tuners.py`
- Add new branch: `elif self.cli.tuner_type == TunerType.WORM11.name:` that calls `self.gen_worm11_tuners()` instead of `LeleWorm`

**`pylele_config_parser()`** / `CONFIGURATIONS` | `config.py`
- Add `WORM11` arg list and `'travel11'` configuration entry

**`TunerType` enum** | `config_common.py`
- Add `WORM11 = WORM11_TUNER_CFG` member

## [Classes]

### Modified Classes

**`LeleTuners`** | `tuners.py`
- No new class needed. Add method(s) to handle WORM11 case.
- Update `is_worm()` to return True for WORM11 (since WORM11 is a worm-type tuner)
- Actually, WORM11 uses `WormConfig` so `is_worm()` already returns True.

**`WormConfig`** | `config_common.py`
- No changes needed. WORM11_TUNER_CFG instantiates the existing `WormConfig` class.

## [Dependencies]

No new external packages required. All dependencies already exist in the project.

The `pylele.parts.worm_gear` and `pylele.parts.worm_drive` modules are already present and used by `pytravelele.sh`. They import from `b13d.api.solid`, `solid2`, `pylele.parts.tuner_knob_hole`, etc., all of which are existing dependencies.

## [Testing]

### Unit Testing Approach

1. **WORM11 TunerConfig verification**: Add a test in `test_tuners()` to verify the WORM11 dimensions produce reasonable positions
2. **travel11 configuration test**: Add `'travel11'` to the configuration test loop in `test_all_assembly()` with a reference volume
3. **Bottom assembly test**: Add `'travel11'` to `test_bottom_assembly()` body type tests
4. **Visual validation**: After implementation, run the script and visually inspect the STL to ensure the gear/drive cuts appear correctly in the body

### Reference Volume

The reference volume for `travel11` will be determined by running the mock test after implementation. Use a placeholder value initially, then update with the actual volume from test output.

### Test Updates

- `test_all_assembly()` in `all_assembly.py`: Add `'travel11'` to the test_config loop
- `test_bottom_assembly()` in `bottom_assembly.py`: Optionally add travel11 body test case

## [Implementation Order]

1. **Add WORM11_TUNER_CFG and TunerType.WORM11** to `config_common.py`
2. **Add WORM11 args and travel11 configuration** to `config.py`
3. **Update tuners.py** to handle WORM11 tuner type using WormGear/WormDrive from pylele.parts
4. **Create pytravel11.sh** shell script
5. **Update all_assembly.py** with travel11 reference volume
6. **Run tests** to validate and obtain reference volumes
7. **Iterate** on dimensions if needed based on test output
