import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
import requests
import io
import time
import re
import tempfile
import os
from typing import Optional, Dict, Any

# Kiểm tra phiên bản Streamlit
st.set_page_config(
    page_title="Tự động hóa báo cáo tài chính",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .report-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Tiêu đề
st.title("📊 Hệ thống tự động hóa báo cáo tài chính")
st.caption("Hỗ trợ Yahoo Finance, PDF, CSV, Excel | Tương thích Python 3.13")

# Khởi tạo session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.data_source = "Yahoo Finance"
    st.session_state.ticker = "AAPL"
    st.session_state.yf_data = None
    st.session_state.pdf_data = None
    st.session_state.df_upload = None
    st.session_state.loading = False
    st.session_state.last_update = None

# Sidebar
with st.sidebar:
    st.header("🔧 Cấu hình")
    
    # Chọn nguồn dữ liệu
    data_source = st.radio(
        "📁 **Chọn nguồn dữ liệu**",
        options=["Yahoo Finance", "Upload PDF", "Upload CSV/Excel"],
        index=0,
        key="data_source_radio",
        help="Chọn nguồn dữ liệu bạn muốn sử dụng"
    )
    
    st.divider()
    
    # Xử lý theo từng nguồn
    if data_source == "Yahoo Finance":
        st.subheader("📈 Cấu hình Yahoo Finance")
        
        # Nhập mã cổ phiếu
        ticker = st.text_input(
            "Mã cổ phiếu",
            value=st.session_state.ticker,
            help="VD: AAPL, VNM, FPT, MSN, VIC",
            key="ticker_input"
        ).upper().strip()
        
        st.session_state.ticker = ticker
        
        # Chọn kỳ báo cáo
        period = st.selectbox(
            "Kỳ báo cáo",
            options=["1 năm", "3 năm", "5 năm", "10 năm"],
            index=1,
            key="period_select"
        )
        
        years_map = {"1 năm": 1, "3 năm": 3, "5 năm": 5, "10 năm": 10}
        years = years_map[period]
        
        # Nút refresh
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Lấy dữ liệu", use_container_width=True, type="primary"):
                st.session_state.loading = True
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            if st.button("🗑️ Xóa cache", use_container_width=True):
                st.cache_data.clear()
                st.session_state.yf_data = None
                st.success("✅ Đã xóa cache")
                time.sleep(1)
                st.rerun()
    
    elif data_source == "Upload PDF":
        st.subheader("📄 Upload file PDF")
        
        uploaded_pdf = st.file_uploader(
            "Chọn file PDF",
            type=['pdf'],
            accept_multiple_files=False,
            help="Chọn báo cáo tài chính dạng PDF"
        )
        
        if uploaded_pdf:
            st.session_state.uploaded_pdf = uploaded_pdf
            
            if st.button("📄 Xử lý PDF", use_container_width=True, type="primary"):
                st.session_state.loading = True
                st.rerun()
    
    else:  # Upload CSV/Excel
        st.subheader("📊 Upload file dữ liệu")
        
        uploaded_file = st.file_uploader(
            "Chọn file CSV hoặc Excel",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=False,
            help="File cần có định dạng bảng rõ ràng"
        )
        
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            
            if st.button("📊 Đọc dữ liệu", use_container_width=True, type="primary"):
                st.session_state.loading = True
                st.rerun()
    
    st.divider()
    
    # Thông tin hệ thống
    with st.expander("ℹ️ Thông tin"):
        st.write(f"**Python:** 3.13")
        st.write(f"**Streamlit:** 1.54.0")
        if st.session_state.last_update:
            st.write(f"**Cập nhật:** {st.session_state.last_update}")

# --- CÁC HÀM XỬ LÝ DỮ LIỆU ---

@st.cache_data(ttl=1800, show_spinner="🔄 Đang kết nối Yahoo Finance...")
def fetch_yahoo_finance(ticker: str, years: int) -> Dict[str, Any]:
    """Lấy dữ liệu từ Yahoo Finance với cache"""
    
    if not ticker:
        return {"success": False, "error": "Mã cổ phiếu trống"}
    
    try:
        # Thêm delay để tránh rate limit
        time.sleep(1.5)
        
        # Tạo đối tượng Ticker
        stock = yf.Ticker(ticker)
        
        # Lấy thông tin cơ bản
        info = {}
        for attempt in range(3):
            try:
                info = stock.info
                if info and len(info) > 5:
                    break
            except:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                continue
        
        # Lấy lịch sử giá
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)
        hist = stock.history(start=start_date, end=end_date)
        
        # Lấy báo cáo tài chính
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        # Thử lấy quarterly nếu annual không có
        if financials is None or financials.empty:
            financials = stock.quarterly_financials
        if balance_sheet is None or balance_sheet.empty:
            balance_sheet = stock.quarterly_balance_sheet
        if cashflow is None or cashflow.empty:
            cashflow = stock.quarterly_cashflow
        
        return {
            "success": True,
            "ticker": ticker,
            "info": info,
            "history": hist,
            "financials": financials,
            "balance_sheet": balance_sheet,
            "cashflow": cashflow,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        error_msg = str(e)
        if "Too Many Requests" in error_msg or "rate limit" in error_msg.lower():
            return {"success": False, "error": "rate_limit", "ticker": ticker}
        else:
            return {"success": False, "error": error_msg, "ticker": ticker}

@st.cache_data(ttl=3600)
def extract_pdf_data(pdf_file) -> Optional[pd.DataFrame]:
    """Trích xuất dữ liệu từ PDF"""
    
    if pdf_file is None:
        return None
    
    try:
        # Tạo file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name
        
        all_tables = []
        
        # Đọc PDF
        try:
            import pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Lấy text
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        financial_lines = []
                        
                        # Tìm dòng có số liệu tài chính
                        keywords = ['doanh thu', 'lợi nhuận', 'chi phí', 'tài sản',
                                  'nợ', 'vốn', 'revenue', 'profit', 'asset']
                        
                        for line in lines:
                            if any(k in line.lower() for k in keywords):
                                if re.search(r'\d+[.,]\d+', line):
                                    financial_lines.append(line)
                        
                        if financial_lines:
                            all_tables.extend(financial_lines)
                    
                    # Lấy bảng
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df = df.replace('', pd.NA).dropna(how='all')
                            if not df.empty and len(df.columns) >= 2:
                                all_tables.append(df)
        except:
            pass
        
        # Dọn dẹp
        os.unlink(tmp_path)
        
        if all_tables:
            return all_tables
        else:
            return None
            
    except Exception as e:
        st.error(f"Lỗi xử lý PDF: {str(e)}")
        return None

def format_number(value):
    """Định dạng số đẹp"""
    try:
        if pd.isna(value) or value == 'N/A':
            return 'N/A'
        num = float(value)
        if abs(num) >= 1e9:
            return f"{num/1e9:.2f}B"
        elif abs(num) >= 1e6:
            return f"{num/1e6:.2f}M"
        elif abs(num) >= 1e3:
            return f"{num/1e3:.2f}K"
        else:
            return f"{num:,.0f}"
    except:
        return str(value)

# --- MAIN APP ---

# Xử lý loading state
if st.session_state.get('loading', False):
    with st.spinner("🔄 Đang xử lý dữ liệu..."):
        time.sleep(1)
        
        # Xử lý theo nguồn
        if data_source == "Yahoo Finance":
            ticker = st.session_state.ticker
            if ticker:
                st.session_state.yf_data = fetch_yahoo_finance(ticker, years)
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
        
        elif data_source == "Upload PDF":
            if 'uploaded_pdf' in st.session_state:
                st.session_state.pdf_data = extract_pdf_data(st.session_state.uploaded_pdf)
        
        else:  # Upload CSV/Excel
            if 'uploaded_file' in st.session_state:
                try:
                    file = st.session_state.uploaded_file
                    if file.name.endswith('.csv'):
                        st.session_state.df_upload = pd.read_csv(file)
                    else:
                        st.session_state.df_upload = pd.read_excel(file)
                except Exception as e:
                    st.error(f"Lỗi đọc file: {str(e)}")
        
        st.session_state.loading = False
        st.rerun()

# HIỂN THỊ KẾT QUẢ
st.divider()

# Case 1: Yahoo Finance
if data_source == "Yahoo Finance":
    if st.session_state.yf_data:
        data = st.session_state.yf_data
        
        if data.get('success'):
            ticker = data['ticker']
            info = data.get('info', {})
            
            # Hiển thị thông tin công ty
            company_name = info.get('longName', ticker)
            st.subheader(f"🏢 {company_name}")
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                market_cap = info.get('marketCap', 0)
                st.metric("Vốn hóa", format_number(market_cap))
            with col2:
                pe = info.get('trailingPE', 'N/A')
                st.metric("P/E", f"{pe:.2f}" if isinstance(pe, (int, float)) else pe)
            with col3:
                roe = info.get('returnOnEquity', 0)
                st.metric("ROE", f"{roe*100:.1f}%" if roe else 'N/A')
            with col4:
                profit_margin = info.get('profitMargins', 0)
                st.metric("Biên LN", f"{profit_margin*100:.1f}%" if profit_margin else 'N/A')
            
            # Tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 KQKD", "💰 Dòng tiền", "📊 CĐKT", "📉 Lịch sử giá"
            ])
            
            with tab1:
                financials = data.get('financials')
                if financials is not None and not financials.empty:
                    st.dataframe(financials.head(10), use_container_width=True)
                else:
                    st.info("Không có dữ liệu báo cáo KQKD")
            
            with tab2:
                cashflow = data.get('cashflow')
                if cashflow is not None and not cashflow.empty:
                    st.dataframe(cashflow.head(10), use_container_width=True)
                else:
                    st.info("Không có dữ liệu báo cáo dòng tiền")
            
            with tab3:
                balance = data.get('balance_sheet')
                if balance is not None and not balance.empty:
                    st.dataframe(balance.head(10), use_container_width=True)
                else:
                    st.info("Không có dữ liệu bảng CĐKT")
            
            with tab4:
                history = data.get('history')
                if history is not None and not history.empty:
                    fig = px.line(history, y='Close', title=f'Giá đóng cửa {ticker}')
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("Xem dữ liệu chi tiết"):
                        st.dataframe(history.tail(20), use_container_width=True)
                else:
                    st.info("Không có dữ liệu lịch sử giá")
        
        else:
            error = data.get('error', '')
            if error == 'rate_limit':
                st.error("⚠️ **Yahoo Finance đang giới hạn truy cập**")
                st.info("""
                **Giải pháp:**
                1. Đợi 2-3 phút và thử lại
                2. Dùng nút "Xóa cache" để refresh
                3. Chuyển sang upload file PDF/Excel
                """)
            else:
                st.error(f"❌ Lỗi: {error}")
    
    else:
        st.info("👈 Nhập mã cổ phiếu và nhấn 'Lấy dữ liệu' để bắt đầu")
        
        # Hiển thị ví dụ
        with st.expander("📘 Mã cổ phiếu phổ biến"):
            st.markdown("""
            - **VN**: VNM, FPT, MSN, HPG, VIC, VCB, BID
            - **US**: AAPL, MSFT, GOOGL, AMZN, TSLA
            - **World**: BABA, TSM, SONY, NESN.SW
            """)

