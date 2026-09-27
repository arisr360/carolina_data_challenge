"""
Run this ONCE to build the merged dataset the Streamlit app reads.
Re-run it any time your source CSV or the shapefile changes.

Usage: python prep_data.py
"""

import pandas as pd
import geopandas as gpd

# ---- 1. Load your cleaned school-level CSV ----
df = pd.read_csv('data/nc_schools.csv')  # <- adjust path if needed

top5 = ['access_to_broadband_internet', 'lead_exposure_risk',
        'some_other_race_alone', 'low_birth_weight', 'poverty']

# ---- 2. Aggregate to district level ----
district_df = (
    df.groupby('school_district', as_index=False)[top5 + ['less_than_hs']]
      .mean()
)

# ---- 3. Z-score the top 5, so the app can show "std devs from state average" ----
z = district_df.copy()
for col in top5:
    z[col + '_z'] = (district_df[col] - district_df[col].mean()) / district_df[col].std()

# ---- 4. Load NC district boundaries ----
districts = gpd.read_file(
    'data/EDGE_SCHOOLDISTRICT_TL25_SY2425 (1)/EDGE_SCHOOLDISTRICT_TL25_SY2425.shp'
)
nc_districts = districts[districts['STATEFP'] == '37'].copy()

# ---- 5. Fix name mismatches between shapefile and your CSV ----
rename_map = {
    'Carteret County Schools': 'Carteret County Public Schools',
    'Chapel Hill-Carrboro Schools': 'Chapel Hill-Carrboro City Schools',
    'Cherokee Central Schools': 'Cherokee Central High School',
    'Edgecombe County Schools': 'Edgecombe County Public Schools',
    'Forsyth County Schools': 'Winston Salem / Forsyth County Schools',
    'Jackson County Schools': 'Jackson County Public Schools',
    'Johnston County Schools': 'Johnston County Public Schools',
    'Lenoir County Schools': 'Lenoir County Public Schools',
    'McDowell County Schools': 'Mcdowell County Schools',
    'Mooresville City Schools': 'Mooresville Graded School District',
    'Nash-Rocky Mount Schools': 'Nash County Public Schools',
    'Newton-Conover City Schools': 'Newton Conover City Schools',
    'Pasquotank County Schools': 'Elizabeth City-Pasquotank Public Schools',
    'Randolph County Schools': 'Randolph County School System',
    'Robeson County Schools': 'Public Schools Of Robeson County',
}
nc_districts['NAME_clean'] = nc_districts['NAME'].replace(rename_map)

# ---- 6. Merge boundaries with your data ----
merged = nc_districts.merge(z, left_on='NAME_clean', right_on='school_district')
print(f"Matched {len(merged)} of {len(nc_districts)} shapefile districts")

# Plotly needs lat/lon (EPSG:4326)
merged = merged.to_crs(epsg=4326)

# ---- 7. Save clean file for the app to load ----
merged.to_file('data/merged_districts.geojson', driver='GeoJSON')
print("Saved data/merged_districts.geojson")