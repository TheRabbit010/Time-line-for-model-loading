import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import re
from PIL import Image
import os
from datetime import timedelta, datetime
import math

# ==============================================================================
# 1. ฟังก์ชันสำหรับแยกประเภทเตาจากไฟล์ .PAQ
# ==============================================================================
def identify_furnace_type(text_to_search):
    furnace_id = "NB3" # Default
    if re.search(r'\b(RAD|CDS|KN9|12SHP|DNGA|P42QR|P42V|SU2|F44|Y4L)\b', text_to_search, re.IGNORECASE): 
        furnace_id = "NB1"
    elif re.search(r'\b(Utahc|UT|Tahc|G2|NB2)\b', text_to_search, re.IGNORECASE): 
        furnace_id = "NB2"
    elif re.search(r'\b(BTM|KE8|M2|EVO|NB3)\b', text_to_search, re.IGNORECASE): 
        furnace_id = "NB3"
    elif re.search(r'\bWK\d{1,2}\b', text_to_search, re.IGNORECASE) or re.search(r'\b\d{6}\b', text_to_search): 
        furnace_id = "NB1"
    else:
        f_match = re.search(r'NB\s*Furnace\s*0?([123])\b|NB\s*#?\s*0?([123])\b|NB-0?([123])\b', text_to_search, re.IGNORECASE)
        if f_match: 
            found_num = next(g for g in f_match.groups() if g is not None)
            furnace_id = f"NB{found_num}"
    return furnace_id

# ==============================================================================
# 2. ฟังก์ชันวิเคราะห์หาเตาจากข้อมูลใน Excel
# ==============================================================================
def detect_furnace_from_dataframe(df):
    text_data = ""
    for col in ['Description', 'Reference', 'WORKCENTERLIST']:
        if col in df.columns:
            text_data += " " + " ".join(df[col].dropna().astype(str).tolist())
            
    text_data = text_data.upper()
    
    nb1_kws = ["16XHP", "27XHP", "12XHP", "CMFB", "D15B", "DNGA", "P42QR", "W42JK", "F44", "F48", "DEMIO", "5H45V", "KN9", "N117", "YR9", "SU2", "Y4L", "GC7", "RADIATOR", "CONDENSER", "APU450"]
    nb2_kws = ["TAHC", "UTAHC", "CHORA", "HEATER CORE", "TK/NX5", "APU350"]
    nb3_kws = ["KE8", "X11C", "T34", "RBC", "K2", "J4LL", "BTM", "EVO", "CORION", "EVAPORATOR", "MAIN_COOLER", "APU214"]
    
    nb1_score = sum(text_data.count(kw) for kw in nb1_kws)
    nb2_score = sum(text_data.count(kw) for kw in nb2_kws)
    nb3_score = sum(text_data.count(kw) for kw in nb3_kws)
    
    if nb1_score == 0 and nb2_score == 0 and nb3_score == 0:
        return None
        
    scores = {"NB1": nb1_score, "NB2": nb2_score, "NB3": nb3_score}
    return max(scores, key=scores.get)