# Case 2: PDF
elif data_source == "Upload PDF":
    if st.session_state.pdf_data:
        st.subheader("📄 Dữ liệu từ PDF")
        
        pdf_data = st.session_state.pdf_data
        
        for i, item in enumerate(pdf_data):
            if isinstance(item, pd.DataFrame):
                with st.expander(f"📊 Bảng {i+1}"):
                    st.dataframe(item, use_container_width=True)
            elif isinstance(item, str):
                with st.expander(f"📝 Dòng {i+1}"):
                    st.write(item)
            else:
                with st.expander(f"📄 Mục {i+1}"):
                    st.write(item)
    else:
        st.info("👈 Upload file PDF và nhấn 'Xử lý PDF' để bắt đầu")

# Case 3: CSV/Excel
elif data_source == "Upload CSV/Excel":
    if st.session_state.df_upload is not None:
        st.subheader("📊 Dữ liệu từ file")
        
        df = st.session_state.df_upload
        
        # Hiển thị thông tin
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Số dòng", len(df))
        with col2:
            st.metric("Số cột", len(df.columns))
        with col3:
            st.metric("Kiểu file", "CSV" if df is not None else "Excel")
        
        # Hiển thị dữ liệu
        st.dataframe(df, use_container_width=True)
        
        # Thống kê
        if st.checkbox("Hiển thị thống kê"):
            st.dataframe(df.describe(), use_container_width=True)
    else:
        st.info("👈 Upload file và nhấn 'Đọc dữ liệu' để bắt đầu")

# Footer
st.divider()
st.caption("© 2025 - Hệ thống tự động hóa báo cáo tài chính | Python 3.13 | Streamlit 1.54.0")
