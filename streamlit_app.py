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
# 1. ฟังก์ชันสำหรับแยกประเภทเตา (NB1, NB2, NB3) จากชื่อไฟล์
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
# 2. ฐานข้อมูลโซนของเตา (Zone Lengths) อัปเดตล่าสุด
# ==============================================================================
FURNACE_ZONE_DATA = {
    "NB1": [
        {"name": "Entrance", "len": 2.00, "type": "Xfer"}, {"name": "Fluxer", "len": 2.70, "type": "Flux"},
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
        {"name": "Entrance", "len": 2.02, "type": "Xfer"}, {"name": "Fluxer", "len": 4.70, "type": "Flux"},
        {"name": "Xfer", "len": 2.00, "type": "Xfer"}, {"name": "Flux spray", "len": 4.70, "type": "Flux"},
        {"name": "Xfer", "len": 2.50, "type": "Xfer"}, {"name": "DryOFF-Z#1", "len": 2.83, "type": "Dryer"},
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
        {"name": "Entrance", "len": 0.90, "type": "Xfer"}, {"name": "Fluxer", "len": 4.05, "type": "Flux"},
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
    "Dryer": "#FFD700", "Debinder": "#FFA500", "Heating": "#FF4500",
    "Cooling": "#87CEFA", "Flux": "#9370DB", "Xfer": "#D3D3D3", "Exit": "#A9A9A9"
}

IMAGE_MAPPING = {
    "NB1": "Screenshot 2026-10-21 083432.png", 
    "NB2": "Screenshot 2026-10-20 144037.png",
    "NB3": "Screenshot 2026-10-20 144101.png"
}

# ==============================================================================
# 3. ฐานข้อมูล Model Pitch และ Pieces per Pitch
# ==============================================================================
def get_model_info(description, furnace_id):
    desc = str(description).upper()
    
    if furnace_id == "NB1":
        if "KN9 #6" in desc: return 760 / 1000.0, 1
        if "KN9" in desc: return 790 / 1000.0, 2
        if "D12A" in desc: return 790 / 1000.0, 2
        if "Y4L" in desc: return 790 / 1000.0, 2
        if "T36" in desc: return 790 / 1000.0, 2
        if "N117" in desc: return 790 / 1000.0, 2
        if "YR9" in desc: return 790 / 1000.0, 2
        if "F44" in desc or "F48" in desc: return 660 / 1000.0, 2
        if "DEMIO DE" in desc: return 565 / 1000.0, 2
        if "DEMIO CE" in desc: return 590 / 1000.0, 2
        if "CMFB" in desc: return 640 / 1000.0, 2
        if "P42QRMY25" in desc: return 765 / 1000.0, 2
        if "P42QR" in desc or "W42JK" in desc: return 760 / 1000.0, 2
        if "SU2" in desc and "RAD" not in desc: return 660 / 1000.0, 2
        if "DNGA" in desc or "D15B" in desc: return 610 / 1000.0, 2
        if "5H45V" in desc: return 670 / 1000.0, 2
        if "RAD 12XHP SU2" in desc: return 580 / 1000.0, 2
        if "RAD16XHP" in desc: return 1041 / 1000.0, 2
        if "RAD27XHP" in desc: return 887 / 1000.0, 2
        if "RAD P13C" in desc: return 518 / 1000.0, 2
        return 660 / 1000.0, 2 

    elif furnace_id == "NB2":
        if "DUMMY" in desc: return 355 / 1000.0, 4
        if "P13C" in desc: return 370 / 1000.0, 4
        return 380 / 1000.0, 4

    elif furnace_id == "NB3":
        if "KE8" in desc: return 370 / 1000.0, 3
        if any(kw in desc for kw in ["X11C", "T34", "D12A", "RBC", "K2"]): return 383 / 1000.0, 3
        if "J4LL" in desc: return 383 / 1000.0, 2 
        if "BTM N175" in desc: return 1280 / 1000.0, 2
        if "BTM N173" in desc: return 1400 / 1000.0, 2
        if "BTM M48" in desc: return 1435 / 1000.0, 1
        return 463 / 1000.0, 3
        
    return 660 / 1000.0, 2

# ==============================================================================
# 4. ส่วนของหน้าจอ Streamlit (UI)
# ==============================================================================
st.set_page_config(page_title="Furnace Product Simulation", page_icon="🔥", layout="wide")

current_nb_detected = None

with st.sidebar:
    st.markdown("### 1. อัปโหลดไฟล์ข้อมูล Datapaq (.PAQ)")
    st.caption("อัปโหลดเพื่อระบุเตาอัตโนมัติ (ไม่บังคับ)")
    uploaded_file = st.file_uploader("📂 ลากไฟล์ .PAQ มาวางที่นี่", type=["paq"])

    if uploaded_file is not None:
        filename = uploaded_file.name
        current_nb_detected = identify_furnace_type(filename)
        st.success(f"✅ อัปโหลดไฟล์ .PAQ สำเร็จ")

# ------------------------------------------------------------------------------
# Main Page
# ------------------------------------------------------------------------------
st.title("🔥 Furnace Product & Simulation")
st.markdown("ระบบจำลองตำแหน่งชิ้นงานในเตาอบประสาน (Brazing Furnace) โดยอ้างอิงจากแผนการโหลดชิ้นงานจริง")

# ==============================================================================
# 5. อัปโหลดและประมวลผลข้อมูล Excel
# ==============================================================================
st.markdown("### 📥 2. อัปโหลดแผนการผลิต (Excel)")
uploaded_excels = st.file_uploader(
    "อัปโหลดไฟล์ข้อมูลแผนการผลิตของเตา (.xlsx หรือ .xls สามารถเลือกหลายไฟล์พร้อมกันได้)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

if uploaded_excels:
    st.success(f"✅ อัปโหลดไฟล์ Excel สำเร็จจำนวน {len(uploaded_excels)} ไฟล์")

st.markdown("---")

# ==============================================================================
# 6. ตั้งค่าพารามิเตอร์เตา 
# ==============================================================================
st.markdown("### ⚙️ 3. ตั้งค่าพารามิเตอร์เตา")
col1, col2 = st.columns(2)

with col1:
    if current_nb_detected:
        st.info(f"🔥 ระบบตรวจพบเตาจากไฟล์ .PAQ: **{current_nb_detected}**")
        current_nb = current_nb_detected
    else:
        current_nb = st.selectbox("🔥 เลือกเตา (Manual):", ["NB1", "NB2", "NB3"], index=2)

with col2:
    belt_speed_m_min = st.number_input("ความเร็วสายพาน (เมตร/นาที)", min_value=0.1, max_value=5.0, value=1.40, step=0.10, format="%.2f")
    belt_speed_ms = belt_speed_m_min / 60.0  
    st.caption("ℹ️ *ระยะห่าง (Pitch) และการจัดเรียงถูกคำนวณอัตโนมัติจากฐานข้อมูลตามรุ่น*")

st.markdown("---")

# ==============================================================================
# 7. ประมวลผลข้อมูลชิ้นงาน
# ==============================================================================
df_pieces = pd.DataFrame()

if uploaded_excels:
    dfs = []
    for file in uploaded_excels:
        try:
            df_temp = pd.read_excel(file)
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ {file.name} ได้: {e}")
            
    if dfs:
        df_schedule = pd.concat(dfs, ignore_index=True)
        
        required_cols = ['Description', 'Quantity', 'Start Time']
        if all(col in df_schedule.columns for col in required_cols):
            df_schedule = df_schedule.dropna(subset=['Start Time', 'Quantity'])
            df_schedule = df_schedule[df_schedule['Quantity'] > 0]
            
            df_schedule['Start Time'] = pd.to_datetime(df_schedule['Start Time'])
            df_schedule = df_schedule.sort_values('Start Time')
            
            # พรีวิวข้อมูล
            preview_cols = required_cols.copy()
            if 'Reference' in df_schedule.columns:
                preview_cols.insert(0, 'Reference')
            
            with st.expander("ดูข้อมูลแผนการผลิต (Data Preview)"):
                st.dataframe(df_schedule[preview_cols].head(50), use_container_width=True)
                
            pieces_list = []
            next_available_time = None  
            
            for _, row in df_schedule.iterrows():
                qty = int(row['Quantity'])
                start_t = row['Start Time']
                desc = str(row['Description'])
                
                # ดึงค่า Reference ถ้ามี
                ref = str(row['Reference']) if 'Reference' in df_schedule.columns else ""
                
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
                        'Pieces_in_Box': pieces_per_pitch
                    })
                    current_load_time += pd.Timedelta(seconds=interval_s)
                
                next_available_time = current_load_time
            
            df_pieces = pd.DataFrame(pieces_list)
            if not df_pieces.empty:
                df_pieces = df_pieces.sort_values('LoadTime').reset_index(drop=True)
        else:
            st.error(f"❌ ไฟล์ Excel ต้องมีคอลัมน์ต่อไปนี้: {', '.join(required_cols)}")