# ==============================================================================
# 3. ฐานข้อมูลโซนของเตา (Zone Lengths) อัปเดตล่าสุด
# ==============================================================================
FURNACE_ZONE_DATA = {
    "NB1": [
        {"name": "Entrance", "len": 2.00, "type": "Entrance"}, {"name": "Fluxer", "len": 2.70, "type": "Flux"},
        {"name": "Xfer", "len": 2.18, "type": "Xfer"}, {"name": "Dryer Z#1", "len": 6.03, "type": "Dryer"},
        {"name": "Dryer Z#2", "len": 6.03, "type": "Dryer"}, {"name": "EXT Dryer", "len": 0.68, "type": "Dryer"},
        {"name": "ENT DB", "len": 0.68, "type": "Debinder"}, {"name": "DB Z#1", "len": 3.10, "type": "Debinder"},
        {"name": "DB Z#2", "len": 2.60, "type": "Debinder"}, {"name": "DB Z#3", "len": 2.60, "type": "Debinder"},
        {"name": "DB Z#4", "len": 3.10, "type": "Debinder"}, {"name": "XFER#1", "len": 3.00, "type": "Xfer"},
        {"name": "Z#1", "len": 3.65, "type": "Heating"}, {"name": "Z#2", "len": 2.68, "type": "Heating"},
        {"name": "Z#3", "len": 2.36, "type": "Heating"}, {"name": "Z#4", "len": 2.02, "type": "Heating"},
        {"name": "Z#5", "len": 2.01, "type": "Heating"}, {"name": "Z#6", "len": 1.84, "type": "Heating"},
        {"name": "Z#7", "len": 2.81, "type": "Heating"}, {"name": "WatCool#1", "len": 2.39, "type": "Cooling"},
        {"name": "WatCool#2", "len": 1.41, "type": "Cooling"}, {"name": "Exit curtain", "len": 2.29, "type": "Cooling"},
        {"name": "XFER#2", "len": 0.22, "type": "Cooling"}, {"name": "Air Cool#1", "len": 1.25, "type": "Cooling"},
        {"name": "Air Cool#2", "len": 1.25, "type": "Cooling"}, {"name": "Exit", "len": 1.85, "type": "Exit"}
    ],
    "NB2": [
        {"name": "Entrance", "len": 2.00, "type": "Entrance"}, {"name": "Flux spray", "len": 4.70, "type": "Flux"},
        {"name": "Xfer 2", "len": 2.50, "type": "Xfer"}, {"name": "DryOFF-Z#1", "len": 2.83, "type": "Dryer"},
        {"name": "DryOFF-Z#2", "len": 2.83, "type": "Dryer"}, {"name": "Xfer1", "len": 3.00, "type": "Xfer"},
        {"name": "Z#1", "len": 3.65, "type": "Heating"}, {"name": "Z#2", "len": 2.68, "type": "Heating"},
        {"name": "Z#3", "len": 2.36, "type": "Heating"}, {"name": "Z#4", "len": 2.02, "type": "Heating"},
        {"name": "Z#5", "len": 2.01, "type": "Heating"}, {"name": "Z#6", "len": 1.84, "type": "Heating"},
        {"name": "Z#7", "len": 2.81, "type": "Heating"}, {"name": "WatCool#1", "len": 2.39, "type": "Cooling"},
        {"name": "WatCool#2", "len": 1.41, "type": "Cooling"}, {"name": "Exit curtain", "len": 2.29, "type": "Cooling"},
        {"name": "XFER#2", "len": 0.22, "type": "Cooling"}, {"name": "Air Cool#1", "len": 1.25, "type": "Cooling"},
        {"name": "Air Cool#2", "len": 1.25, "type": "Cooling"}, {"name": "Exit", "len": 1.85, "type": "Exit"}
    ],
    "NB3": [
        {"name": "Entrance", "len": 0.90, "type": "Entrance"}, {"name": "Fluxer", "len": 4.05, "type": "Flux"},
        {"name": "XFER", "len": 2.52, "type": "Xfer"}, {"name": "Dryer#1", "len": 1.88, "type": "Dryer"},
        {"name": "Dryer#2", "len": 1.88, "type": "Dryer"}, {"name": "Dryer#3", "len": 1.88, "type": "Dryer"},
        {"name": "XFER#1", "len": 3.00, "type": "Xfer"}, {"name": "Z#1", "len": 3.65, "type": "Heating"},
        {"name": "Z#2", "len": 2.68, "type": "Heating"}, {"name": "Z#3", "len": 2.36, "type": "Heating"},
        {"name": "Z#4", "len": 2.02, "type": "Heating"}, {"name": "Z#5", "len": 2.01, "type": "Heating"},
        {"name": "Z#6", "len": 1.84, "type": "Heating"}, {"name": "Z#7", "len": 2.81, "type": "Heating"},
        {"name": "WatCool#1", "len": 2.39, "type": "Cooling"}, {"name": "WatCool#2", "len": 1.41, "type": "Cooling"},
        {"name": "Exit curtain", "len": 2.50, "type": "Cooling"}, {"name": "AirCool#1", "len": 1.25, "type": "Cooling"},
        {"name": "AirCool#2", "len": 1.25, "type": "Cooling"}, {"name": "Exit", "len": 1.85, "type": "Exit"}
    ]
}

ZONE_COLORS = {
    "Entrance": "#D3D3D3", "Dryer": "#FFD700", "Debinder": "#FFA500", "Heating": "#FF4500",
    "Cooling": "#87CEFA", "Flux": "#9370DB", "Xfer": "#D3D3D3", "Exit": "#A9A9A9"
}

IMAGE_MAPPING = {
    "NB1": "Pic NB1.png", 
    "NB2": "Pic NB2.png",
    "NB3": "Pic NB3.png"
}

