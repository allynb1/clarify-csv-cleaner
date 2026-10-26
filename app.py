import hashlib
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Clarify", page_icon="◇", layout="wide")

st.title("◇ Clarify")
st.caption("From raw data to clear insights.")

# ---------------------------------------------------------------- session state
defaults = {
    "signature": None,
    "file_name": None,
    "file_size": 0,
    "original_df": None,
    "working_df": None,
    "cleaning_log": [],
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Read CSV bytes, falling back to latin-1 if UTF-8 fails."""
    try:
        return pd.read_csv(BytesIO(raw), low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(BytesIO(raw), encoding="latin-1", low_memory=False)


def apply_change(new_df: pd.DataFrame, message: str) -> None:
    st.session_state.working_df = new_df
    st.session_state.cleaning_log.append(message)
    st.rerun()


tab_upload, tab_view, tab_clean, tab_viz, tab_export = st.tabs(
    ["1 · Upload", "2 · View", "3 · Clean", "4 · Visualize", "5 · Export"]
)

# ---------------------------------------------------------------- 1. UPLOAD
with tab_upload:
    st.subheader("Upload your data")
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    st.caption(
        "Your data stays in this app session. The original upload is kept "
        "separately from your working copy."
    )

    if uploaded is not None:
        raw = uploaded.getvalue()
        sig = hashlib.sha256(uploaded.name.encode("utf-8") + raw).hexdigest()
        if st.session_state.signature != sig:
            try:
                loaded = read_csv_bytes(raw)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not read this CSV: {exc}")
            else:
                st.session_state.signature = sig
                st.session_state.file_name = uploaded.name
                st.session_state.file_size = len(raw)
                st.session_state.original_df = loaded.copy(deep=True)
                st.session_state.working_df = loaded.copy(deep=True)
                st.session_state.cleaning_log = []

    working = st.session_state.working_df

    if working is None:
        st.info("Upload a CSV file to get started.")
        st.markdown("**Workflow:** Upload → View → Clean → Visualize → Export")
    else:
        st.write(
            f"**File:** {st.session_state.file_name} "
            f"({st.session_state.file_size / 1024:,.1f} KB)"
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows", f"{len(working):,}")
        m2.metric("Columns", f"{len(working.columns):,}")
        m3.metric("Missing cells", f"{int(working.isna().sum().sum()):,}")
        m4.metric("Duplicate rows", f"{int(working.duplicated().sum()):,}")

working = st.session_state.working_df
no_data_msg = "Upload a CSV file in the Upload tab first."

# ---------------------------------------------------------------- 2. VIEW
with tab_view:
    if working is None:
        st.info(no_data_msg)
    else:
        st.subheader("Preview records")
        max_rows = min(max(len(working), 1), 500)
        preview_rows = st.slider(
            "Rows to preview", 1, max_rows, min(20, max_rows), key="view_rows"
        )
        st.dataframe(working.head(preview_rows), width="stretch", hide_index=True)
        st.caption(
            f"Showing {min(preview_rows, len(working)):,} of {len(working):,} rows "
            "(preview capped at 500 to keep the page responsive)."
        )

        st.subheader("Column types and missing values")
        schema = pd.DataFrame(
            {
                "Column": working.columns.astype(str),
                "Type": working.dtypes.astype(str).values,
                "Missing values": working.isna().sum().values,
                "Missing %": (working.isna().mean() * 100).round(1).values,
                "Unique values": working.nunique(dropna=True).values,
            }
        )
        st.dataframe(schema, width="stretch", hide_index=True)

        with st.expander("Columns with missing values only"):
            missing = working.isna().sum().rename("Missing values").to_frame()
            missing = missing[missing["Missing values"] > 0].sort_values(
                "Missing values", ascending=False
            )
            if missing.empty:
                st.success("No missing values detected.")
            else:
                st.dataframe(missing, width="stretch")

# ---------------------------------------------------------------- 3. CLEAN
with tab_clean:
    if working is None:
        st.info(no_data_msg)
    else:
        st.subheader("Clean your working copy")
        st.caption(
            "The original upload is never modified. Each action updates the working "
            "copy and is recorded in the cleaning history."
        )
        actions = [
            "Trim whitespace in text columns",
            "Remove duplicate rows",
            "Fill missing values in one column",
            "Drop rows with missing values",
            "Rename a column",
        ]
        action = st.selectbox("Choose a cleaning action", actions, key="clean_action")
        cols = list(working.columns)

        if action == "Trim whitespace in text columns":
            st.write("Removes spaces at the start and end of text values.")
            if st.button("Trim text values", key="apply_trim"):
                df = working.copy()
                text_cols = df.select_dtypes(include=["object", "string"]).columns
                for c in text_cols:
                    df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)
                apply_change(df, f"Trimmed whitespace in {len(text_cols)} text column(s).")

        elif action == "Remove duplicate rows":
            dupes = int(working.duplicated().sum())
            st.write(f"Exact duplicate rows detected: **{dupes:,}**")
            if st.button("Remove duplicate rows", disabled=dupes == 0, key="apply_dupes"):
                df = working.drop_duplicates().reset_index(drop=True)
                apply_change(df, f"Removed {dupes:,} duplicate row(s).")

        elif action == "Fill missing values in one column":
            if not cols:
                st.info("There are no columns to fill.")
            else:
                column = st.selectbox("Column", cols, key="fill_column")
                missing_count = int(working[column].isna().sum())
                st.write(f"Missing values in **{column}**: {missing_count:,}")
                is_numeric = pd.api.types.is_numeric_dtype(working[column])
                choices = (
                    ["Median", "Mean", "Zero", "Custom value"]
                    if is_numeric
                    else ["Most frequent value", "Custom value"]
                )
                method = st.selectbox("Fill method", choices, key="fill_method")
                custom = (
                    st.text_input("Custom value", key="fill_custom")
                    if method == "Custom value"
                    else None
                )
                if st.button("Fill missing values", disabled=missing_count == 0, key="apply_fill"):
                    df = working.copy()
                    fill_value = None
                    error = None
                    if method == "Median":
                        fill_value = df[column].median()
                    elif method == "Mean":
                        fill_value = df[column].mean()
                    elif method == "Zero":
                        fill_value = 0
                    elif method == "Most frequent value":
                        modes = df[column].mode(dropna=True)
                        if modes.empty:
                            error = "No existing value to use. Choose a custom value instead."
                        else:
                            fill_value = modes.iloc[0]
                    else:
                        if custom is None or custom == "":
                            error = "Enter a custom value."
                        elif is_numeric:
                            try:
                                fill_value = pd.to_numeric(custom, errors="raise")
                            except (ValueError, TypeError):
                                error = "Enter a valid number for this numeric column."
                        else:
                            fill_value = custom
                    if error:
                        st.error(error)
                    else:
                        df[column] = df[column].fillna(fill_value)
                        apply_change(
                            df,
                            f"Filled {missing_count:,} missing value(s) in '{column}' using {method}.",
                        )

        elif action == "Drop rows with missing values":
            affected = int(working.isna().any(axis=1).sum())
            st.warning(f"This will remove {affected:,} row(s) with at least one missing value.")
            if st.button("Drop incomplete rows", disabled=affected == 0, key="apply_drop"):
                df = working.dropna().reset_index(drop=True)
                apply_change(df, f"Dropped {affected:,} row(s) with missing values.")

        elif action == "Rename a column":
            if not cols:
                st.info("There are no columns to rename.")
            else:
                column = st.selectbox("Column to rename", cols, key="rename_column")
                new_name = st.text_input("New column name", key="rename_new").strip()
                clash = new_name in cols and new_name != column
                if clash:
                    st.warning("A column with that name already exists.")
                if st.button(
                    "Rename column",
                    disabled=(not new_name or clash or new_name == column),
                    key="apply_rename",
                ):
                    df = working.rename(columns={column: new_name})
                    apply_change(df, f"Renamed column '{column}' to '{new_name}'.")

        st.divider()
        st.markdown("**Cleaning history**")
        if st.session_state.cleaning_log:
            for i, item in enumerate(st.session_state.cleaning_log, 1):
                st.write(f"{i}. {item}")
            if st.button("Undo all cleaning (restore original)", key="undo_all"):
                st.session_state.working_df = st.session_state.original_df.copy(deep=True)
                st.session_state.cleaning_log = []
                st.rerun()
        else:
            st.caption("No cleaning actions applied yet.")

# ---------------------------------------------------------------- 4. VISUALIZE
with tab_viz:
    if working is None:
        st.info(no_data_msg)
    elif working.empty or len(working.columns) == 0:
        st.warning("There is no data to visualize.")
    else:
        st.subheader("Explore your data")
        numeric_cols = list(working.select_dtypes(include="number").columns)
        other_cols = [c for c in working.columns if c not in numeric_cols]
        chart_type = st.selectbox(
            "Chart type",
            ["Bar chart", "Histogram", "Scatter plot", "Line chart", "Box plot"],
            key="viz_type",
        )

        if chart_type == "Bar chart":
            category = st.selectbox(
                "Category column", other_cols or list(working.columns), key="viz_bar_cat"
            )
            counts = (
                working[category]
                .fillna("(Missing)")
                .astype(str)
                .value_counts()
                .head(30)
                .rename_axis(category)
                .reset_index(name="Count")
            )
            fig = px.bar(counts, x=category, y="Count", title=f"Top values in {category}")
            st.plotly_chart(fig, width="stretch")

        elif chart_type == "Histogram":
            if not numeric_cols:
                st.info("A histogram needs a numeric column.")
            else:
                column = st.selectbox("Numeric column", numeric_cols, key="viz_hist_col")
                fig = px.histogram(
                    working, x=column, title=f"Distribution of {column}", marginal="box"
                )
                st.plotly_chart(fig, width="stretch")
                st.dataframe(working[column].describe().to_frame("Summary"), width="stretch")

        elif chart_type == "Scatter plot":
            if len(numeric_cols) < 2:
                st.info("A scatter plot needs at least two numeric columns.")
            else:
                xcol = st.selectbox("X-axis", numeric_cols, key="viz_sc_x")
                ycol = st.selectbox(
                    "Y-axis", [c for c in numeric_cols if c != xcol], key="viz_sc_y"
                )
                fig = px.scatter(working, x=xcol, y=ycol, title=f"{ycol} vs. {xcol}")
                st.plotly_chart(fig, width="stretch")

        elif chart_type == "Line chart":
            if not numeric_cols:
                st.info("A line chart needs a numeric column.")
            else:
                xcol = st.selectbox("X-axis", list(working.columns), key="viz_ln_x")
                ycol = st.selectbox("Numeric Y-axis", numeric_cols, key="viz_ln_y")
                chart_df = working[[xcol, ycol]].dropna()
                if xcol == ycol:
                    st.info("Pick different columns for the X and Y axes.")
                else:
                    if len(chart_df) > 5000:
                        st.caption("Showing the first 5,000 rows.")
                        chart_df = chart_df.head(5000)
                    chart_df = chart_df.sort_values(xcol)
                    fig = px.line(chart_df, x=xcol, y=ycol, title=f"{ycol} by {xcol}")
                    st.plotly_chart(fig, width="stretch")

        else:  # Box plot
            if not numeric_cols:
                st.info("A box plot needs a numeric column.")
            else:
                column = st.selectbox("Numeric column", numeric_cols, key="viz_box_col")
                group = st.selectbox(
                    "Group by (optional)", ["(none)"] + other_cols, key="viz_box_group"
                )
                fig = px.box(
                    working,
                    y=column,
                    x=None if group == "(none)" else group,
                    points="outliers",
                    title=f"Spread of {column}",
                )
                st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- 5. EXPORT
with tab_export:
    if working is None:
        st.info(no_data_msg)
    else:
        st.subheader("Export your prepared data")
        st.write(f"The cleaned dataset has **{len(working):,}** rows and **{len(working.columns):,}** columns.")
        st.download_button(
            "Download cleaned CSV",
            data=working.to_csv(index=False).encode("utf-8-sig"),
            file_name="clarify_cleaned.csv",
            mime="text/csv",
        )
        if st.session_state.cleaning_log:
            log_df = pd.DataFrame(
                {
                    "Step": range(1, len(st.session_state.cleaning_log) + 1),
                    "Cleaning action": st.session_state.cleaning_log,
                }
            )
            st.download_button(
                "Download cleaning history",
                data=log_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="clarify_cleaning_history.csv",
                mime="text/csv",
            )
        else:
            st.caption("No cleaning history yet. Apply a cleaning action to export a log.")