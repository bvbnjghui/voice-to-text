import streamlit as st
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
import os
import time

# --- 1. 頁面配置 ---
st.set_page_config(
    page_title="AI 逐字稿專家 Pro", 
    page_icon="🎙️", 
    layout="wide"
)

# --- 2. 模型設定對照表 ---
MODEL_REPO_MAP = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3"
}

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    model_option = st.selectbox("選擇模型:", list(MODEL_REPO_MAP.keys()), index=3)
    
    st.info("**實測建議**：\n- **Medium**: 準確度與速度最平衡，推薦日常使用。\n- **Large-v3**: 適合音質較差或需要極高精度的場合。")
    
    device_option = st.radio("運算設備:", ("cpu", "cuda"), index=0)
    compute_option = st.selectbox("計算精度:", ("int8", "float16"), index=0)
    
    st.divider()
    if st.button("🧹 重置系統 (清除快取)"):
        st.cache_resource.clear()
        st.rerun()

# --- 4. 核心功能：模型加載 (UI與邏輯分離避免轉圈圈) ---
@st.cache_resource(show_spinner=False)
def get_model_resource(model_name, device, compute_type):
    repo_id = MODEL_REPO_MAP[model_name]
    
    # --- 新增：強制將模型存放在專案資料夾下的 models 目錄 ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_model_path = os.path.join(base_dir, "models", model_name)
    
    # 下載模型到指定路徑
    snapshot_download(repo_id, local_dir=local_model_path)
    
    # 載入時使用該路徑
    return WhisperModel(local_model_path, device=device, compute_type=compute_type)

try:
    with st.status(f"⚙️ 系統準備中: {model_option}", expanded=False) as load_status:
        model = get_model_resource(model_option, device_option, compute_option)
        load_status.update(label=f"🟢 系統就緒: {model_option}", state="complete")
except Exception as e:
    st.error(f"模型啟動失敗: {e}")
    st.stop()

# --- 5. 主介面設計 ---
st.title("🎙️ AI 語音轉文字生產力工具")

uploaded_file = st.file_uploader("1. 上傳錄音檔", type=["mp3", "wav", "m4a"])

if uploaded_file:
    st.audio(uploaded_file)
    st.markdown("---")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        audio_topic = st.text_input("📍 錄音主題", placeholder="例如：專案週報、讀書筆記")
    with col_b:
        user_prompt = st.text_area(
            "📝 進階提示詞", 
            value="這是一段繁體中文音訊。請使用台灣繁體慣用語，並正確標註標點符號。",
            height=100
        )

    final_prompt = f"主題：{audio_topic}。{user_prompt}" if audio_topic else user_prompt

    # 操作按鈕
    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
    with btn_col1:
        start_btn = st.button("🚀 開始辨識", use_container_width=True, type="primary")
    with btn_col2:
        stop_btn = st.button("🛑 中止/重置", use_container_width=True)

    if stop_btn:
        st.warning("已中斷目前作業。")
        st.stop()

    if start_btn:
        temp_path = f"temp_{int(time.time())}.wav"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        prog_bar = st.progress(0, text="AI 正在聽取中...")
        result_area = st.empty()
        
        try:
            start_time = time.time()
            full_text = ""
            
            segments, info = model.transcribe(
                temp_path,
                beam_size=5,
                language="zh",
                initial_prompt=final_prompt,
                vad_filter=True
            )

            # 辨識過程
            for segment in segments:
                timestamp = f"[{segment.start:05.2f}s -> {segment.end:05.2f}s]"
                new_line = f"{timestamp} {segment.text}\n"
                full_text += new_line
                
                # 實時更新展示區 (text_area 適合滾動查看)
                result_area.text_area("即時辨識中...", value=full_text, height=400)
                
                # 更新進度
                prog = min(segment.end / info.duration, 1.0)
                prog_bar.progress(prog, text=f"辨識進度: {int(prog*100)}% (目前位置: {segment.end:.1f}秒)")

            # --- 修正 1：迴圈結束強迫推到 100% ---
            prog_bar.progress(1.0, text="✅ 辨識完成！100%")
            duration = time.time() - start_time
            st.success(f"🎊 辨識完成！總時長 {info.duration:.1f} 秒，耗時 {duration:.1f} 秒。")
            
            # --- 修正 2：改用 st.code 解決複製按鈕消失問題 ---
            st.markdown("### 📋 最終逐字稿紀錄 (點擊右側按鈕快速複製)")
            st.code(full_text, language="text", wrap_lines=True)
            
            # --- 6. 結果匯出 ---
            st.markdown("### 📤 匯出轉換結果")
            md_content = f"# 語音辨識紀錄\n**主題**：{audio_topic if audio_topic else '未設定'}\n**日期**：{time.strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{full_text}"
            
            export_col1, export_col2, _ = st.columns([1, 1, 2])
            with export_col1:
                st.download_button("💾 下載純文字 (.txt)", full_text, file_name=f"transcript.txt", use_container_width=True)
            with export_col2:
                st.download_button("📝 下載 Markdown (.md)", md_content, file_name=f"transcript.md", use_container_width=True)
                
        except Exception as e:
            st.error(f"錯誤：{e}")
        finally:
            if os.path.exists(temp_path): os.remove(temp_path)
else:
    st.info("👋 歡迎使用！請上傳音訊檔案開始作業。")