# ==============================================================================
# 4. ฐานข้อมูล Model Pitch และ Pieces per Pitch (อัปเดตจากไฟล์ Product Catalog)
# ==============================================================================
def get_model_info(description, furnace_id):
    desc = str(description).upper()
    
    if furnace_id == "NB1":
        # -- Radiator Specific --
        if "16XHP" in desc and "123T" in desc: return 1.041, 2
        if "27XHP" in desc and any(kw in desc for kw in ["64T", "73T", "123T"]): return 0.887, 2
        if "12XHP" in desc and "SU2" in desc: return 0.660, 2
        
        # -- Condenser Specific --
        if "CMFB" in desc: return 0.640, 2
        if "D15B" in desc: return 0.610, 2
        if "DNGA" in desc and not any(kw in desc for kw in ["DNGA1", "DNGA2"]): return 0.610, 2
        if "SU2" in desc: return 0.660, 2
        if "42QR" in desc or "P42QR" in desc or "W42JK" in desc: return 0.760, 2
        if "F44" in desc or "F48" in desc: return 0.660, 2
        if "5H45V" in desc: return 0.670, 2
        if "KN6 #6" in desc or "KN9 #6" in desc: return 0.760, 1
        
        return 0.790, 2 

    elif furnace_id == "NB2":
        # -- Heater Core (TAHC/UTAHC) Specific --
        if "P13C" in desc: return 0.370, 4
        if "SFTP" in desc or "KAMAZ" in desc: return 0.380, 3
        
        return 0.380, 4

    elif furnace_id == "NB3":
        # -- BTM (Battery Thermal Management) --
        if "N173" in desc or "KEI EV" in desc: return 1.400, 4
        if "N175" in desc or "OUTLANDER" in desc: return 1.260, 4
        if "M48" in desc: return 1.435, 2
        
        # -- Evaporator & Corion --
        if "KE8" in desc: return 0.370, 3
        if any(kw in desc for kw in ["NX5", "J4LL", "J2LL", "D2LL"]): return 0.363, 2
        if "RBC" in desc or "D12A" in desc: return 0.363, 3
        if "U825" in desc or "EMK" in desc: return 0.513, 3
        
        return 0.463, 3
        
    return 0.660, 2

# ==============================================================================
# 5. ส่วนของหน้าจอ Streamlit (UI)
# ==============================================================================
st.set_page_config(page_title="Furnace Product Simulation", page_icon="🔥", layout="wide")

current_nb_detected_paq = None

with st.sidebar:
    st.markdown("### 1. อัปโหลดไฟล์ข้อมูล Datapaq (.PAQ)")
    st.caption("อัปโหลดเพื่อระบุเตาอัตโนมัติ (ไม่บังคับ)")
    uploaded_file = st.file_uploader("📂 ลากไฟล์ .PAQ มาวางที่นี่", type=["paq"])

    if uploaded_file is not None:
        filename = uploaded_file.name
        current_nb_detected_paq = identify_furnace_type(filename)
        st.success(f"✅ อัปโหลดไฟล์ .PAQ สำเร็จ")

# ------------------------------------------------------------------------------
# Main Page
# ------------------------------------------------------------------------------
st.title("🔥 Furnace Product & Simulation")
st.markdown("ระบบจำลองตำแหน่งชิ้นงานในเตาอบประสาน (Brazing Furnace) โดยอ้างอิงจากแผนการโหลดชิ้นงานจริง")

# ==============================================================================
# 6. อัปโหลดและเตรียมข้อมูล Excel (มีปุ่ม Reset Data)
# ==============================================================================
st.markdown("### 📥 2. อัปโหลดแผนการผลิต (Excel)")

if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = str(datetime.now().timestamp())

col_up1, col_up2 = st.columns([4, 1])
with col_up1:
    uploaded_excels = st.file_uploader(
        "อัปโหลดไฟล์ข้อมูลแผนการผลิตของเตา (.xlsx หรือ .xls สามารถเลือกหลายไฟล์พร้อมกันได้)", 
        type=["xlsx", "xls"], 
        accept_multiple_files=True,
        key=st.session_state["file_uploader_key"]
    )

with col_up2:
    st.write("")
    st.write("")
    if st.button("🗑️ Reset / Clear Data", use_container_width=True):
        st.session_state["file_uploader_key"] = str(datetime.now().timestamp())
        st.rerun()

df_schedule_raw = pd.DataFrame()
current_nb_detected_excel = None

if uploaded_excels:
    st.success(f"✅ อัปโหลดไฟล์ Excel สำเร็จจำนวน {len(uploaded_excels)} ไฟล์")
    dfs = []
    for file in uploaded_excels:
        try:
            df_temp = pd.read_excel(file)
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ {file.name} ได้: {e}")
            
    if dfs:
        df_schedule_raw = pd.concat(dfs, ignore_index=True)
        current_nb_detected_excel = detect_furnace_from_dataframe(df_schedule_raw)