# ==============================================================================
# 8. กราฟจำลอง Simulation
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
    df_pieces['Position'] = df_pieces['Elapsed_s'] * df_pieces['Speed_ms']
    
    df_current = df_pieces[(df_pieces['Position'] >= 0) & (df_pieces['Position'] <= total_furnace_length)]
    
    color_sequence = px.colors.qualitative.Plotly
    
    if not df_current.empty:
        for i, (model_name, group) in enumerate(df_current.groupby('Model')):
            fig.add_trace(go.Scatter(
                x=group['Position'], y=[1.2] * len(group),
                mode="markers", name=model_name,
                marker=dict(symbol="square", size=12, color=color_sequence[i % len(color_sequence)], line=dict(width=1, color="black")),
                hovertemplate=f"<b>{model_name}</b><br>ตำแหน่ง: %{{x:.2f}} ม.<br>โหลดเข้า: %{{customdata}}<extra></extra>",
                customdata=group['LoadTime'].dt.strftime('%H:%M:%S')
            ))

else:
    st.info("💡 **ข้อมูลการโหลดชิ้นงานยังว่างเปล่า** อัปโหลดไฟล์ Excel ด้านบนเพื่อดูตำแหน่งจริงและเวลาที่สัมพันธ์กัน")
    
    pitch_m = 0.660
    product_positions = np.arange(0, total_furnace_length, pitch_m)
    fig.add_trace(go.Scatter(
        x=product_positions, y=[1.2] * len(product_positions),
        mode="markers", name="ตัวอย่าง (Sample Data)",
        marker=dict(symbol="square", size=12, color="#32CD32", line=dict(width=2, color="black")),
        hovertemplate="ตำแหน่ง: %{x:.2f} เมตร<extra></extra>"
    ))

