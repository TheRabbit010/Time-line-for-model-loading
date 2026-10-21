# ==============================================================================
# 6. อัปโหลดและเตรียมข้อมูล Excel
# ==============================================================================
st.markdown("### 📥 2. อัปโหลดแผนการผลิต (Excel)")

# จัดการ Session State สำหรับรีเซ็ตกล่อง File Uploader
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = str(datetime.now().timestamp())

col_up1, col_up2 = st.columns([4, 1])
with col_up1:
    uploaded_excels = st.file_uploader(
        "อัปโหลดไฟล์ข้อมูลแผนการผลิตของเตา (.xlsx หรือ .xls สามารถเลือกหลายไฟล์พร้อมกันได้)", 
        type=["xlsx", "xls"], 
        accept_multiple_files=True,
        key=st.session_state["file_uploader_key"] # ผูก key กับ session_state
    )

with col_up2:
    st.write("") # เว้นบรรทัดให้ตรงกับกล่องอัปโหลด
    st.write("")
    # ปุ่ม Reset/Clear data
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
        # เมื่อตรวจจับ NB ได้ (จากฟังก์ชันที่เราปรับปรุงใหม่) 
        # ระบบจะนำ current_nb_detected_excel ไปกำหนดค่า current_nb อัตโนมัติในส่วนที่ 7 ถัดไป
        current_nb_detected_excel = detect_furnace_from_dataframe(df_schedule_raw)

st.markdown("---")