st.markdown("---")

# ==============================================================================
# 7. ตั้งค่าพารามิเตอร์เตา
# ==============================================================================
st.markdown("### ⚙️ 3. ตั้งค่าพารามิเตอร์เตา")
col1, col2 = st.columns(2)

with col1:
    auto_detected_nb = current_nb_detected_paq or current_nb_detected_excel
    
    if auto_detected_nb:
        source_msg = ".PAQ" if current_nb_detected_paq else "Excel"
        st.info(f"🔥 ระบบตรวจพบเตาจากไฟล์ {source_msg}: **{auto_detected_nb}**")
        current_nb = auto_detected_nb
    else:
        current_nb = st.selectbox("🔥 เลือกเตา (Manual):", ["NB1", "NB2", "NB3"], index=2)

default_speeds = {
    "NB1": 1.40,
    "NB2": 1.56,
    "NB3": 1.27
}
default_speed_for_current_nb = default_speeds.get(current_nb, 1.40)

with col2:
    belt_speed_m_min = st.number_input(
        "ความเร็วสายพาน (เมตร/นาที)", 
        min_value=0.1, 
        max_value=5.0, 
        value=default_speed_for_current_nb, 
        step=0.01, 
        format="%.2f"
    )
    belt_speed_ms = belt_speed_m_min / 60.0  
    st.caption("ℹ️ *ระยะห่าง (Pitch) และการจัดเรียงถูกคำนวณอัตโนมัติจากฐานข้อมูลตามรุ่น*")

st.markdown("---")

# ==============================================================================
# 8. ประมวลผลข้อมูลชิ้นงาน
# ==============================================================================
zones = FURNACE_ZONE_DATA[current_nb]
cumulative_len = 0
furnace_zones_df = []
for z in zones:
    start = cumulative_len
    end = cumulative_len + z["len"]
    furnace_zones_df.append({
        "Name": z["name"], "Type": z["type"], "Length": z["len"], 
        "Start": start, "End": end
    })
    cumulative_len = end

total_furnace_length = cumulative_len
df_zones = pd.DataFrame(furnace_zones_df)
all_zone_labels = df_zones["Name"].tolist()

df_pieces = pd.DataFrame()

