import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# ---------------------------------------------------------
# ⚙️ CONFIGURATION (Google Sheet Link)
# ---------------------------------------------------------
# Step: Yahan double quotes "" ke beech mein apna Google Sheet ka "Publish to CSV" link paste karein
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ-RbUqcpirKabS-li6tY-1kgYYNUjRee3K4qxVcyqwc5b0dOwr56eWydXMdM93XQ/pub?gid=2081631817&single=true&output=csv"

# ---------------------------------------------------------
# SETTINGS: EXACT OUTPUT HEADERS
# ---------------------------------------------------------
OUTPUT_HEADERS = [
    "First Name", "Last Name", "Company", "Title", "Phone1", "Phone2", 
    "Other Phones", "Email1", "Other Emails", "Address1", "City", "State", 
    "Country", "Pincode", "Address2", "Assignee", "Contact Type", "Location", 
    "Feedbacks", "Property Type", "Property Available For", "Property Sell Address", 
    "Property Meet Address", "Lead Source", "Ops-Sale-Lead-Given-By", 
    "Meeting-Date", "Meeting-Time", "Call-Time", "Area", "Price", 
    "BHK", "Sq.Ft.-Sq.Yd.", "Relationship-Manager", "Total No. of property", 
    "Property Area", "Priority-lead"
]

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
@st.cache_data(ttl=600) # Data har 10 minute mein refresh hoga
def load_bde_data(url):
    try:
        # Check if URL is placeholder
        if "YAHAN_APNA" in url:
            return None, "Error: Code mein Google Sheet ka Link paste karna baaki hai!"
        
        # Read CSV from Google Sheet
        df_sheet = pd.read_csv(url)
        
        # Convert to Dictionary {Name: [Loc1, Loc2]}
        bde_dict = {}
        # Assuming Column A is 'BDE Name' and Column B is 'Locations'
        # We use index 0 and 1 to be safe against header name changes
        for index, row in df_sheet.iterrows():
            name = str(row.iloc[0]).strip()
            locs_str = str(row.iloc[1])
            locs_list = [x.strip() for x in locs_str.split(',') if x.strip()]
            bde_dict[name] = locs_list
            
        return bde_dict, None
    except Exception as e:
        return None, f"Google Sheet Error: {e}. Kya link sahi hai? (Publish to Web > CSV)"

# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Cleardeals Ops Tool", layout="wide")
st.title("🚀 Cleardeals Operations Automation Tool")

# ---------------------------------------------------------
# SIDEBAR: BDE STATUS
# ---------------------------------------------------------
st.sidebar.header("📡 Live Data Connection")
bde_data, error_msg = load_bde_data(SHEET_URL)

if error_msg:
    st.sidebar.error(error_msg)
    st.error("⚠️ Google Sheet connect nahi ho payi. Code check karein.")
elif bde_data:
    st.sidebar.success("✅ Google Sheet Connected!")
    st.sidebar.markdown("### Active Team:")
    for name, locs in bde_data.items():
        st.sidebar.text(f"👤 {name} ({len(locs)} locs)")
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------
# MAIN TOOL (Daily Work)
# ---------------------------------------------------------
st.header("Daily File Processing")

uploaded_files = st.file_uploader("Sabhi Master Excel Files yahan dalein", type=["xlsx", "csv"], accept_multiple_files=True)

if bde_data:
    st.subheader("Select BDEs for Today's Output")
    all_bdes = list(bde_data.keys())
    selected_bdes = st.multiselect("Kin BDEs ke liye file banani hai?", all_bdes, default=all_bdes)

    if uploaded_files and st.button("🚀 Process Files & Generate CSVs"):
        
        master_df_list = []
        for file in uploaded_files:
            try:
                if file.name.endswith('.csv'):
                    df_temp = pd.read_csv(file)
                else:
                    df_temp = pd.read_excel(file)
                master_df_list.append(df_temp)
            except Exception as e:
                st.error(f"Error reading file {file.name}: {e}")
        
        if master_df_list:
            full_df = pd.concat(master_df_list, ignore_index=True)
            
            try:
                # Filter: Only rows where Column B (Index 1) is 'Res_resale'
                filtered_df = full_df[full_df.iloc[:, 1].astype(str).str.strip().str.lower() == 'res_resale']
                
                output_files_dict = {} 
                today_str = datetime.now().strftime("%d%b%Y") 
                
                for bde in selected_bdes:
                    target_locations = [loc.lower() for loc in bde_data[bde]]
                    
                    # Location Check: Column F is Index 5
                    location_col_idx = 5 
                    
                    mask = filtered_df.iloc[:, location_col_idx].astype(str).str.strip().str.lower().isin(target_locations)
                    bde_rows = filtered_df[mask].copy()
                    
                    if not bde_rows.empty:
                        # Create DataFrame with EXACT HEADERS
                        final_df = pd.DataFrame(index=bde_rows.index, columns=OUTPUT_HEADERS)
                        
                        # --- MAPPING LOGIC ---
                        # Master Columns: D=3, E=4, F=5, G=6, H=7, I=8, P=15
                        
                        # 1. Master D -> First Name
                        final_df['First Name'] = bde_rows.iloc[:, 3]
                        
                        # NEW REQUIREMENT: Col C (Company) -> "NEW"
                        final_df['Company'] = "NEW"
                        
                        # 2. Master E -> Phone1
                        final_df['Phone1'] = bde_rows.iloc[:, 4]
                        
                        # 3. Master F -> Location (With P- prefix)
                        final_df['Location'] = "P-" + bde_rows.iloc[:, 5].astype(str)
                        
                        # 4. Master G -> Property Sell Address
                        final_df['Property Sell Address'] = bde_rows.iloc[:, 6]
                        
                        # 5. Master H -> BHK
                        final_df['BHK'] = bde_rows.iloc[:, 7]
                        
                        # 6. Master I -> Sq.Ft.-Sq.Yd.
                        final_df['Sq.Ft.-Sq.Yd.'] = bde_rows.iloc[:, 8]

                        # 7. Master P -> Price (Column AD equivalent)
                        final_df['Price'] = bde_rows.iloc[:, 15]
                        
                        # 8. Master F -> Area (Without P-)
                        final_df['Area'] = bde_rows.iloc[:, 5]
                        
                        # 9. Static Values
                        final_df['Property Type'] = "Residential"
                        final_df['Property Available For'] = "Sell"
                        
                        # Add to dictionary (Using .csv extension)
                        filename = f"{bde}.{today_str}.csv"
                        output_files_dict[filename] = final_df
                
                if output_files_dict:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for fname, data in output_files_dict.items():
                            with zf.open(fname, "w") as buffer:
                                # Saving as CSV (UTF-8 format)
                                # encode='utf-8-sig' ensures Excel opens it correctly with special chars
                                csv_data = data.to_csv(index=False, encoding='utf-8-sig')
                                buffer.write(csv_data.encode('utf-8-sig'))
                    
                    st.success(f"🎉 Success! {len(output_files_dict)} CSV Files Created.")
                    st.download_button(
                        label="📥 Download All Files (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"Processed_CSVs_{today_str}.zip",
                        mime="application/zip"
                    )
                else:
                    st.warning("Koi matching data nahi mila. Locations aur Master file check karein.")
                    
            except Exception as e:
                st.error(f"Processing Error: {e}. Check karein ki Master File ka format sahi hai.")
else:
    st.info("👈 Please Sidebar check karein aur Google Sheet connect hone ka wait karein.")