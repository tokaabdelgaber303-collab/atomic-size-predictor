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
    "Compare atomic sizes and arrange four atoms or ions "
    "using reference radius data."
)

DATA_FILE = Path(__file__).parent / "atomic_and_ionic_radii.csv"

ELEMENTS = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
]

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)

    required = [
        "species", "symbol", "radius_pm",
        "radius_type", "charge"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "CSV is missing columns: " + ", ".join(missing)
        )

    df["species"] = df["species"].astype(str).str.strip()
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["radius_pm"] = pd.to_numeric(
        df["radius_pm"], errors="coerce"
    )
    df["charge"] = pd.to_numeric(
        df["charge"], errors="coerce"
    )
    df["radius_type"] = (
        df["radius_type"].astype(str).str.lower().str.strip()
    )

    if "coordination" not in df:
        df["coordination"] = ""
    if "spin" not in df:
        df["spin"] = ""

    df["coordination"] = (
        df["coordination"].fillna("").astype(str).str.strip()
    )
    df["spin"] = (
        df["spin"].fillna("").astype(str).str.strip()
    )

    return df.dropna(
        subset=["radius_pm", "charge"]
    ).copy()

if not DATA_FILE.exists():
    st.error(
        "Dataset not found. Upload atomic_and_ionic_radii.csv "
        "to the same GitHub repository as app.py."
    )
    st.stop()

try:
    data = load_data()
except Exception as e:
    st.error(f"Could not read dataset: {e}")
    st.stop()

mode = st.radio(
    "Choose comparison type",
    ["Neutral atoms", "Ions"],
    horizontal=True
)

pool = data[
    data["radius_type"] == (
        "neutral" if mode == "Neutral atoms" else "ionic"
    )
].copy()

if mode == "Neutral atoms":
    # Show only elements that have reference data.
    available_symbols = set(pool["symbol"])
    st.caption(
        f"Reference data available for "
        f"{len(available_symbols)} element symbols."
    )
    options = sorted(
        pool["species"].unique(),
        key=lambda s: (
            ELEMENTS.index(s)
            if s in ELEMENTS else 999,
            s
        )
    )
else:
    coordination_values = sorted(
        c for c in pool["coordination"].unique() if c
    )

    if not coordination_values:
        st.warning(
            "No coordination labels are present in your ionic "
            "dataset. Check the source dataset before comparing ions."
        )
        st.stop()

    coordination = st.selectbox(
        "Choose ionic coordination environment",
        coordination_values
    )

    pool = pool[pool["coordination"] == coordination].copy()

    # Exclude ambiguous species with multiple records.
    counts = pool["species"].value_counts()
    options = sorted(counts[counts == 1].index.tolist())

if len(options) < 4:
    st.error(
        "Fewer than four unambiguous species have radius data "
        "for this selection."
    )
    st.stop()

st.subheader("Arrange four species")

defaults = (
    ["Li", "Na", "K", "Cs"]
    if mode == "Neutral atoms"
    else options[:4]
)
defaults = [x for x in defaults if x in options]
while len(defaults) < 4:
    candidate = next(x for x in options if x not in defaults)
    defaults.append(candidate)

selected = []
for i in range(4):
    selected.append(
        st.selectbox(
            f"Species {i + 1}",
            options,
            index=options.index(defaults[i]),
            key=f"species_{mode}_{i}"
        )
    )

direction = st.selectbox(
    "Sort by",
    ["Smallest to largest", "Largest to smallest"]
)

if st.button("Arrange species", type="primary"):
    if len(set(selected)) != 4:
        st.error("Select four different species.")
        st.stop()

    result = pool[pool["species"].isin(selected)].copy()

    if result["species"].duplicated().any():
        st.error(
            "Some species have ambiguous reference records. "
            "Check coordination and spin."
        )
        st.stop()

    ascending = direction == "Smallest to largest"
    result = result.sort_values(
        "radius_pm", ascending=ascending
    ).reset_index(drop=True)

    result.insert(0, "Rank", range(1, len(result) + 1))

    columns = [
        "Rank", "species", "radius_pm",
        "radius_type", "charge", "coordination", "spin"
    ]
    columns = [c for c in columns if c in result.columns]

    st.subheader("Results")
    st.dataframe(
        result[columns].rename(
            columns={
                "species": "Species",
                "radius_pm": "Radius (pm)",
                "radius_type": "Radius type",
                "charge": "Charge",
                "coordination": "Coordination",
                "spin": "Spin"
            }
        ),
        hide_index=True,
        use_container_width=True
    )

    separator = " < " if ascending else " > "
    st.success(
        "Order: " + separator.join(result["species"].tolist())
    )

    if mode == "Neutral atoms":
        st.info(
            "Atomic radius generally increases down a group "
            "and decreases across a period. The precise trend "
            "depends on the radius definition used in the dataset."
        )
    else:
        st.info(
            "Ionic radii depend on ionic charge, coordination, "
            "and sometimes spin state. Interpret rankings only "
            "when the radius values are comparable."
        )

st.divider()
with st.expander("View available reference data"):
    st.dataframe(pool, use_container_width=True)
