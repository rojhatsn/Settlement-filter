import streamlit as st
import pandas as pd
import ast
import base64

# Set page config
st.set_page_config(page_title="Nisanyan Settlement Filter", layout="wide", page_icon="logo.png")

# Display Logo
col1, col2 = st.columns([1, 8])
with col1:
    st.image("logo.png", width=50)
with col2:
    st.title("Nisanyan Settlement Filter by KDP")

st.logo("logo.png")
st.markdown("Filter Turkey settlements by Ethinicity, Tribe, and Location for uMap export.")

# --- Data Loading ---
@st.cache_data
def load_data():
    try:
        # data is utf-16 based on previous steps
        df = pd.read_csv("Turkey_Settlements_Nisanyanmap.csv", encoding="utf-16")
        
        # Parse Coordinates: "[lat, lon]" -> lat, lon
        def parse_coords(coord_str):
            try:
                if isinstance(coord_str, str):
                    parsed = ast.literal_eval(coord_str)
                    if isinstance(parsed, list) and len(parsed) == 2:
                        return parsed[0], parsed[1]
            except:
                pass
            return None, None

        # Apply parsing
        coords = df['Coordinates'].apply(parse_coords)
        df['latitude'] = [c[1] for c in coords]
        df['longitude'] = [c[0] for c in coords]
        
        # Clean specific columns for display
        df['Tribes'] = df['Tribes'].fillna('')
        df['Ethnicity'] = df['Ethnicity'].fillna('')
        df['Description'] = df['Description'].fillna('')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# 1. Province
all_provinces = sorted(df['Province'].unique().tolist())
selected_provinces = st.sidebar.multiselect("Select Province(s)", all_provinces)

# 2. District (Dependent on Province)
if selected_provinces:
    filtered_for_districts = df[df['Province'].isin(selected_provinces)]
    available_districts = sorted(filtered_for_districts['District'].unique().tolist())
else:
    available_districts = sorted(df['District'].unique().tolist())
    
selected_districts = st.sidebar.multiselect("Select District(s)", available_districts)

# 3. Tribe Filter
# Extract unique tribes
all_tribes = set()
for x in df['Tribes'].dropna():
    if x:
        for t in str(x).split(','):
            t_clean = t.strip()
            if t_clean:
                all_tribes.add(t_clean)
sorted_tribes = sorted(list(all_tribes))

selected_tribes = st.sidebar.multiselect("Select Tribe(s)", sorted_tribes)

# 4. Ethnicity Filter
# Extract unique ethnicities
all_ethnicities = set()
for x in df['Ethnicity'].dropna():
    if x:
        for e in str(x).split(','):
            e_clean = e.strip()
            if e_clean:
                all_ethnicities.add(e_clean)
sorted_ethnicities = sorted(list(all_ethnicities))

selected_ethnicities = st.sidebar.multiselect("Select Ethnicity", sorted_ethnicities)

# 5. Other Filters
name_search = st.sidebar.text_input("Search Name / Old Name")
desc_search = st.sidebar.text_input("Search Description")

# --- Apply Filters ---
filtered_df = df.copy()

if selected_provinces:
    filtered_df = filtered_df[filtered_df['Province'].isin(selected_provinces)]

if selected_districts:
    filtered_df = filtered_df[filtered_df['District'].isin(selected_districts)]

if name_search:
    # Search in Name OR Old_Name
    m1 = filtered_df['Name'].str.contains(name_search, case=False, na=False)
    m2 = filtered_df['Old_Name'].str.contains(name_search, case=False, na=False)
    filtered_df = filtered_df[m1 | m2]

if selected_tribes:
    # Construct regex pattern to match any of the selected tribes
    # We use word boundaries or logic to ensure we don't match substrings incorrectly if possible,
    # but simple contains is usually enough for this user.
    # Using regex OR (|) to match any selected tribe.
    import re
    tribe_pattern = '|'.join([re.escape(t) for t in selected_tribes])
    filtered_df = filtered_df[filtered_df['Tribes'].str.contains(tribe_pattern, case=False, na=False)]

if selected_ethnicities:
    import re
    eth_pattern = '|'.join([re.escape(e) for e in selected_ethnicities])
    filtered_df = filtered_df[filtered_df['Ethnicity'].str.contains(eth_pattern, case=False, na=False)]

if desc_search:
    filtered_df = filtered_df[filtered_df['Description'].str.contains(desc_search, case=False, na=False)]

# --- Main Interface ---

# Metrics
st.markdown(f"**Found {len(filtered_df)} settlements**")

# Tabs for Map and Data
tab1, tab2 = st.tabs(["📍 Map View", "📄 Data Table"])

