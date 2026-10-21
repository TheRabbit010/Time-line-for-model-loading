import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import re
from PIL import Image
import os
from datetime import timedelta

# (ฟังก์ชัน identify_furnace_type, FURNACE_ZONE_DATA, MODEL_DB, ZONE_COLORS, IMAGE_MAPPING, get_pitch_for_model คงเดิมตามด้านบน)

# ... [ใส่ส่วน Setup เตา และ Sidebar เดิมที่นี่] ...

with st.sidebar:
    st.markdown("### ⚙️ ตั้งค่าพารามิเตอร์เตา")
    # เพิ่มตัวเลือกให้กำหนดความเร็วสายพาน (เมตร/นาที)
    belt_speed_m_min = st.number_input("ความเร็วสายพาน (เมตร/นาที)", min_value=0.1, max_value=5.0, value=1.5, step=0.1)
    belt_speed_ms = belt_speed_m_min / 60.0  # แปลงเป็น เมตร/วินาที

# ==============================================================================
# อัปโหลด Excel และประมวลผลตำแหน่งตามสูตร: เวลาโหลด = Start Time + (ลำดับชิ้น * (Pitch / Speed))
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
    
    dfs = []
    for file in uploaded_excels:
        try:
            df_temp = pd.read_excel(file)
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ {file.name} ได้: {e}")
            
    if dfs:
        df_schedule = pd.concat(dfs, ignore_index=True)
        
        # ตรวจสอบว่ามีคอลัมน์ที่จำเป็นตามไฟล์ภาพ
        required_cols = ['Description', 'Quantity', 'Start Time']
        if all(col in df_schedule.columns for col in required_cols):
            # กรองข้อมูลเอาเฉพาะแถวที่มีจำนวนมากกว่า 0 และมีเวลาเริ่ม
            df_schedule = df_schedule.dropna(subset=['Start Time', 'Quantity'])
            df_schedule = df_schedule[df_schedule['Quantity'] > 0]
            
            with st.expander("ดูข้อมูลแผนการผลิต (Data Preview)"):
                st.dataframe(df_schedule[required_cols], use_container_width=True)
                
            # 2. กระจายข้อมูลชิ้นงานแต่ละชิ้นตามความเร็วและระยะแก๊ป (Pitch)
            pieces_list = []
            for _, row in df_schedule.iterrows():
                qty = int(row['Quantity'])
                start_t = pd.to_datetime(row['Start Time'])
                desc = str(row['Description'])
                
                # ดึงระยะห่าง (Pitch) ของรุ่นนั้นๆ
                pitch_m = get_pitch_for_model(desc)
                
                # คำนวณช่วงเวลาที่ต้องรอระหว่างชิ้น (วินาที) = ระยะห่าง / ความเร็ว
                interval_s = pitch_m / belt_speed_ms
                
                # จำลองการโหลดชิ้นงานทีละชิ้นตามเวลา
                for i in range(qty):
                    # ชิ้นแรกเริ่มที่ Start Time ชิ้นต่อไปบวกเวลา Interval เข้าไป
                    load_t = start_t + pd.Timedelta(seconds=i * interval_s)
                    pieces_list.append({
                        'Model': desc,
                        'LoadTime': load_t,
                        'Pitch_m': pitch_m,
                        'Speed_ms': belt_speed_ms
                    })
            
            df_pieces = pd.DataFrame(pieces_list)
            if not df_pieces.empty:
                df_pieces = df_pieces.sort_values('LoadTime').reset_index(drop=True)
        else:
            st.error(f"❌ ไฟล์ Excel ต้องมีคอลัมน์ต่อไปนี้: {', '.join(required_cols)}")

st.markdown("---")

# ... [ส่วนการวาดกราฟ เตา และโซนต่างๆ คงเดิม] ...

# ------------------------------------------------------------------------------
# ส่วนจัดการ Slider และการคำนวณตำแหน่ง ณ เวลาที่เลือก
# ------------------------------------------------------------------------------
if not df_pieces.empty:
    min_time = df_pieces['LoadTime'].min()
    max_time = df_pieces['LoadTime'].max() + pd.Timedelta(minutes=90) 
    
    if 'sim_time_state' not in st.session_state:
        st.session_state.sim_time_state = min_time.to_pydatetime()
        
    current_sim = st.session_state.sim_time_state
    
    # คำนวณระยะทาง = เวลาที่ผ่านไป (วินาที) * ความเร็ว (เมตร/วินาที)
    df_pieces['Elapsed_s'] = (pd.to_datetime(current_sim) - df_pieces['LoadTime']).dt.total_seconds()
    df_pieces['Position'] = df_pieces['Elapsed_s'] * df_pieces['Speed_ms']
    
    # กรองเฉพาะชิ้นงานที่กำลังอยู่ในเตา (ตำแหน่ง >= 0 และไม่เกินความยาวเตา)
    df_current = df_pieces[(df_pieces['Position'] >= 0) & (df_pieces['Position'] <= total_furnace_length)]
    
    # ... [นำ df_current ไปวาดจุด (Scatter) ในกราฟตามโค้ดเดิม] ...

# ------------------------------------------------------------------------------
# แสดง Slider ด้านล่าง
# ------------------------------------------------------------------------------
if not df_pieces.empty:
    st.markdown("---")
    def update_sim_time():
        st.session_state.sim_time_state = st.session_state.sim_time_slider
        
    sim_time = st.slider(
        "⏱️ ลากเพื่อเลื่อนดูเวลาจำลอง (Slide to Simulator Time):", 
        min_value=min_time.to_pydatetime(), 
        max_value=max_time.to_pydatetime(), 
        value=st.session_state.sim_time_state, 
        step=timedelta(minutes=1),  # เลื่อนทีละ 1 นาทีเป็น Step
        format="YYYY-MM-DD HH:mm",
        key="sim_time_slider",
        on_change=update_sim_time
    )
