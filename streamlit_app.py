import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import re
from PIL import Image
import os
from datetime import timedelta

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
# 2. ฐานข้อมูลโซนของเตา (Zone Lengths) และ Model Pitch
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
        {"name": "WatCool#2", "len": 1.41, "type": "Cooling"}, {"name": "Exit curtain", "len": 2.10, "type": "Cooling"},
        {"name": "XFER#2", "len": 0.40, "type": "Cooling"}, {"name": "Air Cool#1", "len": 1.25, "type": "Cooling"},
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
        {"name": "WatCool#2", "len": 1.41, "type": "Cooling"}, {"name": "Exit curtain", "len": 2.10, "type": "Cooling"},
        {"name": "XFER#2", "len": 0.40, "type": "Cooling"}, {"name": "Air Cool#1", "len": 1.25, "type": "Cooling"},
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

MODEL_DB = pd.DataFrame([
    {"Model": "New design standard dummy SUS304L", "Pitch (mm)": 350},
    {"Model": "Dummy SUS", "Pitch (mm)": 455},
    {"Model": "Dummy KN9", "Pitch (mm)": 790},
    {"Model": "KN9 #6", "Pitch (mm)": 760},
    {"Model": "D12A", "Pitch (mm)": 790},
    {"Model": "Y4L", "Pitch (mm)": 790},
    {"Model": "F44", "Pitch (mm)": 660},
    {"Model": "F48", "Pitch (mm)": 660},
    {"Model": "P42QR", "Pitch (mm)": 760},
    {"Model": "SU2", "Pitch (mm)": 660},
    {"Model": "DNGA", "Pitch (mm)": 610}
])

ZONE_COLORS = {
    "Dryer": "#FFD700", "Debinder": "#FFA500", "Heating": "#FF4500",
    "Cooling": "#87CEFA", "Flux": "#9370DB", "Xfer": "#D3D3D3", "Exit": "#A9A9A9"
}

IMAGE_MAPPING = {
    "NB1": "Screenshot 2026-10-20 143941.png",
    "NB2": "Screenshot 2026-10-20 144037.png",
    "NB3": "Screenshot 2026-10-20 144101.png"
}

def get_pitch_for_model(description):
    """ค้นหา Pitch จากชื่อโมเดล ถ้าไม่เจอใช้ค่า 660mm เป็นค่าปริยาย"""
    desc_str = str(description).upper()
    for _, row in MODEL_DB.iterrows():
        kw = str(row['Model']).upper()
        if kw in desc_str:
            return row['Pitch (mm)'] / 1000.0
    return 0.660 # Default

# ==============================================================================
# 3. ส่วนของหน้าจอ Streamlit (UI)
# ==============================================================================
st.set_page_config(page_title="Furnace Product Simulation", page_icon="🔥", layout="wide")

current_nb = "NB3" # ค่าเริ่มต้นในกรณีที่ไม่มีการอัปโหลด

# ------------------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 1. อัปโหลดไฟล์ข้อมูล Datapaq (.PAQ) (ถ้ามี)")
    uploaded_file = st.file_uploader("📂 ลากไฟล์ .PAQ มาวางที่นี่", type=["paq"])

    if uploaded_file is not None:
        filename = uploaded_file.name
        current_nb = identify_furnace_type(filename)
        st.success(f"✅ อัปโหลดไฟล์สำเร็จ:\n`{filename}`")
        st.info(f"📍 ระบบตรวจพบเตา: **{current_nb}** อัตโนมัติ")
    else:
        st.info("💡 สามารถอัปโหลด .PAQ เพื่อระบุเตาอัตโนมัติ หรือเลือกเตาเองด้านล่าง")
        current_nb = st.selectbox("🔥 เลือกเตา (Manual):", ["NB1", "NB2", "NB3"], index=2)

# ------------------------------------------------------------------------------
# Main Page
# ------------------------------------------------------------------------------
st.title("🔥 Furnace Product & Simulation")
st.markdown("ระบบจำลองตำแหน่งชิ้นงานในเตาอบประสาน (Brazing Furnace) โดยอ้างอิงจากแผนการโหลดชิ้นงานจริง")

