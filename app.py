import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Atomic Size Predictor",
    page_icon="⚛️",
    layout="wide"
)

st.title("⚛️ Atomic Size Predictor")
st.write(
    "Compare and arrange four atoms or ions using "
    "reference radius data."
)

BASE = Path(__file__).parent
ATOMIC_FILE = BASE / "neutral_atomic_radii.csv"
IONIC_FILE = BASE / "ionic_radii.csv"


@st.cache_data
def load_csv(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    return df


def find_column(df, possible_names):
    """Find a column despite capitalization or spacing differences."""
    normalized = {
        str(c).strip().lower().replace(" ", "_"): c
        for c in df.columns
    }

    for name in possible_names:
        key = name.lower().replace(" ", "_")
        if key in normalized:
            return normalized[key]

    return None


def prepare_data(df, is_ion):
    symbol_col = find_column(
        df, ["species", "symbol", "ion", "element"]
    )
    radius_col = find_column(
        df, ["radius_pm", "atomic_radius", "ionic_radius",
             "radius", "calculated_radius"]
    )
    charge_col = find_column(
        df, ["charge", "ionic_charge"]
    )
    coord_col = find_column(
        df, ["coordination", "coordination_number"]
    )
    spin_col = find_column(df, ["spin", "spin_state"])

    if symbol_col is None or radius_col is None:
        raise ValueError(
            "Could not identify the species and radius columns. "
            f"Columns found: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["species"] = df[symbol_col].astype(str).str.strip()
    out["radius_pm"] = pd.to_numeric(
        df[radius_col], errors="coerce"
    )

    if charge_col is not None:
        out["charge"] = pd.to_numeric(
            df[charge_col], errors="coerce"
        )
    else:
        out["charge"] = pd.NA if is_ion else 0

    out["radius_type"] = "ionic" if is_ion else "neutral"

    out["coordination"] = (
        df[coord_col].fillna("").astype(str).str.strip()
        if coord_col else ""
    )
    out["spin"] = (
        df[spin_col].fillna("").astype(str).str.strip()
        if spin_col else ""
    )

    out = out.dropna(subset=["radius_pm"]).copy()

    # Do not silently treat missing ionic charges as zero.
    if is_ion:
        out = out.dropna(subset=["charge"])
        out = out[out["charge"] != 0]

    return out


for path in [ATOMIC_FILE, IONIC_FILE]:
    if not path.exists():
        st.error(f"File not found: {path.name}")
        st.stop()

try:
    neutral = prepare_data(
        load_csv(str(ATOMIC_FILE)), is_ion=False
    )
    ions = prepare_data(
        load_csv(str(IONIC_FILE)), is_ion=True
    )
except Exception as exc:
    st.error(f"Could not prepare your data: {exc}")
    st.stop()


mode = st.radio(
    "Choose species type",
    ["Neutral atoms", "Ions"],
    horizontal=True
)

pool = neutral.copy() if mode == "Neutral atoms" else ions.copy()

if mode == "Ions":
    coordination_values = sorted(
        c for c in pool["coordination"].unique() if c
    )

    if coordination_values:
        coordination = st.selectbox(
            "Coordination environment",
            coordination_values
        )
        pool = pool[pool["coordination"] == coordination]
    else:
        st.warning(
            "Your ionic file has no coordination information. "
            "Comparisons will be limited to its available records."
        )

    # Multiple records may exist for the same ion.
    counts = pool["species"].value_counts()
    options = sorted(counts[counts == 1].index.tolist())
else:
    options = sorted(pool["species"].unique().tolist())

if len(options) < 4:
    st.error(
        "Fewer than four unambiguous species are available "
        "for this selection. Check your CSV columns and data."
    )
    st.stop()

st.subheader("Arrange four species")

defaults = ["Li", "Na", "K", "Cs"] if mode == "Neutral atoms" else []
defaults = [s for s in defaults if s in options]

while len(defaults) < 4:
    defaults.append(next(s for s in options if s not in defaults))

selected = []
for i in range(4):
    selected.append(
        st.selectbox(
            f"Species {i + 1}",
            options,
            index=options.index(defaults[i]),
            key=f"{mode}_{i}"
        )
    )

direction = st.radio(
    "Sorting direction",
    ["Smallest to largest", "Largest to smallest"],
    horizontal=True
)

if st.button("Sort species", type="primary"):
    if len(set(selected)) != 4:
        st.error("Please choose four different species.")
        st.stop()

    result = pool[pool["species"].isin(selected)].copy()

    if result["species"].duplicated().any():
        st.error(
            "Some species have multiple reference records. "
            "Select a specific coordination or spin state."
        )
        st.stop()

    ascending = direction == "Smallest to largest"
    result = result.sort_values(
        "radius_pm", ascending=ascending
    ).reset_index(drop=True)

    result.insert(0, "Rank", range(1, len(result) + 1))

    st.subheader("Results")
    st.dataframe(
        result.rename(columns={
            "species": "Species",
            "radius_pm": "Radius (pm)",
            "radius_type": "Radius type",
            "charge": "Charge",
            "coordination": "Coordination",
            "spin": "Spin state"
        }),
        hide_index=True,
        use_container_width=True
    )

    separator = " < " if ascending else " > "
    st.success(
        "Order: " + separator.join(result["species"].tolist())
    )

    st.caption(
        "Rankings use the reference radii in your CSV files, "
        "not ML predictions. Check the source and radius "
        "definition before comparing values."
    )

with st.expander("Inspect loaded data"):
    st.write("Neutral atom records:", len(neutral))
    st.dataframe(neutral.head(20))
    st.write("Ionic records:", len(ions))
    st.dataframe(ions.head(20))
