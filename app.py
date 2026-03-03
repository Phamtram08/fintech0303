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
from typing import Optional, Dict, Any, List

# Kiểm tra thư viện PDF
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# Cấu hình trang
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
    .success-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 10px 0;
    }
    .warning-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
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
    st.session_state.uploaded_pdf = None
    st.session_state.uploaded_file = None
    st.session_state.pdf_processed = False

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
        
        # Kiểm tra thư viện PDF
        if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
            st.error("⚠️ Thiếu thư viện đọc PDF. Vui lòng cài đặt:")
            st.code("pip install pdfplumber PyPDF2")
        
        uploaded_pdf = st.file_uploader(
            "Chọn file PDF",
            type=['pdf'],
            accept_multiple_files=False,
            help="Chọn báo cáo tài chính dạng PDF (tối đa 200MB)"
        )
        
        if uploaded_pdf:
            st.session_state.uploaded_pdf = uploaded_pdf
            st.info(f"📄 File: {uploaded_pdf.name} ({uploaded_pdf.size/1024/1024:.1f}MB)")
            
            if st.button("📄 Xử lý PDF", use_container_width=True, type="primary"):
                st.session_state.loading = True
                st.session_state.pdf_processed = False
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
        st.write(f"**pdfplumber:** {'✅' if PDFPLUMBER_AVAILABLE else '❌'}")
        st.write(f"**PyPDF2:** {'✅' if PYPDF2_AVAILABLE else '❌'}")
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

@st.cache_data(ttl=3600, show_spinner="🔄 Đang xử lý file PDF...")
def extract_pdf_data(pdf_file) -> Optional[Dict]:
    """Trích xuất dữ liệu từ PDF và trả về dạng có cấu trúc"""
    
    if pdf_file is None:
        return None
    
    result = {
        'success': False,
        'pages': [],
        'tables': [],
        'text': [],
        'financial_data': [],
        'error': None,
        'filename': pdf_file.name if pdf_file else 'unknown.pdf'
    }
    
    try:
        # Tạo file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name
        
        st.info(f"📄 Đang xử lý file: {pdf_file.name}")
        
        # Thử đọc bằng pdfplumber trước
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(tmp_path) as pdf:
                    result['total_pages'] = len(pdf.pages)
                    
                    for page_num, page in enumerate(pdf.pages):
                        page_data = {
                            'page_num': page_num + 1,
                            'text': page.extract_text() or '',
                            'tables': []
                        }
                        
                        # Lấy text
                        if page_data['text']:
                            result['text'].append(page_data['text'])
                            
                            # Tìm dòng có số liệu tài chính
                            lines = page_data['text'].split('\n')
                            for line in lines:
                                if re.search(r'\d+[.,]\d+', line):
                                    if any(k in line.lower() for k in ['doanh', 'lợi', 'chi', 'thu', 'năm', 'quý', 'revenue', 'profit', 'expense']):
                                        result['financial_data'].append({
                                            'page': page_num + 1,
                                            'content': line
                                        })
                        
                        # Lấy bảng
                        tables = page.extract_tables()
                        for table in tables:
                            if table and len(table) > 1:
                                try:
                                    df = pd.DataFrame(table[1:], columns=table[0])
                                    df = df.replace('', pd.NA).dropna(how='all')
                                    if not df.empty and len(df.columns) >= 2:
                                        result['tables'].append({
                                            'page': page_num + 1,
                                            'dataframe': df
                                        })
                                except:
                                    pass
                        
                        result['pages'].append(page_data)
                    
                    result['success'] = True
                    
            except Exception as e:
                result['error'] = f"pdfplumber error: {str(e)}"
        
        # Nếu pdfplumber thất bại, thử PyPDF2
        if not result['success'] and PYPDF2_AVAILABLE:
            try:
                with open(tmp_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    result['total_pages'] = len(reader.pages)
                    
                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text() or ''
                        if text:
                            result['text'].append(text)
                            
                            lines = text.split('\n')
                            for line in lines:
                                if re.search(r'\d+[.,]\d+', line):
                                    result['financial_data'].append({
                                        'page': page_num + 1,
                                        'content': line
                                    })
                    
                    result['success'] = True
                    
            except Exception as e:
                result['error'] = f"PyPDF2 error: {str(e)}"
        
        # Dọn dẹp
        os.unlink(tmp_path)
        
        # Đánh giá kết quả
        if result['success']:
            if len(result['tables']) > 0:
                result['message'] = f"✅ Tìm thấy {len(result['tables'])} bảng và {len(result['financial_data'])} dòng dữ liệu"
            elif len(result['financial_data']) > 0:
                result['message'] = f"✅ Tìm thấy {len(result['financial_data'])} dòng dữ liệu tài chính"
            elif len(result['text']) > 0:
                result['message'] = f"✅ Đọc được {len(result['text'])} trang text"
            else:
                result['message'] = "⚠️ Không tìm thấy dữ liệu trong PDF"
        else:
            result['message'] = f"❌ Lỗi: {result['error']}"
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f"❌ Lỗi xử lý PDF: {str(e)}",
            'filename': pdf_file.name if pdf_file else 'unknown.pdf'
        }