# ==============================================================================
# อัปโหลด Excel ทำงานได้เลย ไม่ต้องรอ current_nb (เพราะตอนนี้มีค่าตั้งต้นเสมอ)
# ==============================================================================
st.markdown("### 📥 2. อัปโหลดแผนการผลิต (Excel)")
uploaded_excels = st.file_uploader(
    f"อัปโหลดไฟล์ข้อมูลแผนการผลิตของเตา {current_nb} (.xlsx หรือ .xls สามารถเลือกหลายไฟล์พร้อมกันได้)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

df_pieces = pd.DataFrame()

if uploaded_excels:
    st.success(f"✅ อัปโหลดไฟล์ Excel สำเร็จจำนวน {len(uploaded_excels)} ไฟล์")
    
    # 1. อ่านข้อมูล Excel ทั้งหมดมารวมกัน
    dfs = []
    for file in uploaded_excels:
        try:
            df_temp = pd.read_excel(file)
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ {file.name} ได้: {e}")
            
    if dfs:
        df_schedule = pd.concat(dfs, ignore_index=True)
        # กรองเฉพาะแถวที่มีข้อมูลที่ต้องการ
        if 'Start Time' in df_schedule.columns and 'End Time' in df_schedule.columns and 'Quantity' in df_schedule.columns:
            df_schedule = df_schedule.dropna(subset=['Start Time', 'End Time', 'Quantity'])
            
            # --- จัดให้คอลัมน์ Description อยู่ซ้ายสุดตอนโชว์พรีวิว ---
            if 'Description' in df_schedule.columns:
                cols = df_schedule.columns.tolist()
                cols.insert(0, cols.pop(cols.index('Description')))
                df_schedule_view = df_schedule[cols]
            else:
                df_schedule_view = df_schedule

            with st.expander("ดูข้อมูลแผนการผลิต (Data Preview)"):
                st.dataframe(df_schedule_view, use_container_width=True)
                
            # 2. กระจายข้อมูลชิ้นงานแต่ละชิ้น
            pieces_list = []
            for _, row in df_schedule.iterrows():
                qty = int(row['Quantity'])
                if qty <= 0: continue
                
                start_t = pd.to_datetime(row['Start Time'])
                end_t = pd.to_datetime(row['End Time'])
                desc = str(row.get('Description', 'Unknown Model'))
                
                pitch_m = get_pitch_for_model(desc)
                
                # หาความเร็วสายพาน
                total_seconds = (end_t - start_t).total_seconds()
                if qty > 1 and total_seconds > 0:
                    interval_s = total_seconds / qty
                    speed_ms = pitch_m / interval_s
                else:
                    interval_s = 0
                    speed_ms = 1.5 / 60.0 
                    
                for i in range(qty):
                    load_t = start_t + pd.Timedelta(seconds=i * interval_s)
                    pieces_list.append({
                        'Model': desc,
                        'LoadTime': load_t,
                        'Pitch_m': pitch_m,
                        'Speed_ms': speed_ms
                    })
            
            df_pieces = pd.DataFrame(pieces_list)
            if not df_pieces.empty:
                df_pieces = df_pieces.sort_values('LoadTime').reset_index(drop=True)
        else:
            st.error("❌ ไฟล์ Excel ไม่มีคอลัมน์ 'Start Time', 'End Time' หรือ 'Quantity' ตามฟอร์แมตที่ต้องการ")

st.markdown("---")

# ==============================================================================
# กราฟจำลอง Simulation
# ==============================================================================

# คำนวณความยาวสะสมของแต่ละ Zone ของเตาที่ตรวจจับได้
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

# สร้างแกนกราฟ
fig = go.Figure()

# 1. วาดแถบของแต่ละ Zone
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

# 2. วาดเส้นแกนสายพาน
fig.add_shape(
    type="line", x0=0, x1=total_furnace_length, y0=1.2, y1=1.2,
    line=dict(color="gray", width=2, dash="dot"), layer="below"
)

# ------------------------------------------------------------------------------
# หากมีการอัปโหลด Excel และคำนวณชิ้นงานได้
# ------------------------------------------------------------------------------
sim_time = None
df_current = pd.DataFrame()

if not df_pieces.empty:
    
    # จัดการ Slider ให้อยู่ด้านล่างกราฟเดี๋ยวค่อยแสดง
    min_time = df_pieces['LoadTime'].min()
    max_time = df_pieces['LoadTime'].max() + pd.Timedelta(minutes=90) 
    
    # เก็บค่า sim_time ไว้ก่อน เพื่อใช้วาดกราฟ (แต่ตัว Slider UI จะถูกวาดทีหลัง)
    if 'sim_time_state' not in st.session_state:
        st.session_state.sim_time_state = min_time.to_pydatetime()
        
    # คำนวณระยะทางของชิ้นงานทุกชิ้น ณ วินาที sim_time (จาก state)
    current_sim = st.session_state.sim_time_state
    df_pieces['Elapsed_s'] = (pd.to_datetime(current_sim) - df_pieces['LoadTime']).dt.total_seconds()
    df_pieces['Position'] = df_pieces['Elapsed_s'] * df_pieces['Speed_ms']
    
    # กรองเฉพาะชิ้นงานที่กำลังอยู่ในเตา 
    df_current = df_pieces[(df_pieces['Position'] >= 0) & (df_pieces['Position'] <= total_furnace_length)]
    
    # วาดชิ้นงานลงในกราฟ โดยแยกสีตาม Model
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

# ------------------------------------------------------------------------------
# หากยังไม่ได้อัปโหลด Excel ให้โชว์แบบ Static เป็นตัวอย่างแทน
# ------------------------------------------------------------------------------
else:
    st.info("💡 **ข้อมูลการโหลดชิ้นงานยังว่างเปล่า** (ด้านล่างคือภาพตัวอย่าง) อัปโหลดไฟล์ Excel เพื่อดูตำแหน่งจริงและเวลาที่สัมพันธ์กัน")
    selected_model = st.selectbox("เลือกโมเดลเพื่อดูตัวอย่าง (Sample Model):", MODEL_DB["Model"].tolist())
    
    pitch_mm = MODEL_DB.loc[MODEL_DB["Model"] == selected_model, "Pitch (mm)"].values[0]
    pitch_m = pitch_mm / 1000.0
    
    product_positions = np.arange(0, total_furnace_length, pitch_m)
    fig.add_trace(go.Scatter(
        x=product_positions, y=[1.2] * len(product_positions),
        mode="markers", name=f"ตัวอย่าง {selected_model}",
        marker=dict(symbol="square", size=12, color="#32CD32", line=dict(width=2, color="black")),
        hovertemplate="ตำแหน่ง: %{x:.2f} เมตร<extra></extra>"
    ))

# ------------------------------------------------------------------------------
# นำภาพ Layout เตาขึ้นไปวางด้านบนโครงสร้าง
# ------------------------------------------------------------------------------
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

# ตั้งค่ากราฟ
fig.update_layout(
    title=f"Furnace Timeline: {current_nb} (Total Length: {total_furnace_length:.2f} m)",
    xaxis=dict(title="Distance (Meters)", range=[0, total_furnace_length], tickmode="linear", tick0=0, dtick=2),
    yaxis=dict(visible=False, range=y_range),
    height=450, margin=dict(l=20, r=20, t=50, b=40),
    template="plotly_white", hovermode="x unified",
    showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# 1. โชว์กราฟก่อน
st.plotly_chart(fig, use_container_width=True)

# 2. โชว์ Time Slider (ย้ายมาไว้ด้านล่างกราฟตามที่ขอ)
if not df_pieces.empty:
    st.markdown("---")
    # ใช้ session_state เพื่อให้ Slider รีเฟรชหน้าจอเมื่อลากเสร็จ
    def update_sim_time():
        st.session_state.sim_time_state = st.session_state.sim_time_slider
        
    sim_time = st.slider(
        "⏱️ ลากเพื่อเลื่อนดูเวลาจำลอง (Slide to Simulator Time):", 
        min_value=min_time.to_pydatetime(), 
        max_value=max_time.to_pydatetime(), 
        value=st.session_state.sim_time_state, 
        step=timedelta(minutes=1),
        format="YYYY-MM-DD HH:mm",
        key="sim_time_slider",
        on_change=update_sim_time
    )
    
    # 3. โชว์ตารางสรุป
    st.markdown(f"### 📋 สรุปจำนวนชิ้นงานในเตา ณ เวลา **{st.session_state.sim_time_state.strftime('%Y-%m-%d %H:%M')}**")
    if not df_current.empty:
        bins = [0] + df_zones["End"].tolist()
        labels = df_zones["Name"].tolist()
        df_current['Zone'] = pd.cut(df_current['Position'], bins=bins, labels=labels, right=True)
        
        wip_summary = df_current.groupby(['Zone', 'Model']).size().reset_index(name='Quantity')
        wip_summary = wip_summary[wip_summary['Quantity'] > 0]
        
        wip_pivot = wip_summary.pivot(index='Model', columns='Zone', values='Quantity').fillna(0).astype(int)
        st.dataframe(wip_pivot, use_container_width=True)
    else:
        st.info("ไม่มีชิ้นงานอยู่ในเตา ณ เวลาที่เลือก")
