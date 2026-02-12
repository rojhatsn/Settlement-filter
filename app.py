import streamlit as st
import pandas as pd
import ast
import base64

# Set page config
st.set_page_config(page_title="Nisanyan Settlement Filter", layout="wide", page_icon="logo.png")

# Display Logo
col1, col2 = st.columns([1, 8])
with col1:
    st.image("logo.png", width=80)
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
    map_data = filtered_df.dropna(subset=['latitude', 'longitude'])
    if not map_data.empty:
        st.map(map_data, size=20, color='#FF0000')
    else:
        st.warning("No coordinates found to plot.")

with tab2:
    st.dataframe(filtered_df)

# --- Export ---
st.sidebar.markdown("---")
st.sidebar.header("Export")

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_df(filtered_df)

st.sidebar.download_button(
    label="Download Filtered CSV",
    data=csv,
    file_name='filtered_settlements_umap.csv',
    mime='text/csv',
)
