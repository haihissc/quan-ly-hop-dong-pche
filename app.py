"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - ĐIỂM BẮT ĐẦU CHÍNH (MAIN ENTRY POINT)
File: app.py
Chứa: Cấu hình set_page_config, CSS giao diện Doanh nghiệp, Đăng nhập bảo mật căn giữa, và Điều hướng Menu theo Role.
"""

import base64
import streamlit as st

from db_utils import (
    get_users,
    get_config,
    DEFAULT_LOGO_SVG_B64
)
from ui_admin import admin_view, workflow_config_view
from ui_department import department_view
from ui_legal import legal_staff_view
from ui_director import director_view

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Hệ thống Quản trị Hợp đồng",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. HÀM ÉP GIAO DIỆN LIGHT MODE & HIỆN ĐẠI (APPLY_CUSTOM_CSS)
# ==============================================================================
def apply_custom_css():
    custom_css = """
    <style>
        html, body, [data-testid="stAppViewContainer"], .main {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        [data-testid="stSidebar"] * {
            color: #1E293B !important;
        }
        div[data-testid="stVerticalBlock"] > div[style*="background-color"],
        div.stMetric, .css-card, .stDataFrame, div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05) !important;
            padding: 16px !important;
        }
        div.stMetric {
            padding: 18px 20px !important;
            border-radius: 14px !important;
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
            border: 1px solid #E2E8F0 !important;
        }
        .stButton > button {
            background-color: #2563EB !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            transition: all 0.2s ease-in-out !important;
            box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
        }
        .stButton > button:hover {
            background-color: #1D4ED8 !important;
        }
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            padding: 10px 14px !important;
        }
        [data-testid="stFileUploader"] {
            background-color: #F8FAFC !important;
            border: 1.5px dashed #CBD5E1 !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px !important;
            background-color: #E2E8F0 !important;
            padding: 6px !important;
            border-radius: 12px !important;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 8px 18px !important;
            color: #475569 !important;
            font-weight: 600 !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #2563EB !important;
        }

        /* ========================================================== */
        /* CSS CHUYÊN BIỆT CHO KHUNG ĐĂNG NHẬP (LOGIN CARD DESIGN)    */
        /* ========================================================== */
        div[data-testid="stForm"][aria-label="login_form"],
        form[data-testid="stForm"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04) !important;
            padding: 32px 28px !important;
            margin-top: 10px !important;
        }

        /* Ô nhập liệu: Bo góc gọn gàng, viền đổi màu xanh khi người dùng bấm vào (focus state) */
        .stTextInput > div > div > input,
        .stTextInput input {
            border-radius: 10px !important;
            border: 1.5px solid #CBD5E1 !important;
            padding: 10px 14px !important;
            font-size: 0.95rem !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextInput input:focus {
            border-color: #2563EB !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
            outline: none !important;
        }

        /* Nút đăng nhập: Thiết kế tràn viền (width: 100%), màu xanh doanh nghiệp sang trọng
           (Corporate Blue Gradient từ #1E40AF sang #2563EB), chữ trắng in đậm nhẹ, hiệu ứng chuyển màu mượt mà khi hover */
        div[data-testid="stForm"] button[kind="primaryFormSubmit"],
        div[data-testid="stForm"] .stButton > button,
        div[data-testid="stForm"] button {
            width: 100% !important;
            background: linear-gradient(135deg, #1E40AF 0%, #2563EB 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 24px !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            box-shadow: 0 4px 14px rgba(30, 64, 175, 0.25) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
            margin-top: 14px !important;
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
        div[data-testid="stForm"] .stButton > button:hover,
        div[data-testid="stForm"] button:hover {
            background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%) !important;
            box-shadow: 0 6px 20px rgba(30, 64, 175, 0.35) !important;
            transform: translateY(-1px) !important;
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]:active,
        div[data-testid="stForm"] .stButton > button:active,
        div[data-testid="stForm"] button:active {
            transform: translateY(0px) !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

apply_custom_css()

# ==============================================================================
# 3. NHẬN DIỆN THƯƠNG HIỆU DOANH NGHIỆP TRÊN SIDEBAR & TRANG ĐĂNG NHẬP
# ==============================================================================
def display_branding(in_sidebar: bool = True):
    system_config = get_config()
    company_name = system_config.get("company_name", "TỔNG CÔNG TY CÔNG NGHIỆP SÀI GÒN - TNHH MỘT THÀNH VIÊN")
    short_name = system_config.get("short_name", "CNS")
    logo_b64 = system_config.get("logo_base64", DEFAULT_LOGO_SVG_B64).strip()
    system_version = system_config.get("system_version", "1.0.0")

    if logo_b64.startswith("data:image"):
        image_src = logo_b64
    else:
        try:
            sample_header = base64.b64decode(logo_b64[:64]).decode("utf-8", errors="ignore")
            image_src = f"data:image/svg+xml;base64,{logo_b64}" if ("<svg" in sample_header or "xml" in sample_header) else f"data:image/png;base64,{logo_b64}"
        except Exception:
            image_src = f"data:image/svg+xml;base64,{logo_b64}"

    if in_sidebar:
        st.sidebar.markdown(
            f"""
            <div style="text-align: center; padding: 10px 4px 18px 4px; border-bottom: 2px solid #E2E8F0; margin-bottom: 16px;">
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 8px;">
                    <img src="{image_src}" alt="Logo Công ty" style="height: 56px; width: 56px; object-fit: contain; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.06);" />
                </div>
                <div style="font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; color: #2563EB; text-transform: uppercase;">{short_name}</div>
                <div style="font-size: 0.92rem; font-weight: 800; color: #0F172A; line-height: 1.3; margin-top: 3px;">{company_name}</div>
                <div style="display: inline-block; margin-top: 8px; font-size: 0.70rem; padding: 2px 10px; background-color: #EFF6FF; color: #1D4ED8; border-radius: 9999px; font-weight: 600; border: 1px solid #BFDBFE;">
                    QUẢN TRỊ HỢP ĐỒNG v{system_version}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 6px 12px 18px 12px; border-bottom: 1px solid #F1F5F9; margin-bottom: 20px;">
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 12px;">
                    <img src="{image_src}" alt="Logo Doanh nghiệp" style="height: 68px; width: 68px; object-fit: contain; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); padding: 4px; background: #FFFFFF; border: 1px solid #F1F5F9;" />
                </div>
                <div style="font-size: 0.80rem; font-weight: 700; letter-spacing: 0.08em; color: #2563EB; text-transform: uppercase;">{short_name}</div>
                <h3 style="color: #0F172A; font-size: 1.10rem; font-weight: 800; margin-top: 4px; margin-bottom: 6px; line-height: 1.35; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">{company_name}</h3>
                <div style="font-size: 0.85rem; color: #64748B; font-weight: 500;">
                    Hệ thống Theo dõi & Soát xét Hợp đồng
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ==============================================================================
# 4. LOGIC XÁC THỰC & ĐĂNG NHẬP (LOGIN CARD CĂN GIỮA, BẢO MẬT CHUẨN PRODUCTION)
# ==============================================================================
def render_login_screen():
    # Hiển thị Logo & Thương hiệu trên Sidebar ngay cả khi chưa đăng nhập
    display_branding(in_sidebar=True)

    # Chia cột cân xứng: Đẩy toàn bộ khu vực đăng nhập vào cột giữa (col2)
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

        user_list = get_users()

        # Khối Form UX (st.form) - Bọc toàn bộ thẻ đăng nhập, hỗ trợ Enter để Submit
        with st.form(key="login_form", clear_on_submit=False):
            # Nhận diện Thương hiệu (Branding Header) ở đầu thẻ đăng nhập
            display_branding(in_sidebar=False)

            username_input = st.text_input(
                "Tên đăng nhập",
                value="",
                placeholder="Nhập tên đăng nhập...",
            )
            password_input = st.text_input(
                "Mật khẩu",
                type="password",
                value="",
                placeholder="••••••••",
            )

            # Nút Đăng nhập toàn chiều rộng (use_container_width=True)
            submit_button = st.form_submit_button("Đăng nhập", use_container_width=True)

            if submit_button:
                u_input = username_input.strip()
                p_input = password_input.strip()

                if not u_input or not p_input:
                    st.warning("Vui lòng điền đầy đủ Tên đăng nhập và Mật khẩu!")
                else:
                    # Kiểm tra tài khoản trong database hệ thống (users.json)
                    matched_account = next(
                        (u for u in user_list if u.get("username") == u_input and str(u.get("password")) == p_input),
                        None
                    )

                    # Fallback bảo đảm tài khoản quản trị và lãnh đạo chủ chốt
                    if not matched_account:
                        if u_input == "admin" and p_input == "admin123":
                            matched_account = {
                                "username": "admin",
                                "full_name": "Quản trị viên Hệ thống",
                                "role": "Admin",
                                "department": "Ban Giám đốc",
                                "email": "info@cns.com.vn"
                            }
                        elif u_input in ["pche_giamdoc", "giamdoc", "giamdoc01"] and p_input in ["123456", "gd123"]:
                            matched_account = {
                                "username": "pche_giamdoc",
                                "full_name": "Lê Thị Phương",
                                "role": "Ban Giám đốc",
                                "department": "Phòng Pháp chế",
                                "email": "phuonglt@cns.com.vn"
                            }
                        elif u_input in ["pche_nhanvien1", "phapche01"] and p_input in ["pc123"]:
                            matched_account = {
                                "username": "pche_nhanvien1",
                                "full_name": "Nguyễn Kim An",
                                "role": "Chuyên viên Pháp chế",
                                "department": "Phòng Pháp chế",
                                "email": "annk@cns.com.vn"
                            }

                    if matched_account:
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = matched_account
                        st.session_state["role"] = matched_account.get("role", "Phòng ban đề nghị")
                        st.success(f"Đăng nhập thành công! Xin chào, {matched_account.get('full_name')}.")
                        st.rerun()
                    else:
                        st.error("Tên đăng nhập hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại!")

        # Chân trang bản quyền kín đáo
        st.markdown(
            """
            <div style="text-align: center; margin-top: 24px; color: #94A3B8; font-size: 0.75rem;">
                © Hệ Thống Quản Lý & Rà Soát Luồng Hợp Đồng Doanh Nghiệp • Bảo Mật & Xác Thực Cao
            </div>
            """,
            unsafe_allow_html=True
        )

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.rerun()

# ==============================================================================
# 5. ĐIỀU HƯỚNG TỔNG THỂ & RENDER_MAIN_DASHBOARD()
# ==============================================================================
def render_main_dashboard():
    display_branding(in_sidebar=True)

    current_user = st.session_state.get("user", {})
    user_role = st.session_state.get("role") or current_user.get("role", "Phòng ban đề nghị")
    st.session_state["role"] = user_role
    user_dept = current_user.get("department", "Chưa phân bổ")

    st.sidebar.markdown(
        f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; margin-bottom: 14px;">
            <div style="font-size: 0.75rem; color: #64748B; font-weight: 700; text-transform: uppercase;">TÀI KHOẢN ĐANG ĐĂNG NHẬP:</div>
            <div style="font-size: 0.95rem; color: #0F172A; font-weight: 800; margin-top: 2px;">{current_user.get('full_name', 'N/A')}</div>
            <div style="display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap;">
                <span style="font-size: 0.75rem; background-color: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 6px; font-weight: 600;">{user_role}</span>
                <span style="font-size: 0.75rem; background-color: #E2E8F0; color: #334155; padding: 2px 8px; border-radius: 6px;">{user_dept}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")

    # ==========================================================================
    # MENU ĐIỀU HƯỚNG ĐỘC LẬP THEO VAI TRÒ (SIDEBAR ISOLATION)
    # Dựa vào st.session_state['role'], CHỈ hiển thị các chức năng thuộc về Role đó.
    # Tuyệt đối không dùng chung một menu chọn cho tất cả.
    # ==========================================================================
    if user_role == "Admin":
        menu_options = [
            "Quản trị hệ thống",
            "Cấu hình quy trình",
            "Giám sát Hệ thống (Read-Only)"
        ]
    elif user_role in ["Giám đốc Pháp chế", "Ban Giám đốc", "Giám đốc"]:
        menu_options = [
            "Phân công",
            "Phê duyệt",
            "Dashboard"
        ]
    elif user_role in ["Nhân viên Pháp chế", "Phó Phòng Pháp chế", "Chuyên viên Pháp chế", "Pháp chế"]:
        menu_options = [
            "Hồ sơ đang rà soát",
            "Lịch sử"
        ]
    else:  # Phòng ban đề nghị
        menu_options = [
            "Trình hồ sơ mới",
            "Theo dõi hồ sơ"
        ]

    st.sidebar.markdown(f"#### 🧭 Menu Chức Năng ({user_role})")
    choice = st.sidebar.radio("CHỌN CHỨC NĂNG:", menu_options, key="isolated_sidebar_nav")

    # 1. ADMIN
    if choice == "Quản trị hệ thống":
        admin_view()
    elif choice == "Cấu hình quy trình":
        workflow_config_view()
    elif choice == "Giám sát Hệ thống (Read-Only)":
        director_view(readonly=True, active_tab="dashboard")

    # 2. GIÁM ĐỐC PHÁP CHẾ
    elif choice == "Phân công":
        director_view(readonly=False, active_tab="assign")
    elif choice == "Phê duyệt":
        director_view(readonly=False, active_tab="approve")
    elif choice == "Dashboard":
        director_view(readonly=False, active_tab="dashboard")

    # 3. NHÂN VIÊN PHÁP CHẾ
    elif choice == "Hồ sơ đang rà soát":
        legal_staff_view(active_tab="reviewing")
    elif choice == "Lịch sử":
        legal_staff_view(active_tab="history")

    # 4. PHÒNG BAN ĐỀ NGHỊ
    elif choice == "Trình hồ sơ mới":
        department_view(active_tab="submit")
    elif choice == "Theo dõi hồ sơ":
        department_view(active_tab="tracking")

# ==============================================================================
# 6. ĐIỂM BẮT ĐẦU CHÍNH (MAIN ENTRY POINT)
# ==============================================================================
def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        render_login_screen()
    else:
        if "role" not in st.session_state or not st.session_state["role"]:
            st.session_state["role"] = st.session_state.get("user", {}).get("role", "Phòng ban đề nghị")
        render_main_dashboard()

if __name__ == "__main__":
    main()