def format_number(value):
    """Định dạng số đẹp"""
    try:
        if pd.isna(value) or value == 'N/A' or value is None:
            return 'N/A'
        if isinstance(value, str):
            value = value.replace(',', '').replace(' ', '')
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
    
    # Xử lý theo nguồn
    if data_source == "Yahoo Finance":
        ticker = st.session_state.ticker
        if ticker:
            with st.spinner(f"🔄 Đang lấy dữ liệu {ticker}..."):
                st.session_state.yf_data = fetch_yahoo_finance(ticker, years)
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
    
    elif data_source == "Upload PDF":
        if st.session_state.uploaded_pdf is not None:
            with st.spinner("🔄 Đang xử lý PDF..."):
                st.session_state.pdf_data = extract_pdf_data(st.session_state.uploaded_pdf)
                st.session_state.pdf_processed = True
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
    
    else:  # Upload CSV/Excel
        if st.session_state.uploaded_file is not None:
            with st.spinner("🔄 Đang đọc file..."):
                try:
                    file = st.session_state.uploaded_file
                    if file.name.endswith('.csv'):
                        st.session_state.df_upload = pd.read_csv(file)
                    else:
                        st.session_state.df_upload = pd.read_excel(file)
                    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                except Exception as e:
                    st.error(f"❌ Lỗi đọc file: {str(e)}")
    
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
            company_name = info.get('longName', info.get('shortName', ticker))
            st.subheader(f"🏢 {company_name} ({ticker})")
            
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
                    st.dataframe(financials, use_container_width=True)
                else:
                    st.info("ℹ️ Không có dữ liệu báo cáo KQKD")
            
            with tab2:
                cashflow = data.get('cashflow')
                if cashflow is not None and not cashflow.empty:
                    st.dataframe(cashflow, use_container_width=True)
                else:
                    st.info("ℹ️ Không có dữ liệu báo cáo dòng tiền")
            
            with tab3:
                balance = data.get('balance_sheet')
                if balance is not None and not balance.empty:
                    st.dataframe(balance, use_container_width=True)
                else:
                    st.info("ℹ️ Không có dữ liệu bảng CĐKT")
            
            with tab4:
                history = data.get('history')
                if history is not None and not history.empty:
                    fig = px.line(history, y='Close', title=f'Giá đóng cửa {ticker}')
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("📋 Xem dữ liệu chi tiết"):
                        st.dataframe(history.tail(20), use_container_width=True)
                else:
                    st.info("ℹ️ Không có dữ liệu lịch sử giá")
        
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
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Việt Nam:**\n- VNM\n- FPT\n- MSN\n- HPG\n- VIC")
            with col2:
                st.markdown("**Quốc tế:**\n- AAPL\n- MSFT\n- GOOGL\n- TSLA\n- BABA")

# Case 2: PDF - ĐÃ SỬA LỖI
elif data_source == "Upload PDF":
    
    # Hiển thị trạng thái
    if st.session_state.pdf_processed and st.session_state.pdf_data:
        data = st.session_state.pdf_data
        
        # Hiển thị thông báo - ĐÃ SỬA
        if data.get('success'):
            st.markdown(f"""
            <div class="success-box">
                {data.get('message', '✅ Xử lý PDF thành công!')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="warning-box">
                {data.get('message', '⚠️ Có lỗi khi xử lý PDF')}
            </div>
            """, unsafe_allow_html=True)
        
        # Hiển thị tabs
        if data.get('success'):
            tab1, tab2, tab3 = st.tabs(["📊 Bảng dữ liệu", "📝 Dữ liệu tài chính", "📄 Text"])
            
            # Tab 1: Bảng dữ liệu
            with tab1:
                tables = data.get('tables', [])
                if tables:
                    for i, table in enumerate(tables):
                        with st.expander(f"📊 Bảng {i+1} (Trang {table['page']})"):
                            st.dataframe(table['dataframe'], use_container_width=True)
                            
                            # Nút tải xuống
                            csv = table['dataframe'].to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"📥 Tải bảng {i+1}",
                                data=csv,
                                file_name=f"bang_{i+1}.csv",
                                mime="text/csv"
                            )
                else:
                    st.info("ℹ️ Không tìm thấy bảng dữ liệu trong PDF")
            
            # Tab 2: Dữ liệu tài chính
            with tab2:
                financial_data = data.get('financial_data', [])
                if financial_data:
                    df_fin = pd.DataFrame(financial_data)
                    st.dataframe(df_fin, use_container_width=True)
                else:
                    st.info("ℹ️ Không tìm thấy dữ liệu tài chính")
            
            # Tab 3: Text
            with tab3:
                text_data = data.get('text', [])
                if text_data:
                    for i, text in enumerate(text_data):
                        with st.expander(f"📄 Trang {i+1}"):
                            st.text(text[:2000] + "..." if len(text) > 2000 else text)
                else:
                    st.info("ℹ️ Không có dữ liệu text")
        
        else:
            st.error(f"❌ {data.get('error', 'Lỗi không xác định')}")
            
            # Hướng dẫn khắc phục
            with st.expander("🔧 Hướng dẫn khắc phục"):
                st.markdown("""
                1. **Kiểm tra file PDF** có bị lỗi không
                2. **Cài đặt thư viện** đầy đủ:
                   ```bash
                   pip install pdfplumber PyPDF2 --upgrade
