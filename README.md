# Stochastic domestic hot water usage profile generator

This repository implements a **stochastic domestic hot water (DHW) profile generator** based on electric water heater usage.

It produces realistic hourly or 15‑minute hot water demand time series for a full year by combining:

- empirically derived **daily and seasonal DHW patterns** (`DomesticHotWaterProfile`), and
- a **stochastic draw‑off model** per household (`IndividualHotWaterProfile`) driven by yearly electric energy use.

Generated profiles can be exported to CSV and quickly visualized.

---

## Features

- Generate DHW profiles for one or **multiple yearly electric DHW energies** (kWh).
- Stochastic allocation of individual draw‑offs over the year while preserving:
  - daily shape (weekday/weekend/holiday), and
  - monthly/seasonal variation.
- Output as:
  - one CSV per yearly energy value, and
  - one combined CSV with all profiles as columns.
- Minimal matplotlib visualization:
  - full‑year example profile,
  - first‑week comparison for all energies,
  - average daily profile vs. day of year.

The core generation logic is implemented in:

- `domestic_hot_water/domestic_hot_water_profile.py`

and is used by the example script:

- `generate_network_config.py`

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd DHW_profile
```

### 2. Create and activate a virtual environment (optional but recommended)

```bash
python -m venv venv
venv\Scripts\activate  # on Windows
# source venv/bin/activate  # on Linux/macOS
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This will install (among others):

- `pandas`
- `numpy`
- `matplotlib`
- `holidays`

---

## Configuration

The code is configured via `config/config.ini` (or another INI file if you pass it on the command line). A minimal example:

```ini
[path]
input = D:/work/RecOpt/DHW_profile/input
network = D:/work/RecOpt/DHW_profile/output

[time]
simulation_year = 2019
resolution = 1h  ; or 15min

[domestic_hot_water]
; Physical parameters used by IndividualHotWaterProfile
loss_coefficient = 0.9
stored_water_temp = 50
cold_water_temp = 10
hot_water_temp = 40

; List of yearly electric energies for DHW (kWh)
; Used by generate_network_config.py
e_yearly_list = 1000,1500,2000
```

### Important paths

- `path.input`  — must contain `dhwp.txt` (the statistical base DHW pattern file).
- `path.network` — used as the **output directory** where generated CSV profiles are written.

### Time settings

- `time.simulation_year` — calendar year to simulate.
- `time.resolution` — currently supports `1h` and `15min`.

### DHW physical parameters

These are used by `IndividualHotWaterProfile` to relate electric energy to water volume and temperature:

- `loss_coefficient`
- `stored_water_temp`
- `cold_water_temp`
- `hot_water_temp`

---

## Usage

After installing dependencies and defining `config/config.ini`, run:

```bash
python generate_network_config.py
```

By default, the script will:

1. Read configuration from `config/config.ini`.
2. Use `domestic_hot_water/domestic_hot_water_profile.py` to build the base DHW shape for the chosen year.
3. For each yearly energy in `domestic_hot_water.e_yearly_list`, generate an individual stochastic DHW profile.
4. Write each profile and a combined file to `path.network`.
5. Open three simple plots in a matplotlib window.

### Command line config override (optional)

You can pass a different config file as the third command line argument (see `utility/configuration.py`):

```bash
python generate_network_config.py arg1 arg2 path/to/other_config.ini
```

Only the presence and structure of the config file matters; the first two arguments are ignored by this script but may be used in other workflows.

---

## Script details: `generate_network_config.py`

The main entry point is `main()`:

- Reads:
  - `path.input`, `path.network`
  - `time.simulation_year`, `time.resolution`
  - `domestic_hot_water.e_yearly_list` (list of yearly energies in kWh)
- Constructs a base yearly DHW pattern using `DomesticHotWaterProfile`.
- Uses `IndividualHotWaterProfile.get_individual_profile_from_e_yearly(e_yearly, year)` to create a profile for each energy.

### Output files

For `e_yearly_list = [1000, 1500, 2000]` and `simulation_year = 2019`, the script writes:

- `path.network/dhw_profile_2019_1000kWh.csv`
- `path.network/dhw_profile_2019_1500kWh.csv`
- `path.network/dhw_profile_2019_2000kWh.csv`
- `path.network/dhw_profiles_2019_combined.csv`

Each per‑profile CSV contains:

- A DateTime index (full year at chosen resolution).
- One column: `Hot water [l/h]`.

The combined CSV contains:

- Same DateTime index.
- One column per yearly energy, named e.g. `1000kWh`, `1500kWh`, etc.

### Visualization

The script generates three figures:

1. **Full‑year profile** for one representative energy (first in the list).
2. **First week bundle** — all profiles over the first 7 days, plotted together.
3. **Average daily profile vs. day of year** for each yearly energy.

These are intended as quick sanity checks and illustrative plots, not as a full visualization package.

---

## Core modules

### `domestic_hot_water/domestic_hot_water_profile.py`

Contains two main classes:

- `DomesticHotWaterProfile`
  - Builds a normalized yearly DHW pattern using monthly multipliers, weekday/weekend/holiday differences, and hourly distributions from `dhwp.txt`.
  - Methods like `get_day()` and `return_yearly_profile()` keep the original stochastic and seasonal logic intact.

- `IndividualHotWaterProfile`
  - Maps yearly electric energy used for DHW to a yearly hot water volume, number of occupants, and tank size.
  - Uses discrete draw‑off statistics (short/medium/shower/bath) to randomly distribute individual events across the base profile.
  - Key public methods:
    - `get_individual_profile_from_e_yearly(e_yearly_controlled, year)`
    - `calc_number_of_occupants(e_yearly_controlled)`
    - `calc_heater_size(n_people, e_yearly_controlled, measurement=None)`

### `domestic_hot_water/domestic_hot_water_definitions.py`

Holds supporting enums and data for the draw‑off model:

- `DiscreteProfile` and `ContinuousProfile`
- `draw_off_statistics` and `_l_per_discrete_profile`
- `multiply_heavy_profile(vol_water_l)`
- `WaterHeaterData` — helper to select appropriate electric water heater size from a CSV file.

### `utility/configuration.py`

A thin wrapper around `configparser` providing convenient `get`, `getint`, `getfloat`, and `getarray` helpers used by the rest of the code.

### `utility/definitions.py`

Utility helpers for seeding randomness and simple filename helpers.

---

## Data requirements

At minimum, you must provide:

- `dhwp.txt` in `path.input` — the domestic hot water pattern definition file used by `DomesticHotWaterProfile`.
- `water_heater.csv` (path referenced in `WaterHeaterData` inside `domestic_hot_water_definitions.py`), typically under the input path referenced in `config.ini`.

These files are not included here; refer to your local project or data source for their structure and content.

---

## How to cite

If you use this DHW profile generator in academic work or reports, please cite it as:

> Barancsuk L., *Stochastic Domestic Hot Water Usage Profile Generator* (version 1.0), GitHub repository, 2025. Available at: https://github.com/Lilol/stochastic_domestic_hot_water_usage_profile


You can also use a BibTeX-style entry:

```bibtex
@misc{dhw_profile_generator,
  author       = {Barancsuk L.},
  title        = {Stochastic Domestic Hot Water Usage Profile Generator},
  year         = {2025},
  howpublished = {GitHub repository},
  note         = {Version 1.0},
  url          = {https://github.com/Lilol/stochastic_domestic_hot_water_usage_profile}
}
```

---

## License

See `LICENSE` for licensing information.
