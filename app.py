import streamlit as st
import pandas as pd
import io
import zipfile
import json
import os
from datetime import datetime

# ---------------------------------------------------------
# CONFIGURATION & DATA SAVING (Mini Database)
# ---------------------------------------------------------
CONFIG_FILE = "bde_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

# Load saved data
bde_data = load_config()

# ---------------------------------------------------------
# SETTINGS: EXACT OUTPUT HEADERS
# ---------------------------------------------------------
# Ye wahi headers hain jo aapne sample output file mein diye hain
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
# PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Cleardeals Ops Tool", layout="wide")
st.title("🚀 Cleardeals Operations Automation Tool")

# Create Tabs
tab1, tab2 = st.tabs(["📂 Main Tool (Daily Work)", "⚙️ Settings (Manage BDEs)"])

# ---------------------------------------------------------
# TAB 2: SETTINGS (Manage BDEs & Locations)
# ---------------------------------------------------------
with tab2:
    st.header("Manage BDEs and Locations")
    st.info("Yahan aap jo BDE aur Locations save karenge, wo humesha save rahenge.")

    col1, col2 = st.columns(2)
    
    # Section 1: Add New BDE
    with col1:
        st.subheader("➕ Add New BDE")
        new_bde_name = st.text_input("BDE Name (e.g. Atul)")
        new_bde_locs = st.text_area("Locations (Comma se alag karein, e.g. Wagholi, Viman Nagar)")
        
        if st.button("Save BDE"):
            if new_bde_name and new_bde_locs:
                loc_list = [x.strip() for x in new_bde_locs.split(',') if x.strip()]
                bde_data[new_bde_name] = loc_list
                save_config(bde_data)
                st.success(f"✅ {new_bde_name} added with locations: {loc_list}")
                st.rerun()
            else:
                st.error("Naam aur Locations dono bharein.")

    # Section 2: View/Delete Existing BDEs
    with col2:
        st.subheader("📋 Current Team List")
        if bde_data:
            for name, locs in bde_data.items():
                with st.expander(f"👤 {name}"):
                    st.write(f"**Locations:** {', '.join(locs)}")
                    if st.button(f"Delete {name}", key=f"del_{name}"):
                        del bde_data[name]
                        save_config(bde_data)
                        st.rerun()
        else:
            st.warning("Abhi koi BDE saved nahi hai.")

# ---------------------------------------------------------
# TAB 1: MAIN TOOL (Processing Logic)
# ---------------------------------------------------------
with tab1:
    st.header("Daily File Processing")
    
    uploaded_files = st.file_uploader("Sabhi Master Excel Files yahan dalein", type=["xlsx", "csv"], accept_multiple_files=True)
    
    st.subheader("Select BDEs for Today's Output")
    if not bde_data:
        st.error("Pehle 'Settings' tab mein jaakar BDE add karein.")
    else:
        all_bdes = list(bde_data.keys())
        selected_bdes = st.multiselect("Kin BDEs ke liye file banani hai?", all_bdes, default=all_bdes)

        if uploaded_files and st.button("🚀 Process Files & Generate Output"):
            
            master_df_list = []
            for file in uploaded_files:
                try:
                    # Check file type
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
                    # Note: We convert to string and lower case to be safe
                    # Index 1 is the 2nd column
                    filtered_df = full_df[full_df.iloc[:, 1].astype(str).str.strip().str.lower() == 'res_resale']
                    
                    output_files_dict = {} 
                    today_str = datetime.now().strftime("%d%b%Y") 
                    
                    for bde in selected_bdes:
                        target_locations = [loc.lower() for loc in bde_data[bde]]
                        
                        # Location Check: Column F is Index 5 in Master File
                        location_col_idx = 5 
                        
                        mask = filtered_df.iloc[:, location_col_idx].astype(str).str.strip().str.lower().isin(target_locations)
                        bde_rows = filtered_df[mask].copy()
                        
                        if not bde_rows.empty:
                            # Create DataFrame with EXACT HEADERS from your sample file
                            final_df = pd.DataFrame(index=bde_rows.index, columns=OUTPUT_HEADERS)
                            
                            # --- MAPPING LOGIC (Based on Master File Indices) ---
                            # Master Columns: D=3, E=4, F=5, G=6, H=7, I=8, P=15
                            
                            # 1. Master D -> First Name
                            final_df['First Name'] = bde_rows.iloc[:, 3]
                            
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

                            # 7. Master P -> Price (Column AD in excel, 'Price' header)
                            final_df['Price'] = bde_rows.iloc[:, 15]
                            
                            # 8. Master F -> Area (Without P-)
                            final_df['Area'] = bde_rows.iloc[:, 5]
                            
                            # 9. Static Values
                            final_df['Property Type'] = "Residential"
                            final_df['Property Available For'] = "Sell"
                            
                            # Add to dictionary
                            filename = f"{bde}.{today_str}.xlsx"
                            output_files_dict[filename] = final_df
                    
                    if output_files_dict:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            for fname, data in output_files_dict.items():
                                with zf.open(fname, "w") as buffer:
                                    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                                        data.to_excel(writer, index=False)
                        
                        st.success(f"🎉 Success! {len(output_files_dict)} Files Created.")
                        st.download_button(
                            label="📥 Download All BDE Files (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name=f"Processed_Files_{today_str}.zip",
                            mime="application/zip"
                        )
                    else:
                        st.warning("Koi matching data nahi mila. Locations aur Master file check karein.")
                        
                except Exception as e:
                    st.error(f"Processing Error: {e}. Check karein ki Master File ka format sahi hai.")