with tab1:
    # Map requires lat/lon columns and no NaNs
    map_data = filtered_df.dropna(subset=['latitude', 'longitude']).copy()
    
    # Dynamic Coloring Logic
    # Default color (Red)
    map_data['color'] = '#FF0000'
    
    # If multiple tribes selected, assign distinct colors
    if selected_tribes and len(selected_tribes) > 0:
        # distinct colors palette (hex)
        palette = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', '#FF00FF', 
            '#FFA500', '#800080', '#008000', '#000080', '#800000', '#008080'
        ]
        
        tribe_color_map = {}
        for idx, t in enumerate(selected_tribes):
            tribe_color_map[t] = palette[idx % len(palette)]
            
        # Display Legend
        st.markdown("**Color Legend:**")
        cols = st.columns(len(selected_tribes))
        for idx, t in enumerate(selected_tribes):
            color = tribe_color_map[t]
            cols[idx % len(cols)].markdown(f":large_blue_circle: <span style='color:{color}'>**{t}**</span>", unsafe_allow_html=True)
            
        # Apply colors to rows
        def get_color(row_tribes):
            if not isinstance(row_tribes, str):
                return '#FF0000'
            for t in selected_tribes:
                if t in row_tribes:
                    return tribe_color_map[t]
            return '#FF0000'
            
        map_data['color'] = map_data['Tribes'].apply(get_color)
        
    elif selected_ethnicities and len(selected_ethnicities) > 0:
        # distinct colors palette (hex)
        palette = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', '#FF00FF', 
            '#FFA500', '#800080', '#008000', '#000080', '#800000', '#008080'
        ]
        
        eth_color_map = {}
        for idx, e in enumerate(selected_ethnicities):
            eth_color_map[e] = palette[idx % len(palette)]
            
        # Display Legend
        st.markdown("**Color Legend (Ethnicity):**")
        cols = st.columns(len(selected_ethnicities))
        for idx, e in enumerate(selected_ethnicities):
            color = eth_color_map[e]
            cols[idx % len(cols)].markdown(f":large_blue_circle: <span style='color:{color}'>**{e}**</span>", unsafe_allow_html=True)
            
        # Apply colors to rows
        def get_eth_color(row_eth):
            if not isinstance(row_eth, str):
                return '#FF0000'
            for e in selected_ethnicities:
                if e in row_eth:
                    return eth_color_map[e]
            return '#FF0000'
            
        map_data['color'] = map_data['Ethnicity'].apply(get_eth_color)

    if not map_data.empty:
        st.map(map_data, size=20, color='color')
    else:
        st.warning("No coordinates found to plot.")

with tab2:
    st.dataframe(filtered_df)

import zipfile
import io

# --- Export ---
st.sidebar.markdown("---")
st.sidebar.header("Export")

export_format = st.sidebar.radio("Export Format", ["Single CSV", "Separate Sheets (ZIP)"])

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def create_zip(filtered_df, split_col):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # Get unique values in the split column
        # Handle comma-separated values by iterating and filtering
        # Actually, for the map layer logic, it's best if we iterate the *selected* filters
        # because a single row might belong to multiple groups.
        # But uMap points can only belong to one layer usually. 
        # So we will iterate the selected items and create a file for each.
        # If a point is in multiple, it will appear in multiple layers (which is fine/good).
        
        groups = []
        if split_col == "Tribes" and selected_tribes:
            groups = selected_tribes
        elif split_col == "Ethnicity" and selected_ethnicities:
            groups = selected_ethnicities
        
        if not groups:
            # Fallback to categorical unique values if no filter selected but split requested
            # This is complex for comma-sep. Let's stick to selected filters for now or simple unique.
            # If nothing selected, maybe just one big file.
             zip_file.writestr("ALL_Settlements.csv", filtered_df.to_csv(index=False).encode('utf-8'))
        else:
            for group in groups:
                # Filter rows containing this group
                # Use word boundary or simple contains
                subset = filtered_df[filtered_df[split_col].str.contains(group, case=False, na=False)]
                if not subset.empty:
                    # Clean filename
                    safe_name = "".join([c for c in group if c.isalnum() or c in (' ','-','_')]).strip()
                    zip_file.writestr(f"{split_col}_{safe_name}.csv", subset.to_csv(index=False).encode('utf-8'))
                    
    return zip_buffer.getvalue()

if export_format == "Single CSV":
    csv = convert_df(filtered_df)
    st.sidebar.download_button(
        label="Download CSV",
        data=csv,
        file_name='nisanyan_map_export.csv',
        mime='text/csv',
    )
else:
    # Determine split criteria
    split_by = "Tribes" if selected_tribes else ("Ethnicity" if selected_ethnicities else None)
    
    if split_by:
        st.sidebar.info(f"Splitting by: {split_by}")
        zip_data = create_zip(filtered_df, split_by)
        st.sidebar.download_button(
            label="Download ZIP (Layers)",
            data=zip_data,
            file_name='nisanyan_layers.zip',
            mime='application/zip',
        )
    else:
        st.sidebar.warning("Select Tribes or Ethnicities to enable splitting.")