if not df_schedule_raw.empty:
    required_cols = ['Description', 'Quantity', 'Start Time']
    if all(col in df_schedule_raw.columns for col in required_cols):
        df_schedule = df_schedule_raw.dropna(subset=['Start Time', 'Quantity']).copy()
        df_schedule = df_schedule[df_schedule['Quantity'] > 0]
        
        df_schedule['Start Time'] = pd.to_datetime(df_schedule['Start Time'])
        df_schedule = df_schedule.sort_values('Start Time')
        
        preview_cols = required_cols.copy()
        if 'Reference' in df_schedule.columns:
            preview_cols.insert(0, 'Reference')
        if 'WORKCENTERLIST' in df_schedule.columns:
            preview_cols.append('WORKCENTERLIST')
            
        with st.expander("ดูข้อมูลแผนการผลิต (Data Preview)"):
            st.dataframe(df_schedule[preview_cols].head(50), use_container_width=True)
            
        pieces_list = []
        next_available_time = None  
        
        for _, row in df_schedule.iterrows():
            qty = int(row['Quantity'])
            start_t = row['Start Time']
            desc = str(row['Description'])
            desc_upper = desc.upper()
            
            ref = str(row['Reference']) if 'Reference' in df_schedule.columns else ""
            ref_upper = ref.upper()
            
            # --- คำนวณจุดเริ่มต้นรายโมเดลอัตโนมัติ (Per-Model Start Offset) ---
            model_start_offset = 0.0
            if current_nb == "NB3":
                # เพิ่ม Keywords อ้างอิงตามรูปให้ครอบคลุม BTM และ Corion ทั้งหมด (อัปเดตใหม่)
                btm_corion_kws = [
                    "BTM", "CORION", 
                    "AT425115", "AT425220", "ATA44035", "M48", "N173", "N175", "XC2C", 
                    "4L45V", "T175297", "T425109", "T425224", "T425259", "T47938C", 
                    "T47955C", "T625769", "KEI EV", "P33B", "OUTLANDER", 
                    "A5", "A5+", "A5@", "P1MM", "DUMMY EVAP", "A669223C", "KE8"
                ]
                # ตรวจสอบทั้งช่อง Description และ Reference
                if any(kw in desc_upper for kw in btm_corion_kws) or any(kw in ref_upper for kw in btm_corion_kws):
                    # ข้าม Entrance (0.90) และ Fluxer (4.05) รวมเป็น 4.95 เมตร เริ่มตกที่ XFER พอดี
                    model_start_offset = 4.95
                    # บวกค่า Epsilon เล็กน้อยเพื่อให้ค่าน้อยกว่า XFER ตกอยู่ในโซน XFER แน่นอนสำหรับการประมวลผลตาราง
                    model_start_offset += 0.001 
            # -----------------------------------------------------------

            pitch_m, pieces_per_pitch = get_model_info(desc, current_nb)
            interval_s = pitch_m / belt_speed_ms
            
            rows_to_load = int(math.ceil(qty / pieces_per_pitch))
            
            if next_available_time is None or start_t > next_available_time:
                current_load_time = start_t
            else:
                current_load_time = next_available_time
            
            for i in range(rows_to_load):
                pieces_list.append({
                    'Reference': ref,
                    'Model': desc,
                    'LoadTime': current_load_time,
                    'Pitch_m': pitch_m,
                    'Speed_ms': belt_speed_ms,
                    'Pieces_in_Box': pieces_per_pitch,
                    'Start_Offset_m': model_start_offset
                })
                current_load_time += pd.Timedelta(seconds=interval_s)
            
            next_available_time = current_load_time
        
        df_pieces = pd.DataFrame(pieces_list)
        if not df_pieces.empty:
            df_pieces = df_pieces.sort_values('LoadTime').reset_index(drop=True)
            
            # การคำนวณระยะทางที่เหลือ (เช่น BTM จะเป็น 44.13 - 4.95 = 39.18 เมตร)
            df_pieces['Remaining_Dist'] = total_furnace_length - df_pieces['Start_Offset_m']
            # เวลาที่ออกจากเตาจะใช้ระยะทางที่เหลือหารความเร็ว
            df_pieces['ExitTime'] = df_pieces['LoadTime'] + pd.to_timedelta(df_pieces['Remaining_Dist'] / df_pieces['Speed_ms'], unit='s')
            
            df_pieces['Display_Model'] = df_pieces.apply(
                lambda x: f"{x['Model']} ({x['Reference']})" if pd.notna(x.get('Reference')) and str(x.get('Reference')).strip() not in ["", "nan"] else x['Model'],
                axis=1
            )
    else:
        st.error(f"❌ ไฟล์ Excel ต้องมีคอลัมน์ต่อไปนี้: {', '.join(required_cols)}")

# ==============================================================================
# 9. กราฟจำลอง Simulation
# ==============================================================================
fig = go.Figure()

for idx, row in df_zones.iterrows():
    fig.add_shape(
        type="rect", x0=row["Start"], x1=row["End"], y0=0, y1=1,
        fillcolor=ZONE_COLORS.get(row["Type"], "#ccc"), line=dict(color="white", width=1),
        layer="below"
    )
    fig.add_annotation(
        x=(row["Start"] + row["End"]) / 2, y=0.5,
        text=row["Name"], showarrow=False, textangle=-90,
        font=dict(size=11, color="black" if row["Type"] in ["Dryer", "Xfer", "Cooling"] else "white")
    )

fig.add_shape(
    type="line", x0=0, x1=total_furnace_length, y0=1.2, y1=1.2,
    line=dict(color="gray", width=2, dash="dot"), layer="below"
)

df_current = pd.DataFrame()

