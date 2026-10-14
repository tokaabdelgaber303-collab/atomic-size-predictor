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
    "Compare and arrange four elements or ions "
    "using reference atomic and ionic radii."
)

BASE = Path(__file__).parent
ATOMIC_FILE = BASE / "neutral_atomic_radii.csv"
IONIC_FILE = BASE / "ionic_radii.csv"


@st.cache_data
def load_csv(filename):
    return pd.read_csv(filename)


def ion_label(symbol, charge):
    charge = int(charge)
    if charge == 0:
        return symbol
    if charge == 1:
        return f"{symbol}+"
    if charge == -1:
        return f"{symbol}-"
    return f"{symbol}{abs(charge)}{'+' if charge > 0 else '-'}"


def load_neutral():
    df = load_csv(str(ATOMIC_FILE))
    df.columns = df.columns.str.strip()

    # Adapt to the common neutral-radius dataset columns
    symbol_col = "symbol" if "symbol" in df.columns else "Symbol"
    radius_col = next(
        (c for c in ["radius_pm", "atomic_radius",
                     "atomic_radius_pm", "covalent_radius"]
         if c in df.columns),
        None
    )

    if radius_col is None or symbol_col not in df.columns:
        raise ValueError(
            f"Neutral CSV columns are {df.columns.tolist()}. "
            "Please check its symbol and radius column names."
        )

    out = pd.DataFrame({
        "species": df[symbol_col].astype(str).str.strip(),
        "radius_pm": pd.to_numeric(
            df[radius_col], errors="coerce"
        ),
        "charge": 0,
        "radius_type": "neutral",
        "coordination": "",
        "spin": ""
    })

    return out.dropna(subset=["radius_pm"])


def load_ions():
    df = load_csv(str(IONIC_FILE))
    df.columns = df.columns.str.strip()

    required = [
        "symbol", "charge", "coordination", "ionic_radius"
    ]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            "Ionic CSV is missing: " + ", ".join(missing)
        )

    df["charge"] = pd.to_numeric(df["charge"], errors="coerce")
    df["ionic_radius"] = pd.to_numeric(
        df["ionic_radius"], errors="coerce"
    )

    df = df.dropna(
        subset=["symbol", "charge", "ionic_radius"]
    ).copy()

    df = df[df["charge"] != 0]

    df["species"] = df.apply(
        lambda r: ion_label(r["symbol"], r["charge"]),
        axis=1
    )

    out = pd.DataFrame({
        "species": df["species"],
        "radius_pm": df["ionic_radius"],
        "charge": df["charge"],
        "radius_type": "ionic",
        "coordination": df["coordination"].fillna("").astype(str),
        "spin": (
            df["spin"].fillna("").astype(str)
            if "spin" in df.columns else ""
        ),
        "symbol": df["symbol"]
    })

    # Prefer reliable records when they exist for the same
    # species/coordination/spin combination.
    if "most_reliable" in df.columns:
        out["most_reliable"] = df["most_reliable"].values
    else:
        out["most_reliable"] = 0

    return out


if not ATOMIC_FILE.exists() or not IONIC_FILE.exists():
    st.error(
        "Upload neutral_atomic_radii.csv and ionic_radii.csv "
        "to the same GitHub repository as app.py."
    )
    st.stop()

try:
    neutral = load_neutral()
    ions = load_ions()
except Exception as exc:
    st.error(f"Dataset loading error: {exc}")
    st.stop()


mode = st.radio(
    "Choose species type",
    ["Neutral atoms", "Ions"],
    horizontal=True
)

pool = neutral.copy() if mode == "Neutral atoms" else ions.copy()

if mode == "Ions":
    # Select coordination first, preserving the source records.
    coord_values = sorted(
        c for c in pool["coordination"].unique()
        if c and c.lower() != "nan"
    )

    if not coord_values:
        st.error("No coordination values are available.")
        st.stop()

    coordination = st.selectbox(
        "Coordination environment",
        coord_values,
        index=coord_values.index("VI")
        if "VI" in coord_values else 0
    )

    pool = pool[
        pool["coordination"] == coordination
    ].copy()

    # Prefer reliable records for each ion, where available.
    # Keep distinct spin states separate if they are meaningful.
    selected_rows = []

    for species, group in pool.groupby("species"):
        reliable = pd.to_numeric(
            group["most_reliable"], errors="coerce"
        ).fillna(0)

        if (reliable == 1).any():
            group = group[reliable == 1]

        # If duplicate records remain, use one only when
        # the ionic radius values agree.
        if group["radius_pm"].nunique() == 1:
            selected_rows.append(group.iloc[0])
        else:
            # Do not arbitrarily choose between conflicting
            # radii for the same ion.
            continue

    if selected_rows:
        pool = pd.DataFrame(selected_rows).reset_index(drop=True)
    else:
        pool = pool.iloc[0:0].copy()

    options = sorted(pool["species"].unique().tolist())

else:
    options = sorted(pool["species"].unique().tolist())
if len(options) < 4:
    st.warning(
        f"Only {len(options)} unambiguous species are available "
        "with the current settings. Try another coordination "
        "environment or inspect the CSV data."
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
        st.error("Please select four different species.")
        st.stop()

    result = pool[pool["species"].isin(selected)].copy()

    if result["species"].duplicated().any():
        st.error(
            "Some species still have multiple radius records. "
            "Select a more specific coordination or spin state."
        )
        st.stop()

    ascending = direction == "Smallest to largest"
    result = result.sort_values(
        "radius_pm", ascending=ascending
    ).reset_index(drop=True)

    result.insert(0, "Rank", range(1, len(result) + 1))

    st.subheader("Ranking results")
    st.dataframe(
        result[
            ["Rank", "species", "radius_pm", "charge",
             "coordination", "spin"]
        ].rename(columns={
            "species": "Species",
            "radius_pm": "Ionic/atomic radius (pm)",
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
        "Ranks use reference values from the selected dataset. "
        "Ionic radii depend on coordination and can also depend "
        "on spin state."
    )

with st.expander("Inspect available records"):
    st.write("Neutral radius records:", len(neutral))
    st.dataframe(neutral.head(20))
    st.write("Ionic radius records:", len(ions))
    st.dataframe(ions.head(20))
