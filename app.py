import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Cấu hình trang
st.set_page_config(
    page_title="Financial Report Automation",
    page_icon="💰",
    layout="wide"
)

# Tiêu đề chính
st.title("💰 Hệ thống tự động hóa báo cáo tài chính")
st.markdown("---")

# Sidebar - Upload và cấu hình
with st.sidebar:
    st.header("⚙️ Cấu hình báo cáo")
    
    # Upload file
    uploaded_file = st.file_uploader(
        "Tải lên file dữ liệu (CSV, Excel)",
        type=['csv', 'xlsx', 'xls']
    )
    
    # Chọn loại báo cáo
    report_type = st.selectbox(
        "Chọn loại báo cáo",
        ["Báo cáo thu nhập", "Bảng cân đối kế toán", "Báo cáo dòng tiền", "Phân tích tỷ lệ"]
    )
    
    # Chọn khoảng thời gian
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Từ ngày",
            datetime.now() - timedelta(days=30)
        )
    with col2:
        end_date = st.date_input(
            "Đến ngày",
            datetime.now()
        )
    
    # Tùy chọn hiển thị
    show_charts = st.checkbox("Hiển thị biểu đồ", value=True)
    show_summary = st.checkbox("Hiển thị tổng quan", value=True)

# Main content
if uploaded_file is not None:
    try:
        # Đọc dữ liệu
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Hiển thị thông tin dữ liệu
        st.subheader("📊 Dữ liệu tài chính")
        
        # Tabs cho các phần khác nhau
        tab1, tab2, tab3, tab4 = st.tabs([
            "Dữ liệu thô", 
            "Báo cáo thu nhập", 
            "Phân tích tỷ lệ",
            "Biểu đồ"
        ])
        
        with tab1:
            st.dataframe(df)
            st.caption(f"Tổng số dòng: {len(df)} | Tổng số cột: {len(df.columns)}")
            
            # Thống kê cơ bản
            if show_summary:
                st.subheader("Thống kê mô tả")
                st.dataframe(df.describe())
        
        with tab2:
            st.subheader("Báo cáo thu nhập")
            
            # Tạo báo cáo thu nhập mẫu
            income_data = {
                'Chỉ tiêu': ['Doanh thu', 'Giá vốn hàng bán', 'Lợi nhuận gộp', 
                            'Chi phí bán hàng', 'Chi phí quản lý', 'Lợi nhuận trước thuế',
                            'Thuế TNDN', 'Lợi nhuận sau thuế'],
                'Giá trị': [1000000, 600000, 400000, 100000, 50000, 250000, 50000, 200000],
                'Tỷ lệ %': ['100%', '60%', '40%', '10%', '5%', '25%', '5%', '20%']
            }
            income_df = pd.DataFrame(income_data)
            
            # Format số
            st.dataframe(
                income_df.style.format({'Giá trị': '{:,.0f}'}),
                use_container_width=True
            )
            
            # Biểu đồ
            if show_charts:
                fig = px.bar(
                    income_df[:-1],  # Bỏ dòng cuối
                    x='Chỉ tiêu',
                    y='Giá trị',
                    title='Cơ cấu báo cáo thu nhập',
                    color='Chỉ tiêu'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("Phân tích tỷ lệ tài chính")
            
            # Các tỷ lệ tài chính
            ratios = {
                'Tỷ lệ thanh khoản': {
                    'Tỷ lệ thanh toán hiện hành': 2.5,
                    'Tỷ lệ thanh toán nhanh': 1.8,
                    'Tỷ lệ tiền mặt': 0.9
                },
                'Tỷ lệ hoạt động': {
                    'Vòng quay hàng tồn kho': 6.5,
                    'Vòng quay khoản phải thu': 8.2,
                    'Vòng quay tài sản': 1.3
                },
                'Tỷ lệ sinh lời': {
                    'ROA': '12.5%',
                    'ROE': '18.3%',
                    'Biên lợi nhuận': '20%'
                },
                'Tỷ lệ nợ': {
                    'Tỷ lệ nợ/vốn CSH': 1.2,
                    'Tỷ lệ nợ/tổng tài sản': 0.45,
                    'Khả năng thanh toán lãi vay': 4.5
                }
            }
            
            # Hiển thị dưới dạng metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("ROA", "12.5%", "1.2%")
                st.metric("ROE", "18.3%", "2.1%")
            
            with col2:
                st.metric("Biên lợi nhuận", "20%", "1.5%")
                st.metric("Tỷ lệ thanh khoản", "2.5", "0.3")
            
            with col3:
                st.metric("Vòng quay TS", "1.3", "0.1")
                st.metric("Tỷ lệ nợ", "45%", "-2%")
            
            with col4:
                st.metric("EPS", "5,200", "320")
                st.metric("P/E", "15.2", "-1.3")
            
            # Biểu đồ radar cho các tỷ lệ
            if show_charts:
                categories = ['Thanh khoản', 'Hoạt động', 'Sinh lời', 'Nợ', 'Tăng trưởng']
                values = [4, 3.5, 4.2, 3, 3.8]
                
                fig = go.Figure(data=go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself'
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 5]
                        )),
                    showlegend=False,
                    title="Đánh giá tổng thể (thang điểm 5)"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            st.subheader("Biểu đồ phân tích")
            
            if show_charts:
                chart_type = st.selectbox(
                    "Chọn loại biểu đồ",
                    ["Biểu đồ đường", "Biểu đồ cột", "Biểu đồ tròn", "Biểu đồ phân tán"]
                )
                
                # Tạo dữ liệu mẫu
                dates = pd.date_range(start=start_date, end=end_date, periods=10)
                revenue = np.random.randint(800000, 1200000, size=10)
                expense = np.random.randint(500000, 800000, size=10)
                profit = revenue - expense
                
                chart_df = pd.DataFrame({
                    'Ngày': dates,
                    'Doanh thu': revenue,
                    'Chi phí': expense,
                    'Lợi nhuận': profit
                })
                
                if chart_type == "Biểu đồ đường":
                    fig = px.line(chart_df, x='Ngày', y=['Doanh thu', 'Chi phí', 'Lợi nhuận'],
                                title='Xu hướng doanh thu, chi phí và lợi nhuận')
                
                elif chart_type == "Biểu đồ cột":
                    fig = px.bar(chart_df, x='Ngày', y=['Doanh thu', 'Chi phí', 'Lợi nhuận'],
                                title='So sánh doanh thu, chi phí và lợi nhuận', barmode='group')
                
                elif chart_type == "Biểu đồ tròn":
                    total_values = [revenue.sum(), expense.sum(), profit.sum()]
                    labels = ['Doanh thu', 'Chi phí', 'Lợi nhuận']
                    fig = px.pie(values=total_values, names=labels, title='Cơ cấu tổng thể')
                
                else:  # Scatter plot
                    fig = px.scatter(chart_df, x='Doanh thu', y='Lợi nhuận',
                                    title='Mối tương quan doanh thu và lợi nhuận')
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Nút xuất báo cáo
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Xuất báo cáo PDF", use_container_width=True):
                st.success("Đã xuất báo cáo PDF thành công!")
        
        with col2:
            if st.button("📊 Xuất báo cáo Excel", use_container_width=True):
                st.success("Đã xuất báo cáo Excel thành công!")
        
        with col3:
            if st.button("📧 Gửi email báo cáo", use_container_width=True):
                st.info("Tính năng đang phát triển!")
    
    except Exception as e:
        st.error(f"Lỗi khi đọc file: {str(e)}")
        st.info("Vui lòng kiểm tra lại định dạng file!")

else:
    # Hiển thị hướng dẫn khi chưa upload file
    st.info("👈 Vui lòng tải lên file dữ liệu để bắt đầu!")
    
    # Hiển thị dữ liệu mẫu
    st.subheader("📋 Dữ liệu mẫu")
    
    sample_data = {
        'Ngày': pd.date_range(start='2024-01-01', periods=5, freq='D'),
        'Doanh thu': [1000000, 1200000, 1100000, 1300000, 1250000],
        'Chi phí': [600000, 700000, 650000, 750000, 720000],
        'Lợi nhuận': [400000, 500000, 450000, 550000, 530000]
    }
    sample_df = pd.DataFrame(sample_data)
    st.dataframe(sample_df)
    
    # Biểu đồ mẫu
    fig = px.line(sample_df, x='Ngày', y=['Doanh thu', 'Chi phí', 'Lợi nhuận'],
                  title='Dữ liệu mẫu - Xu hướng doanh thu và chi phí')
    st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("© 2024 - Hệ thống tự động hóa báo cáo tài chính | Phát triển bởi Your Name")