if not df_pieces.empty:
    min_time = df_pieces['LoadTime'].min()
    max_time = df_pieces['LoadTime'].max() + pd.Timedelta(minutes=90) 
    min_dt = min_time.to_pydatetime()
    max_dt = max_time.to_pydatetime()
    
    if 'current_sim_time' not in st.session_state or st.session_state.current_sim_time < min_dt or st.session_state.current_sim_time > max_dt:
        st.session_state.current_sim_time = min_dt
        st.session_state.date_input_val = min_dt.date()
        st.session_state.time_input_val = min_dt.strftime("%H:%M:%S")
        st.session_state.sim_time_slider = min_dt
        
    current_sim = st.session_state.current_sim_time
    
    df_pieces['Elapsed_s'] = (pd.to_datetime(current_sim) - df_pieces['LoadTime']).dt.total_seconds()
    
    # อิงตำแหน่งตาม Start Offset ของแต่ละชิ้น 
    df_pieces['Position'] = df_pieces['Start_Offset_m'] + (df_pieces['Elapsed_s'] * df_pieces['Speed_ms'])
    
    df_current = df_pieces[(df_pieces['Position'] >= df_pieces['Start_Offset_m']) & (df_pieces['Position'] <= total_furnace_length)].copy()
    
    color_sequence = px.colors.qualitative.Plotly
    
    if not df_current.empty:
        for i, (display_model_name, group) in enumerate(df_current.groupby('Display_Model')):
            customdata = np.stack((
                group['LoadTime'].dt.strftime('%H:%M:%S'),
                group['ExitTime'].dt.strftime('%H:%M:%S')
            ), axis=-1)

            fig.add_trace(go.Scatter(
                x=group['Position'], y=[1.2] * len(group),
                mode="markers", name=display_model_name, 
                marker=dict(symbol="square", size=12, color=color_sequence[i % len(color_sequence)], line=dict(width=1, color="black")),
                hovertemplate=f"<b>{display_model_name}</b><br>ตำแหน่ง: %{{x:.2f}} ม.<br>โหลดเข้า: %{{customdata[0]}}<br>ออกเตา: %{{customdata[1]}}<extra></extra>",
                customdata=customdata
            ))

else:
    st.info("💡 **ข้อมูลการโหลดชิ้นงานยังว่างเปล่า** อัปโหลดไฟล์ Excel ด้านบนเพื่อดูตำแหน่งจริงและเวลาที่สัมพันธ์กัน")
    
    pitch_m = 0.660
    # แสดงตำแหน่งเริ่มต้นให้สัมพันธ์กับเตา NB3
    start_pos = 4.95 if current_nb == "NB3" else 0.0
    product_positions = np.arange(start_pos, total_furnace_length, pitch_m)
    fig.add_trace(go.Scatter(
        x=product_positions, y=[1.2] * len(product_positions),
        mode="markers", name="ตัวอย่าง (Sample Data)",
        marker=dict(symbol="square", size=12, color="#32CD32", line=dict(width=2, color="black")),
        hovertemplate="ตำแหน่ง: %{x:.2f} เมตร<extra></extra>"
    ))

img_file_sim = IMAGE_MAPPING.get(current_nb)
y_range = [-0.2, 1.8] 

if img_file_sim and os.path.exists(img_file_sim):
    img = Image.open(img_file_sim)
    fig.add_layout_image(
        dict(
            source=img, xref="x", yref="y",
            x=0, y=3.2, sizex=total_furnace_length, sizey=1.6, 
            sizing="stretch", opacity=1, layer="above"
        )
    )
    y_range = [-0.2, 3.5]