img_file_sim = IMAGE_MAPPING.get(current_nb)
y_range = [-0.2, 1.8] 

if os.path.exists(img_file_sim):
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
    height=450, margin=dict(l=20, r=20, t=50, b=40),
    template="plotly_white", hovermode="x unified",
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# 9. Time Slider & Manual Inputs (Two-way binding)
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
    
    st.markdown(f"### 📋 สรุปจำนวนชิ้นงานในเตา ณ เวลา **{st.session_state.current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}**")
    if not df_current.empty:
        bins = [0] + df_zones["End"].tolist()
        labels = df_zones["Name"].tolist()
        df_current['Zone'] = pd.cut(df_current['Position'], bins=bins, labels=labels, right=True)
        
        # ----------------------------------------------------------------------
        # แปลง Model Name ให้รวม Reference ไว้ในบรรทัดใหม่เฉพาะในตาราง
        # ----------------------------------------------------------------------
        df_current['Display_Model'] = df_current.apply(
            lambda x: f"{x['Model']}\n{x['Reference']}" if pd.notna(x.get('Reference')) and str(x.get('Reference')).strip() not in ["", "nan"] else x['Model'],
            axis=1
        )
        
        wip_summary = df_current.groupby(['Zone', 'Display_Model'], observed=False).agg(
            Box_Count=('Display_Model', 'size'),
            Multiplier=('Pieces_in_Box', 'first') 
        ).reset_index()
        
        wip_summary = wip_summary[wip_summary['Box_Count'] > 0]
        wip_summary['Quantity'] = wip_summary['Box_Count'] * wip_summary['Multiplier']
        
        wip_pivot = wip_summary.pivot(index='Display_Model', columns='Zone', values='Quantity').fillna(0).astype(int)
        
        # เปลี่ยนหัวคอลัมน์ Index เพื่อความสวยงาม
        wip_pivot.index.name = 'Model'
        
        st.dataframe(wip_pivot, use_container_width=True)
    else:
        st.info("ไม่มีชิ้นงานอยู่ในเตา ณ เวลาที่เลือก")
