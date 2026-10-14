import streamlit as st

st.set_page_config(
    page_title="Atomic Size Predictor",
    page_icon="⚛️"
)

st.title("⚛️ Atomic Size Predictor")

st.write(
    "Welcome! This application sorts chemical elements "
    "by their reference atomic radii."
)

elements = ["Li", "Na", "K", "Cs"]

st.subheader("Sort four elements")

selected = st.multiselect(
    "Choose four elements",
    options=elements,
    default=elements,
    max_selections=4
)

direction = st.selectbox(
    "Sorting direction",
    ["Smallest to largest", "Largest to smallest"]
)

# Reference-data ordering for this initial demonstration.
# Replace with values loaded from your CSV for the full app.
reference_order = {"Li": 1, "Na": 2, "K": 3, "Cs": 4}

if st.button("Sort elements"):
    if len(selected) != 4:
        st.error("Please select exactly four elements.")
    else:
        result = sorted(
            selected,
            key=lambda symbol: reference_order[symbol],
            reverse=(direction == "Largest to smallest")
        )
        st.success("Order: " + " < ".join(result)
                   if direction == "Smallest to largest"
                   else "Order: " + " > ".join(result))