fig.update_layout(
    title=f"Furnace Timeline: {current_nb} (Total Length: {total_furnace_length:.2f} m)",
    xaxis=dict(title="Distance (Meters)", range=[0, total_furnace_length], tickmode="linear", tick0=0, dtick=2),
    yaxis=dict(visible=False, range=y_range),
    height=550, 
    margin=dict(l=20, r=20, t=50, b=120), 
    template="plotly_white", hovermode="x unified",
    showlegend=True, 
    legend=dict(
        orientation="h", 
        yanchor="top", 
        y=-0.25, 
        xanchor="center", 
        x=0.5
    )
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# 10. Time Slider & Manual Inputs
# ------------------------------------------------------------------------------
if not df_pieces.empty:
    st.markdown("---")
    st.markdown("### ⏱️ ควบคุมเวลาจำลอง (Simulation Time)")
    
    def on_slider_change():
        new_dt = st.session_state.sim_time_slider
        st.session_state.current_sim_time = new_dt
        st.session_state.date_input_val = new_dt.date()
        st.session_state.time_input_val = new_dt.strftime("%H:%M:%S")

    def on_input_change():
        try:
            d = st.session_state.date_input_val
            t_str = st.session_state.time_input_val
            t = pd.to_datetime(t_str, format="%H:%M:%S").time()
            new_dt = datetime.combine(d, t)
            
            if new_dt < min_dt: new_dt = min_dt
            if new_dt > max_dt: new_dt = max_dt
            
            st.session_state.current_sim_time = new_dt
            st.session_state.sim_time_slider = new_dt
            st.session_state.date_input_val = new_dt.date()
            st.session_state.time_input_val = new_dt.strftime("%H:%M:%S")
        except ValueError:
            pass 
            
    col_d, col_t = st.columns(2)
    with col_d:
        st.date_input(
            "📅 เลือกวันที่ (Date)", 
            min_value=min_dt.date(),
            max_value=max_dt.date(),
            key="date_input_val",
            on_change=on_input_change
        )
    with col_t:
        st.text_input(
            "⏰ ป้อนเวลา (Time) เช่น 19:32:00", 
            key="time_input_val",
            on_change=on_input_change,
            help="กรุณาป้อนเวลาในรูปแบบ ชั่วโมง:นาที:วินาที (HH:MM:SS) ตัวอย่าง: 19:32:00"
        )
    
    try:
        pd.to_datetime(st.session_state.time_input_val, format="%H:%M:%S")
    except ValueError:
        st.error("⚠️ รูปแบบเวลาไม่ถูกต้อง! กรุณาป้อนเวลาในรูปแบบ HH:MM:SS (เช่น 19:32:00)")

    st.slider(
        "ลากเพื่อเลื่อนดูเวลาจำลอง (Slide to Simulator Time):", 
        min_value=min_dt, 
        max_value=max_dt, 
        step=timedelta(seconds=1),
        format="YYYY-MM-DD HH:mm:ss",
        key="sim_time_slider",
        on_change=on_slider_change
    )
    
    # ==============================================================================
    # 11. ตารางรายละเอียดรายโซน
    # ==============================================================================
    st.markdown(f"### 📋 รายละเอียดชิ้นงานรายโซน ณ เวลา **{st.session_state.current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}**")
    
    if not df_current.empty:
        bins = [0] + df_zones["End"].tolist()
        df_current['Zone'] = pd.cut(df_current['Position'], bins=bins, labels=all_zone_labels, right=True)
        
        df_current['Display_Model_Table'] = df_current.apply(
            lambda x: f"{x['Model']}\n{x['Reference']}" if pd.notna(x.get('Reference')) and str(x.get('Reference')).strip() not in ["", "nan"] else x['Model'],
            axis=1
        )
        
        wip_summary = df_current.groupby(['Zone', 'Display_Model_Table'], observed=False).agg(
            Box_Count=('Display_Model_Table', 'size'),
            Multiplier=('Pieces_in_Box', 'first') 
        ).reset_index()
        
        wip_summary = wip_summary[wip_summary['Box_Count'] > 0]
        wip_summary['Quantity'] = wip_summary['Box_Count'] * wip_summary['Multiplier']
        
        wip_pivot = wip_summary.pivot(index='Display_Model_Table', columns='Zone', values='Quantity').fillna(0).astype(int)
        wip_pivot.index.name = 'Model (Reference)'
        
        wip_pivot = wip_pivot.reindex(columns=all_zone_labels, fill_value=0)
        
        # --- คำนวณผลรวมรายโซน และผลรวมทั้งหมด ---
        wip_pivot.loc['Total (รวม)'] = wip_pivot.sum(numeric_only=True)
        grand_total = int(wip_pivot.loc['Total (รวม)'].sum())
        
        st.success(f"📌 **มีชิ้นงานในกระบวนการเตาทั้งหมด ณ เวลานี้: {grand_total:,} ชิ้น**")

        def highlight_nonzero(val):
            if isinstance(val, (int, float)) and val > 0:
                return 'background-color: #E8E8E8; color: #000000; font-weight: bold;'
            return ''
            
        def highlight_total_row(row):
            if row.name == 'Total (รวม)':
                return ['background-color: #FFF2CC; font-weight: bold; color: #000000'] * len(row)
            return [''] * len(row)
            
        if hasattr(wip_pivot.style, 'map'):
            styled_pivot = (wip_pivot.style
                            .map(highlight_nonzero)
                            .apply(highlight_total_row, axis=1)
                            .format(precision=0))
        else:
            styled_pivot = (wip_pivot.style
                            .applymap(highlight_nonzero)
                            .apply(highlight_total_row, axis=1)
                            .format(precision=0))
            
        st.dataframe(styled_pivot, use_container_width=True)
    else:
        empty_df = pd.DataFrame(columns=all_zone_labels)
        empty_df.index.name = 'Model (Reference)'
        st.dataframe(empty_df, use_container_width=True)
        wip_summary = pd.DataFrame(columns=['Zone', 'Display_Model_Table', 'Box_Count', 'Multiplier', 'Quantity'])

    # ==============================================================================
    # 12. กล่องสรุปชิ้นงานตามกลุ่มกระบวนการ
    # ==============================================================================
    st.markdown("### 📊 สรุปจำนวนชิ้นงานตามกลุ่มกระบวนการ (Process Group Summary)")
    
    zone_type_mapping = {}
    for z in FURNACE_ZONE_DATA[current_nb]:
        if "XFER" in z['name'].upper():
            zone_type_mapping[z['name']] = z['name']
        else:
            zone_type_mapping[z['name']] = z['type']
    
    display_type_names = {
        "Entrance": "🚪 Entrance (หน้าเตา)",
        "Heating": "🔥 Brazing Zone (Z#1 - Z#7)",
        "Dryer": "💨 Dryer Zone",
        "Debinder": "♨️ Debinder Zone",
        "Cooling": "❄️ Cooling Zone",
        "Flux": "💧 Flux Zone",
        "Exit": "🏁 Exit (ท้ายเตา)"
    }
    
    ordered_types = []
    for z in FURNACE_ZONE_DATA[current_nb]:
        t = zone_type_mapping[z['name']]
        if t not in ordered_types:
            ordered_types.append(t)
            
        if t not in display_type_names:
            display_type_names[t] = f"↔️ {t} (จุดเชื่อมต่อ)"
            
    ordered_display_groups = [display_type_names[t] for t in ordered_types]
    
    if not wip_summary.empty:
        wip_summary['Process_Group_Raw'] = wip_summary['Zone'].map(zone_type_mapping)
        wip_summary['Process_Group'] = wip_summary['Process_Group_Raw'].map(display_type_names)
        
        group_summary = wip_summary.groupby(['Process_Group', 'Display_Model_Table'], observed=False).agg(
            Quantity=('Quantity', 'sum'),
            Box_Count=('Box_Count', 'sum')
        ).reset_index()
        group_summary = group_summary[group_summary['Quantity'] > 0]
    else:
        group_summary = pd.DataFrame(columns=['Process_Group', 'Display_Model_Table', 'Quantity', 'Box_Count'])
    
    if not group_summary.empty:
        chart_data = group_summary.groupby('Process_Group', observed=False).agg(
            Quantity=('Quantity', 'sum'),
            Box_Count=('Box_Count', 'sum')
        ).reset_index()
        
        chart_data['Process_Group'] = pd.Categorical(chart_data['Process_Group'], categories=ordered_display_groups, ordered=True)
        chart_data = chart_data.sort_values('Process_Group')
        
        fig_bar = px.bar(
            chart_data, 
            x='Process_Group', 
            y='Quantity', 
            text='Quantity',
            labels={'Process_Group': '', 'Quantity': 'จำนวนชิ้นงาน (ชิ้น)'},
            color='Quantity',
            color_continuous_scale=px.colors.sequential.Blues
        )
        
        fig_bar.update_traces(
            texttemplate='<b>%{text} ชิ้น</b>', 
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>จำนวน: %{y} ชิ้น<extra></extra>',
            marker_line_color='rgb(8,48,107)',
            marker_line_width=1.5,
            opacity=0.85
        )
        
        fig_bar.update_layout(
            template='plotly_white',
            height=400,
            margin=dict(t=30, b=50, l=20, r=20),
            xaxis=dict(tickangle=-45, title_font=dict(size=14)),
            yaxis=dict(title="จำนวน (ชิ้น)", showgrid=True, gridcolor='#E5E5E5'),
            coloraxis_showscale=False
        )
        
        max_qty = chart_data['Quantity'].max()
        fig_bar.update_yaxes(range=[0, max_qty * 1.2])

        st.plotly_chart(fig_bar, use_container_width=True)

    if len(ordered_display_groups) > 0:
        cols = st.columns(3)
        for idx, p_group in enumerate(ordered_display_groups):
            col = cols[idx % 3]
            with col:
                df_pg = group_summary[group_summary['Process_Group'] == p_group]
                total_qty = int(df_pg['Quantity'].sum()) if not df_pg.empty else 0
                total_pitches = int(df_pg['Box_Count'].sum()) if not df_pg.empty else 0
                
                with st.container(border=True):
                    st.markdown(f"**{p_group}**")
                    if total_qty > 0:
                        st.markdown(f"### รวม: {total_qty} ชิ้น ({total_pitches} pitches)")
                        for _, r in df_pg.iterrows():
                            model_name_inline = r['Display_Model_Table'].replace('\n', ' ')
                            qty = int(r['Quantity'])
                            pitches = int(r['Box_Count'])
                            st.caption(f"• {model_name_inline} : {qty} ชิ้น ({pitches} pitches)")
                    else:
                        st.markdown("### รวม: 0 ชิ้น")
                        st.caption("ไม่มีชิ้นงาน")
    else:
        st.info("ไม่มีกระบวนการหลักในเตานี้")
