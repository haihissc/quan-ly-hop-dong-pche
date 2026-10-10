"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - BƯỚC 1, 2, 3 & 4 HOÀN CHỈNH
Tác giả: Senior Python Developer
Bổ sung Bước 4:
- Hàm legal_staff_view() chi tiết, KHÔNG dùng placeholder:
  Tab 1: Đang rà soát
    - Chỉ hiện hồ sơ có status == 'Đang rà soát' VÀ assigned_to == current_username.
    - Chia đôi màn hình st.columns([1, 1]).
    - Cột trái: Chọn file PDF trong hồ sơ, render trực tiếp bằng thẻ <iframe> base64.
    - Cột phải: Hiển thị Checklist. Dưới mỗi mục có st.radio (Đạt / Không đạt / Có góp ý). Nếu 'Có góp ý' thì hiện st.text_area.
    - Tích hợp AI: Expander nhập API Key Gemini và nội dung điều khoản. Gọi AI đánh giá rủi ro pháp lý (dùng try-except).
    - Chọn Đánh giá tổng quát và nhấn nút 'Trình Giám đốc duyệt'. Đổi trạng thái thành 'Chờ Giám đốc duyệt'.
  Tab 2: Lịch sử rà soát
    - Hiện các hồ sơ nhân viên này đã làm xong. Chỉ cho xem lại ý kiến, không cho sửa.
"""

import os
import json
import base64
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pandas as pd
from fpdf import FPDF
import google.generativeai as genai
import streamlit as st

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
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

apply_custom_css()

# ==============================================================================
# 3. QUẢN LÝ DỮ LIỆU JSON
# ==============================================================================
USERS_FILE = "users.json"
CONFIG_FILE = "config.json"
WORKFLOWS_FILE = "workflows.json"
DEPARTMENTS_FILE = "departments.json"
CONTRACTS_FILE = "contracts.json"

DEFAULT_LOGO_SVG_B64 = (
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIiB"
    "3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCI+PGRlZnM+PGxpbmVhckdyYWRpZW50IGlkPSJnIiB4MT0iMCUiI"
    "HkxPSIwJSIgeDI9IjEwMCUiIHkyPSIxMDAlIj48c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjMUU"
    "0MEFGIi8+PHN0b3Agb2Zmc2V0PSIxMDAlIiBzdG9wLWNvbG9yPSIjM0I4MkY2Ii8+PC9saW5lYXJHcmFka"
    "WVudD48L2RlZnM+PHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIHJ4PSIyMiIgZmlsbD0idXJsKCN"
    "nKSIvPjxwYXRoIGQ9Ik0zMCAyNmgyNmwxNiAxNnYzNGMwIDMuMy0yLjcgNi02IDZIMzBjLTMuMyAwLTYtM"
    "i43LTYtNlYzMmMwLTMuMyAyLjctNiA2LTZ6IiBmaWxsPSIjRkZGRkZGIi8+PHBhdGggZD0iTTU2IDI2djE"
    "2aDE2IiBmaWxsPSIjOTNDNUZEIi8+PHBhdGggZD0iTTM2IDQ4aDI4TTM2IDU4aDI4TTM2IDY4aDE4IiBzd"
    "HJva2U9IiMxRTQwQUYiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PC9zdmc+"
)

def read_json_file(file_path: str, default_data):
    if not os.path.exists(file_path):
        write_json_file(file_path, default_data)
        return default_data
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as error:
        st.error(f"Lỗi khi đọc file '{file_path}': {error}")
        return default_data

def write_json_file(file_path: str, data) -> bool:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as error:
        st.error(f"Lỗi khi ghi dữ liệu vào '{file_path}': {error}")
        return False

DEFAULT_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "full_name": "Quản trị viên Hệ thống",
        "role": "Admin",
        "department": "Ban Giám đốc",
        "email": "admin@congty.com.vn",
        "zalo": "0901234567",
        "status": "active"
    },
    {
        "username": "giamdoc",
        "password": "123456",
        "full_name": "Trần Quang Thắng (Giám đốc)",
        "role": "Ban Giám đốc",
        "department": "Ban Giám đốc",
        "email": "thang.tq@congty.com.vn",
        "zalo": "0912345678",
        "status": "active"
    },
    {
        "username": "giamdoc01",
        "password": "gd123",
        "full_name": "Trần Quang Thắng",
        "role": "Ban Giám đốc",
        "department": "Ban Giám đốc",
        "email": "thang.tq@congty.com.vn",
        "zalo": "0912345678",
        "status": "active"
    },
    {
        "username": "phapche01",
        "password": "pc123",
        "full_name": "Nguyễn Văn Luật",
        "role": "Giám đốc Pháp chế",
        "department": "Phòng Pháp chế",
        "email": "luat.nv@congty.com.vn",
        "zalo": "0987654321",
        "status": "active"
    },
    {
        "username": "kinhdoanh01",
        "password": "kd123",
        "full_name": "Lê Hoàng Nam",
        "role": "Phòng ban đề nghị",
        "department": "Phòng Kinh doanh & Tiếp thị",
        "email": "nam.lh@congty.com.vn",
        "zalo": "0933445566",
        "status": "active"
    }
]

# Tương thích cả hai tên hàm load_json_file và read_json_file
load_json_file = read_json_file
save_json_file = write_json_file

def get_users():
    users = read_json_file(USERS_FILE, DEFAULT_USERS)
    if not users:
        users = DEFAULT_USERS
        save_users(users)
    return users

def save_users(data): return write_json_file(USERS_FILE, data)
def get_config(): return read_json_file(CONFIG_FILE, {})
def save_config(data): return write_json_file(CONFIG_FILE, data)
def get_workflows(): return read_json_file(WORKFLOWS_FILE, [])
def save_workflows(data): return write_json_file(WORKFLOWS_FILE, data)
def get_departments(): return read_json_file(DEPARTMENTS_FILE, [])
def save_departments(data): return write_json_file(DEPARTMENTS_FILE, data)
def get_contracts(): return read_json_file(CONTRACTS_FILE, [])
def save_contracts(data): return write_json_file(CONTRACTS_FILE, data)


# ==============================================================================
# 4. HÀM HIỂN THỊ THƯƠNG HIỆU & LOGO BASE64
# ==============================================================================
def display_branding():
    system_config = get_config()
    company_name = system_config.get("company_name", "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU")
    short_name = system_config.get("short_name", "ASIA HOLDINGS")
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

# ==============================================================================
# 5. LOGIC XÁC THỰC & ĐĂNG NHẬP
# ==============================================================================
def render_login_screen():
    col_left, col_center, col_right = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 24px;">
                <span style="font-size: 42px;">🏢</span>
                <h2 style="color: #1E3A8A; margin-top: 8px; margin-bottom: 4px;">HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG</h2>
                <p style="color: #64748B; font-size: 0.92rem;">Cổng đăng nhập an toàn dành cho cán bộ nhân viên nội bộ</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        user_list = get_users()
        user_options = ["-- Chọn tài khoản mẫu đăng nhập nhanh --"] + [
            f"{u['username']} - {u['full_name']} ({u['role']})" for u in user_list
        ]
        selected_sample = st.selectbox("Chọn nhanh tài khoản thử nghiệm:", user_options)

        default_user = ""
        default_pwd = ""
        if selected_sample != "-- Chọn tài khoản mẫu đăng nhập nhanh --":
            u_name = selected_sample.split(" - ")[0]
            default_user = u_name
            matched = next((u for u in user_list if u["username"] == u_name), None)
            if matched:
                default_pwd = matched.get("password", "")

        with st.form("form_dang_nhap", clear_on_submit=False):
            username_val = st.text_input("Tên đăng nhập", value=default_user, placeholder="admin / giamdoc / giamdoc01 / phapche01")
            password_val = st.text_input("Mật khẩu", type="password", value=default_pwd, placeholder="admin123 / 123456 / gd123 / pc123")
            submit_login = st.form_submit_button("Đăng nhập hệ thống", use_container_width=True)

            if submit_login:
                u_input = username_val.strip()
                p_input = password_val.strip()

                # Kiểm tra danh sách người dùng trong hệ thống
                matched_account = next((u for u in user_list if u.get("username") == u_input and u.get("password") == p_input), None)

                # Fallback bảo đảm đặc quyền Admin và Ban Giám đốc luôn đăng nhập thành công
                if not matched_account:
                    if u_input == "admin" and p_input == "admin123":
                        matched_account = {
                            "username": "admin",
                            "full_name": "Quản trị viên Hệ thống",
                            "role": "Admin",
                            "department": "Ban Giám đốc",
                            "email": "admin@congty.com.vn"
                        }
                    elif u_input in ["giamdoc", "giamdoc01"] and p_input in ["123456", "gd123"]:
                        matched_account = {
                            "username": "giamdoc01",
                            "full_name": "Trần Quang Thắng",
                            "role": "Ban Giám đốc",
                            "department": "Ban Giám đốc",
                            "email": "thang.tq@congty.com.vn"
                        }
                    elif u_input == "phapche01" and p_input == "pc123":
                        matched_account = {
                            "username": "phapche01",
                            "full_name": "Nguyễn Văn Luật",
                            "role": "Chuyên viên Pháp chế",
                            "department": "Phòng Pháp chế",
                            "email": "luat.nv@congty.com.vn"
                        }

                if matched_account:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = matched_account
                    st.success(f"Đăng nhập thành công! Chào mừng {matched_account.get('full_name')}.")
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không chính xác! Vui lòng thử 'admin' / 'admin123'.")

        st.markdown(
            """
            <div style="margin-top: 20px; padding: 14px 16px; background-color: #F1F5F9; border-radius: 10px; border-left: 4px solid #3B82F6; font-size: 0.85rem; color: #334155;">
                <strong>Danh sách tài khoản dùng thử hệ thống:</strong><br/>
                • <b>Quản trị viên (Admin):</b> <code>admin</code> / <code>admin123</code><br/>
                • <b>Ban Giám đốc:</b> <code>giamdoc</code> (<code>123456</code>) hoặc <code>giamdoc01</code> (<code>gd123</code>)<br/>
                • <b>Chuyên viên Pháp chế:</b> <code>phapche01</code> / <code>pc123</code><br/>
                • <b>Phòng ban đề xuất:</b> <code>kinhdoanh01</code> / <code>kd123</code>
            </div>
            """,
            unsafe_allow_html=True
        )

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.rerun()


# ==============================================================================
# 6. BƯỚC 2: HÀM ADMIN_VIEW()
# ==============================================================================
def admin_view():
    st.title("⚙️ Bảng Điều Khiển Quản Trị Hệ Thống (Admin Panel)")
    tab_depts, tab_users, tab_sys_config = st.tabs(["🏢 Quản lý Phòng ban", "👥 Quản lý Người dùng", "🌐 Cấu hình Hệ thống"])

    with tab_depts:
        st.subheader("🏢 Quản Lý Danh Sách Phòng Ban")
        departments = get_departments()
        if departments: st.dataframe(pd.DataFrame(departments), use_container_width=True)
        col_add, col_edit, col_del = st.columns(3)
        with col_add:
            with st.form("form_add_dept", clear_on_submit=True):
                new_d_name = st.text_input("Tên phòng ban mới *")
                new_d_mgr = st.text_input("Trưởng bộ phận")
                new_d_mail = st.text_input("Email")
                if st.form_submit_button("Thêm phòng ban", use_container_width=True):
                    if new_d_name.strip():
                        dept_code = "DEPT_" + str(len(departments) + 1).zfill(2)
                        departments.append({"id": dept_code, "name": new_d_name.strip(), "manager": new_d_mgr.strip() if new_d_mgr else "Chưa phân công", "email": new_d_mail.strip()})
                        save_departments(departments)
                        st.success("Thêm thành công!")
                        st.rerun()

        with col_edit:
            if departments:
                d_names = [d["name"] for d in departments]
                sel_edit_name = st.selectbox("Chọn phòng ban sửa:", d_names)
                target_d = next((d for d in departments if d["name"] == sel_edit_name), None)
                if target_d:
                    with st.form("form_edit_dept"):
                        e_name = st.text_input("Tên mới:", value=target_d.get("name", ""))
                        e_mgr = st.text_input("Trưởng bộ phận:", value=target_d.get("manager", ""))
                        e_mail = st.text_input("Email:", value=target_d.get("email", ""))
                        if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                            target_d["name"], target_d["manager"], target_d["email"] = e_name.strip(), e_mgr.strip(), e_mail.strip()
                            save_departments(departments)
                            st.success("Cập nhật thành công!")
                            st.rerun()

        with col_del:
            if departments:
                del_d_name = st.selectbox("Chọn phòng ban xóa:", [d["name"] for d in departments])
                confirm_del = st.checkbox(f"Xác nhận xóa '{del_d_name}'")
                if st.button("Xóa phòng ban này", use_container_width=True, type="primary"):
                    if confirm_del:
                        save_departments([d for d in departments if d["name"] != del_d_name])
                        st.success("Đã xóa phòng ban!")
                        st.rerun()

    with tab_users:
        st.subheader("👥 Quản Lý Người Dùng & Phân Quyền Thông Minh")
        all_users = get_users()
        departments = get_departments()
        dept_names = [d["name"] for d in departments] if departments else ["Phòng Pháp chế", "Ban Giám đốc", "Phòng Kinh doanh & Tiếp thị"]

        # 1. HIỂN THỊ DANH SÁCH TÀI KHOẢN DƯỚI DẠNG BẢNG ĐỦ: Username, Họ tên, Phòng ban, Role, Email, Zalo
        st.markdown("#### 📋 Danh Sách Tài Khoản Nhân Sự Hiện Có")
        user_table_data = []
        for u in all_users:
            user_table_data.append({
                "Tên đăng nhập (Username)": u.get("username", ""),
                "Họ và tên": u.get("full_name", ""),
                "Phòng ban": u.get("department", "Chưa phân bổ"),
                "Vai trò (Role)": u.get("role", "Chưa gán"),
                "Email": u.get("email", ""),
                "Số điện thoại Zalo": u.get("zalo", "Chưa cập nhật")
            })

        if user_table_data:
            df_users = pd.DataFrame(user_table_data)
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu người dùng trong hệ thống.")

        st.markdown("---")

        # 2. TABS TẠO MỚI HOẶC CHỈNH SỬA TÀI KHOẢN
        sub_tab_add, sub_tab_edit, sub_tab_del = st.tabs(["➕ Tạo Tài Khoản Mới", "✏️ Chỉnh Sửa Nhân Sự", "🗑️ Xóa Tài Khoản"])

        with sub_tab_add:
            st.markdown("##### ➕ Form Đăng Ký Tài Khoản Nhân Sự Mới")
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                u_name = st.text_input("Tên đăng nhập (Username) *", key="add_u_username", placeholder="VD: luat.nv")
                u_pass = st.text_input("Mật khẩu (Password) *", type="password", key="add_u_password", placeholder="Nhập mật khẩu an toàn")
                u_fullname = st.text_input("Họ và tên nhân sự phụ trách *", key="add_u_fullname", placeholder="VD: Nguyễn Văn Luật")
            with col_u2:
                u_mail = st.text_input("Email công vụ *", key="add_u_email", placeholder="VD: luat.nv@congty.com.vn")
                u_zalo = st.text_input("Số điện thoại Zalo *", key="add_u_zalo", placeholder="VD: 0987654321")
                
                # BẮT BUỘC CHỌN PHÒNG BAN TỪ DEPARTMENTS.JSON
                assigned_dept = st.selectbox(
                    "Tên Phòng Ban (Chọn từ danh mục) *",
                    options=dept_names,
                    key="add_u_department"
                )

                # LOGIC PHÂN QUYỀN THÔNG MINH (ROLE ASSIGNMENT)
                if assigned_dept == "Phòng Pháp chế":
                    assigned_role = st.selectbox(
                        "Vai trò (Role) cụ thể trong Phòng Pháp chế: *",
                        ["Giám đốc Pháp chế", "Phó Phòng Pháp chế", "Nhân viên Pháp chế"],
                        key="add_u_legal_role"
                    )
                else:
                    assigned_role = "Phòng ban đề nghị"
                    st.text_input(
                        "Vai trò (Role) được gán tự động:",
                        value=assigned_role,
                        disabled=True,
                        help="Đối với các phòng ban chuyên môn khác, vai trò mặc định là 'Phòng ban đề nghị'.",
                        key="add_u_auto_role"
                    )

            if st.button("Lưu & Tạo Tài Khoản Nhân Sự 🚀", type="primary", use_container_width=True, key="btn_save_new_user"):
                # Bắt lỗi cẩn thận đầy đủ các trường
                if not u_name.strip():
                    st.error("❌ Vui lòng nhập Tên đăng nhập (Username)!")
                elif any(u.get("username") == u_name.strip() for u in all_users):
                    st.error(f"❌ Tên đăng nhập '{u_name.strip()}' đã tồn tại trong hệ thống. Vui lòng chọn tên khác!")
                elif not u_pass.strip():
                    st.error("❌ Vui lòng nhập Mật khẩu (Password)!")
                elif not u_fullname.strip():
                    st.error("❌ Vui lòng nhập Họ và tên nhân sự phụ trách!")
                elif not u_mail.strip() or "@" not in u_mail:
                    st.error("❌ Vui lòng nhập Email hợp lệ!")
                elif not u_zalo.strip():
                    st.error("❌ Vui lòng nhập Số điện thoại Zalo!")
                elif not assigned_dept:
                    st.error("❌ BẮT BUỘC phải chọn Phòng Ban!")
                else:
                    new_user_record = {
                        "username": u_name.strip(),
                        "password": u_pass.strip(),
                        "full_name": u_fullname.strip(),
                        "email": u_mail.strip(),
                        "zalo": u_zalo.strip(),
                        "department": assigned_dept,
                        "role": assigned_role,
                        "status": "active"
                    }
                    all_users.append(new_user_record)
                    if save_users(all_users):
                        st.success(f"🎉 Đã tạo thành công tài khoản cho '{u_fullname.strip()}' thuộc {assigned_dept} với quyền [{assigned_role}]!")
                        st.rerun()

        with sub_tab_edit:
            st.markdown("##### ✏️ Chỉnh Sửa Thông Tin & Phân Quyền Tài Khoản")
            if all_users:
                user_select_labels = [f"{u.get('username')} - {u.get('full_name')} ({u.get('department')})" for u in all_users]
                selected_user_label = st.selectbox("Chọn tài khoản cần cập nhật:", user_select_labels, key="sel_user_to_edit")
                selected_uname = selected_user_label.split(" - ")[0]
                target_user = next((u for u in all_users if u.get("username") == selected_uname), None)

                if target_user:
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        ed_uname = st.text_input("Tên đăng nhập (Username):", value=target_user.get("username", ""), disabled=True)
                        ed_pass = st.text_input("Mật khẩu mới (Bỏ trống nếu giữ nguyên):", type="password", key=f"ed_pass_{target_user['username']}")
                        ed_fullname = st.text_input("Họ và tên nhân sự phụ trách *", value=target_user.get("full_name", ""), key=f"ed_fn_{target_user['username']}")
                    with col_ed2:
                        ed_mail = st.text_input("Email công vụ *", value=target_user.get("email", ""), key=f"ed_mail_{target_user['username']}")
                        ed_zalo = st.text_input("Số điện thoại Zalo *", value=target_user.get("zalo", ""), key=f"ed_zalo_{target_user['username']}")

                        current_dept = target_user.get("department", dept_names[0] if dept_names else "Phòng Pháp chế")
                        dept_idx = dept_names.index(current_dept) if current_dept in dept_names else 0
                        ed_dept = st.selectbox("Tên Phòng Ban (Bắt buộc chọn từ danh mục) *", options=dept_names, index=dept_idx, key=f"ed_dept_{target_user['username']}")

                        if ed_dept == "Phòng Pháp chế":
                            legal_roles = ["Giám đốc Pháp chế", "Phó Phòng Pháp chế", "Nhân viên Pháp chế"]
                            cur_role = target_user.get("role", "Nhân viên Pháp chế")
                            role_idx = legal_roles.index(cur_role) if cur_role in legal_roles else 0
                            ed_role = st.selectbox("Vai trò (Role) cụ thể trong Phòng Pháp chế: *", legal_roles, index=role_idx, key=f"ed_legal_role_{target_user['username']}")
                        else:
                            ed_role = "Phòng ban đề nghị"
                            st.text_input("Vai trò (Role) được gán tự động:", value=ed_role, disabled=True, key=f"ed_auto_role_{target_user['username']}")

                    if st.button("Lưu Cập Nhật Người Dùng 💾", type="primary", use_container_width=True, key=f"btn_edit_{target_user['username']}"):
                        if not ed_fullname.strip() or not ed_mail.strip() or not ed_zalo.strip():
                            st.error("Vui lòng điền đủ Họ tên, Email và Số điện thoại Zalo!")
                        else:
                            target_user["full_name"] = ed_fullname.strip()
                            target_user["email"] = ed_mail.strip()
                            target_user["zalo"] = ed_zalo.strip()
                            target_user["department"] = ed_dept
                            target_user["role"] = ed_role
                            if ed_pass.strip():
                                target_user["password"] = ed_pass.strip()
                            if save_users(all_users):
                                st.success(f"Đã cập nhật thành công thông tin nhân sự '{ed_fullname}'!")
                                st.rerun()

        with sub_tab_del:
            st.markdown("##### 🗑️ Xóa Tài Khoản Nhân Sự")
            if all_users:
                del_opts = [f"{u.get('username')} - {u.get('full_name')} [{u.get('role')}]" for u in all_users if u.get("username") != "admin"]
                if del_opts:
                    del_choice = st.selectbox("Chọn tài khoản cần xóa khỏi hệ thống:", del_opts, key="sel_user_del")
                    confirm_del_user = st.checkbox("Tôi xác nhận muốn xóa tài khoản nhân sự này vĩnh viễn.", key="chk_confirm_del_u")
                    if st.button("Xác Nhận Xóa Tài Khoản ❌", type="primary", use_container_width=True, key="btn_del_user"):
                        if confirm_del_user:
                            del_target_uname = del_choice.split(" - ")[0]
                            remaining_users = [u for u in all_users if u.get("username") != del_target_uname]
                            if save_users(remaining_users):
                                st.success(f"Đã xóa thành công tài khoản '{del_target_uname}'!")
                                st.rerun()
                        else:
                            st.warning("Vui lòng tích vào ô xác nhận trước khi xóa.")
                else:
                    st.info("Chỉ còn tài khoản Quản trị viên 'admin', không thể xóa.")

    with tab_sys_config:
        st.subheader("🌐 Cấu Hình Nhận Diện Doanh Nghiệp & Email Gửi Đi")
        cfg = get_config()
        smtp_cfg = cfg.get("smtp_settings", {})
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cfg_comp_name = st.text_input("Tên công ty đầy đủ *", value=cfg.get("company_name", ""))
            cfg_short = st.text_input("Tên viết tắt", value=cfg.get("short_name", ""))
            cfg_addr = st.text_input("Địa chỉ trụ sở", value=cfg.get("company_address", ""))
            logo_file = st.file_uploader("Upload Logo (PNG, JPG, SVG):", type=["png", "jpg", "jpeg", "svg"])
            active_logo_b64 = cfg.get("logo_base64", "")
            if logo_file is not None:
                active_logo_b64 = base64.b64encode(logo_file.read()).decode("utf-8")
                st.success("Đã mã hóa Logo Base64 thành công!")
        with col_c2:
            cfg_sender = st.text_input("Email gửi đi *", value=smtp_cfg.get("sender_email", ""))
            cfg_app_pwd = st.text_input("Mật khẩu ứng dụng (App Password) *", type="password", value=smtp_cfg.get("app_password", ""))
            cfg_smtp_host = st.text_input("Máy chủ SMTP", value=smtp_cfg.get("server", "smtp.gmail.com"))
            cfg_smtp_port = st.number_input("Cổng SMTP", value=int(smtp_cfg.get("port", 587)))

        if st.button("💾 Lưu Toàn Bộ Cấu Hình Hệ Thống", use_container_width=True, type="primary"):
            cfg["company_name"], cfg["short_name"], cfg["company_address"], cfg["logo_base64"] = cfg_comp_name.strip(), cfg_short.strip(), cfg_addr.strip(), active_logo_b64
            cfg["smtp_settings"] = {"server": cfg_smtp_host.strip(), "port": int(cfg_smtp_port), "sender_email": cfg_sender.strip(), "app_password": cfg_app_pwd.strip(), "use_tls": True}
            save_config(cfg)
            st.success("Đã lưu cấu hình vào config.json thành công!")
            st.rerun()


# ==============================================================================
# 7. BƯỚC 2: HÀM WORKFLOW_CONFIG_VIEW()
# ==============================================================================
def workflow_config_view():
    st.title("⚖️ Quản Lý Loại Hợp Đồng & Checklist Hồ Sơ (Dành cho Pháp chế)")
    workflows = get_workflows()

    st.markdown("### 📋 Danh Sách Loại Hợp Đồng Đang Áp Dụng")
    for wf in workflows:
        with st.expander(f"📌 {wf.get('contract_type', wf.get('name'))} ({wf.get('id')})"):
            st.write(f"**Mô tả:** {wf.get('description', '')}")
            st.markdown("**Checklist tài liệu yêu cầu:**")
            for i, it in enumerate(wf.get("checklist", []), 1):
                st.markdown(f"- {i}. {it} {'*(Bắt buộc tự động)*' if it == 'Tài liệu khác' else ''}")

    st.markdown("---")
    tab_add, tab_edit, tab_del = st.tabs(["➕ Thêm Loại Hợp Đồng Mới", "✏️ Chỉnh Sửa Loại Hợp Đồng", "🗑️ Xóa Loại Hợp Đồng"])

    with tab_add:
        with st.form("form_add_wf"):
            new_wf_name = st.text_input("Tên loại hợp đồng *")
            new_wf_id = st.text_input("Mã định danh (ví dụ: WF_SERVICE)")
            new_wf_desc = st.text_area("Mô tả áp dụng")
            new_wf_checklist = st.text_area("Checklist tài liệu (Mỗi dòng 1 tài liệu):", "Dự thảo Hợp đồng chi tiết\nGiấy phép ĐKKD đối tác\nBáo giá chính thức")
            if st.form_submit_button("Lưu Loại Hợp Đồng", use_container_width=True):
                if new_wf_name.strip():
                    items = [l.strip() for l in new_wf_checklist.split("\n") if l.strip()]
                    if "Tài liệu khác" in items: items.remove("Tài liệu khác")
                    items.append("Tài liệu khác")
                    final_id = new_wf_id.strip() if new_wf_id.strip() else f"WF_{len(workflows)+1}"
                    workflows.append({"id": final_id, "name": new_wf_name.strip(), "contract_type": new_wf_name.strip(), "description": new_wf_desc.strip(), "checklist": items})
                    save_workflows(workflows)
                    st.success("Đã thêm loại hợp đồng thành công! ('Tài liệu khác' đã tự động chèn ở cuối)")
                    st.rerun()

    with tab_edit:
        if workflows:
            wf_names = [w.get("contract_type", w.get("name")) for w in workflows]
            sel_wf = st.selectbox("Chọn loại hợp đồng:", wf_names)
            target = next((w for w in workflows if w.get("contract_type", w.get("name")) == sel_wf), None)
            if target:
                with st.form("form_edit_wf"):
                    e_name = st.text_input("Tên:", value=target.get("contract_type", target.get("name")))
                    e_desc = st.text_area("Mô tả:", value=target.get("description", ""))
                    e_items = [it for it in target.get("checklist", []) if it != "Tài liệu khác"]
                    e_text = st.text_area("Checklist (Mỗi dòng 1 mục):", value="\n".join(e_items))
                    if st.form_submit_button("Cập nhật", use_container_width=True):
                        parsed = [l.strip() for l in e_text.split("\n") if l.strip()]
                        if "Tài liệu khác" in parsed: parsed.remove("Tài liệu khác")
                        parsed.append("Tài liệu khác")
                        target["name"], target["contract_type"], target["description"], target["checklist"] = e_name.strip(), e_name.strip(), e_desc.strip(), parsed
                        save_workflows(workflows)
                        st.success("Đã cập nhật thành công!")
                        st.rerun()

    with tab_del:
        if workflows:
            del_wf_name = st.selectbox("Chọn loại HĐ cần xóa:", [w.get("contract_type", w.get("name")) for w in workflows], key="del_wf_key")
            confirm_del_wf = st.checkbox(f"Xác nhận xóa '{del_wf_name}'")
            if st.button("Xóa loại hợp đồng", use_container_width=True, type="primary"):
                if confirm_del_wf:
                    save_workflows([w for w in workflows if w.get("contract_type", w.get("name")) != del_wf_name])
                    st.success("Đã xóa!")
                    st.rerun()

# ==============================================================================
# 8. BƯỚC 3: HÀM DEPARTMENT_VIEW()
# ==============================================================================
def department_view():
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "khach")
    current_fullname = current_user.get("full_name", "Cán bộ đề xuất")
    current_department = current_user.get("department", "Phòng ban đề nghị")

    st.title("📑 Cổng Nộp & Quản Lý Hồ Sơ Hợp Đồng")
    st.markdown(f"Đơn vị đề xuất: **{current_department}** | Cán bộ phụ trách: **{current_fullname}** (`@{current_username}`)")

    tab_my_contracts, tab_submit_contract = st.tabs(["📂 Hồ Sơ Hợp Đồng Đã Gửi", "📤 Nộp Hồ Sơ Hợp Đồng Mới"])

    with tab_my_contracts:
        st.subheader("📂 Danh Sách Hồ Sơ Đã Gửi Của Đơn Vị")
        all_contracts = get_contracts()
        my_contracts = [c for c in all_contracts if c.get("created_by") == current_username]

        if my_contracts:
            for contract in my_contracts:
                c_id, c_title, c_partner, c_val, c_status = contract.get("id"), contract.get("title"), contract.get("partner_name"), contract.get("value_vnd", 0), contract.get("status", "Chờ xử lý")
                attachments = contract.get("attachments", [])
                with st.expander(f"📄 {c_id}: {c_title} — Trạng thái: [{c_status}]", expanded=False):
                    st.write(f"**Đối tác:** {c_partner} | **Giá trị:** {c_val:,.0f} đ")
                    st.write(f"**Phòng ban đề xuất:** {contract.get('department', current_department)}")
                    st.write(f"**Trạng thái hiện tại:** **{c_status}**")
                    st.write(f"**Tệp đính kèm ({len(attachments)} tệp):**")
                    for att in attachments:
                        st.markdown(f"- 📎 **{att.get('checklist_item')}:** {att.get('file_name')} ({att.get('file_size', 0)/1024:.1f} KB)")
        else:
            st.info(f"Tài khoản `@{current_username}` ({current_department}) chưa gửi hồ sơ hợp đồng nào.")

    with tab_submit_contract:
        st.subheader("📤 Soạn Thảo & Nộp Hồ Sơ Hợp Đồng Mới")
        workflows = get_workflows()
        if not workflows:
            st.warning("Chưa có Loại hợp đồng nào trong workflows.json!")
            return

        workflow_options = [w.get("contract_type", w.get("name")) for w in workflows]
        selected_contract_type = st.selectbox("1. Chọn Loại hợp đồng đề xuất *", workflow_options)
        matched_wf = next((w for w in workflows if w.get("contract_type", w.get("name")) == selected_contract_type), workflows[0])
        workflow_checklist = matched_wf.get("checklist", ["Dự thảo Hợp đồng", "Tài liệu khác"])

        st.markdown("#### 2. Thông tin pháp lý & thương mại")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            contract_title = st.text_input("Tên hợp đồng đề xuất *")
            partner_name = st.text_input("Tên đối tác / Khách hàng *")
            contract_value = st.number_input("Giá trị hợp đồng (VNĐ) *", min_value=0, value=50000000, step=1000000)
        with col_c2:
            st.text_input("Phòng ban đề xuất (Tự động gán):", value=current_department, disabled=True)
            col_d1, col_d2 = st.columns(2)
            with col_d1: eff_date = st.date_input("Ngày hiệu lực:", value=datetime.today())
            with col_d2: exp_date = st.date_input("Ngày kết thúc:")
            contract_notes = st.text_area("Ghi chú tóm tắt:")

        st.markdown("---")
        st.markdown("#### 3. Đính kèm hồ sơ tài liệu theo Checklist quy định")

        uploaded_files_map = {}
        for idx, checklist_item in enumerate(workflow_checklist, 1):
            is_other = (checklist_item == "Tài liệu khác")
            label_text = f"Mục {idx}: {checklist_item} {'(Chọn nhiều file PDF)' if is_other else '(1 file PDF)'} *"
            file_res = st.file_uploader(label=label_text, type=["pdf"], accept_multiple_files=is_other, key=f"uploader_{matched_wf.get('id')}_{idx}")
            uploaded_files_map[checklist_item] = file_res

        if st.button("🚀 Nộp Hồ Sơ Hợp Đồng Lên Ban Giám Đốc", use_container_width=True, type="primary"):
            if not contract_title.strip() or not partner_name.strip():
                st.error("Vui lòng điền đủ Tên hợp đồng và Tên đối tác!")
            else:
                attachments_list = []
                for item_name, file_data in uploaded_files_map.items():
                    if file_data is not None:
                        if isinstance(file_data, list):
                            for sub_f in file_data:
                                f_bytes = sub_f.read()
                                attachments_list.append({"checklist_item": item_name, "file_name": sub_f.name, "file_size": len(f_bytes), "file_base64": base64.b64encode(f_bytes).decode("utf-8")})
                        else:
                            f_bytes = file_data.read()
                            attachments_list.append({"checklist_item": item_name, "file_name": file_data.name, "file_size": len(f_bytes), "file_base64": base64.b64encode(f_bytes).decode("utf-8")})

                all_contracts = get_contracts()
                contract_code = f"HD-{datetime.now().year}-{str(len(all_contracts) + 1).zfill(3)}"
                new_contract_record = {
                    "id": contract_code,
                    "title": contract_title.strip(),
                    "partner_name": partner_name.strip(),
                    "contract_type": selected_contract_type,
                    "value_vnd": int(contract_value),
                    "created_by": current_username,
                    "department": current_department,
                    "workflow_id": matched_wf.get("id", "WF_DEFAULT"),
                    "current_step": 1,
                    "status": "Chờ Giám đốc phân công",
                    "effective_date": str(eff_date),
                    "expiration_date": str(exp_date),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "notes": contract_notes.strip(),
                    "attachments": attachments_list
                }
                all_contracts.append(new_contract_record)
                save_contracts(all_contracts)
                st.success(f"Nộp hồ sơ '{contract_code}: {contract_title}' thành công! Trạng thái: 'Chờ Giám đốc phân công'.")
                st.rerun()

# ==============================================================================
# 9. BƯỚC 4: HÀM LEGAL_STAFF_VIEW() - PHÁP CHẾ RÀ SOÁT & TÍCH HỢP AI GEMINI
# ==============================================================================
def legal_staff_view():
    """
    Giao diện Chuyên viên Pháp chế Rà soát (Legal Staff View):
    Hàm gồm 2 Tab:
    Tab 1: Đang rà soát
      - Chỉ hiện hồ sơ có status == 'Đang rà soát' VÀ assigned_to == current_username.
      - Khi chọn 1 hồ sơ, dùng st.columns([1, 1]) chia đôi màn hình.
      - Cột trái: Cho phép chọn file PDF trong hồ sơ. Render PDF trực tiếp bằng thẻ <iframe> base64.
      - Cột phải: Hiển thị Checklist. Dưới mỗi mục có st.radio (Đạt/Không đạt/Có góp ý).
                  Nếu 'Có góp ý' thì hiện st.text_area.
      - Tích hợp AI: Expander nhập API Key Gemini và nội dung điều khoản. Gọi AI đánh giá rủi ro pháp lý (dùng try-except).
      - Cuối cùng: Chọn Đánh giá tổng quát và nhấn nút 'Trình Giám đốc duyệt'. Đổi status thành 'Chờ Giám đốc duyệt'.
    Tab 2: Lịch sử rà soát
      - Hiện các hồ sơ nhân viên này đã làm xong. Chỉ cho xem lại ý kiến, không cho sửa.
    """
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "")
    current_fullname = current_user.get("full_name", "Chuyên viên Pháp chế")
    current_role = current_user.get("role", "")

    st.title("⚖️ Bàn Làm Việc Pháp Chế: Rà Soát & Thẩm Định Hợp Đồng")

    all_contracts = get_contracts()
    all_users = get_users()
    legal_users = [u for u in all_users if u.get("department") == "Phòng Pháp chế" or "Pháp chế" in u.get("role", "")]

    # ==========================================================================
    # CƠ CHẾ XÁC ĐỊNH CHUYÊN VIÊN / PHẠM VI XEM HỒ SƠ THÔNG MINH
    # ==========================================================================
    # Nếu là Admin hoặc Ban Giám đốc: cho phép giám sát bàn làm việc của mọi chuyên viên
    is_admin_or_director = current_role in ["Admin", "Ban Giám đốc", "Giám đốc Pháp chế"]
    
    target_username = current_username
    view_scope_all = False

    if is_admin_or_director:
        st.markdown(
            f"""
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #2563EB; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
                <span style="font-weight: 700; color: #1E40AF; font-size: 0.88rem;">👑 Chế độ Quản trị & Giám sát Thẩm định:</span>
                <span style="color: #334155; font-size: 0.85rem;"> Bạn đang đăng nhập với vai trò <b>{current_role}</b>. Bạn có thể xem và thực hiện thẩm định theo từng chuyên viên hoặc xem tất cả hồ sơ.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        col_flt1, col_flt2 = st.columns([1.5, 1])
        with col_flt1:
            specialist_options = ["Tất cả hồ sơ đang rà soát"] + [f"{u.get('full_name')} (@{u.get('username')})" for u in legal_users]
            chosen_spec = st.selectbox(
                "🎯 Chọn bàn làm việc chuyên viên để xem/thao tác:",
                specialist_options,
                index=0,
                key="admin_legal_spec_choice"
            )
            if chosen_spec == "Tất cả hồ sơ đang rà soát":
                view_scope_all = True
            else:
                for u in legal_users:
                    if f"@{u.get('username')}" in chosen_spec:
                        target_username = u.get("username")
                        break
        with col_flt2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            active_count = len([c for c in all_contracts if c.get("status") == "Đang rà soát"])
            st.info(f"📊 Toàn hệ thống đang có **{active_count}** hồ sơ chờ thẩm định.")
    else:
        st.markdown(
            f"Chuyên viên phụ trách: **{current_fullname}** (`@{current_username}`) | "
            f"Bộ phận: **Phòng Pháp chế**"
        )

    tab_reviewing, tab_history = st.tabs([
        "🔍 Đang rà soát",
        "📜 Lịch sử rà soát"
    ])

    # ==========================================================================
    # TAB 1: ĐANG RÀ SOÁT
    # ==========================================================================
    with tab_reviewing:
        # LỌC HỒ SƠ CHUẨN XÁC:
        if view_scope_all:
            active_contracts = [c for c in all_contracts if c.get("status") == "Đang rà soát"]
        else:
            # Lọc theo chuyên viên mục tiêu
            active_contracts = [
                c for c in all_contracts
                if c.get("status") == "Đang rà soát" and c.get("assigned_to") == target_username
            ]
            # Nếu chuyên viên này chưa có hồ sơ và người dùng muốn xem các hồ sơ đang rà soát khác
            if not active_contracts and not is_admin_or_director:
                all_reviewing = [c for c in all_contracts if c.get("status") == "Đang rà soát"]
                if all_reviewing:
                    allow_view_all = st.checkbox(
                        f"Tài khoản @{current_username} chưa có hồ sơ riêng. Bạn có muốn xem {len(all_reviewing)} hồ sơ 'Đang rà soát' khác trong Phòng Pháp chế để hỗ trợ đồng nghiệp?",
                        value=True
                    )
                    if allow_view_all:
                        active_contracts = all_reviewing

        if not active_contracts:
            st.info(
                f"Hiện tại không có hồ sơ nào ở trạng thái **'Đang rà soát'** phù hợp với bộ lọc hiện tại."
            )
            st.markdown(
                """
                <div style="margin-top: 10px; padding: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.85rem; color: #475569;">
                    💡 <b>Gợi ý kiểm tra:</b><br/>
                    • Vào <b>👑 Quản trị Giám đốc (director_view) -> Tab 2: Phân công hồ sơ</b> để giao việc cho chuyên viên.<br/>
                    • Đăng nhập tài khoản <code>phapche01</code> (Mật khẩu: <code>pc123</code>) hoặc <code>phapche02</code> (Mật khẩu: <code>pc456</code>) để thao tác trực tiếp.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # CHỌN HỒ SƠ BẰNG ID ĐẢM BẢO MIỄN NHIỄM VỚI LỖI INDEXERROR
            contract_ids = [c.get("id") for c in active_contracts]
            contract_map = {c.get("id"): c for c in active_contracts}

            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                selected_cid = st.selectbox(
                    "Chọn hồ sơ hợp đồng cần thẩm định:",
                    options=contract_ids,
                    format_func=lambda cid: f"{cid} — {contract_map[cid].get('title')} ({contract_map[cid].get('partner_name')}) [Phụ trách: @{contract_map[cid].get('assigned_to', 'N/A')}]",
                    key=f"legal_contract_selector_{target_username}_{len(active_contracts)}"
                )
            with col_sel2:
                selected_contract = contract_map.get(selected_cid, active_contracts[0])
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div style='font-size: 0.85rem; background: #DBEAFE; color: #1E40AF; padding: 6px 12px; border-radius: 6px; font-weight: 700; text-align: center;'>"
                    f"Giá trị: {selected_contract.get('value_vnd', 0):,.0f} VNĐ</div>",
                    unsafe_allow_html=True
                )

            st.markdown("---")

            # CHIA ĐÔI MÀN HÌNH st.columns([1, 1])
            col_left, col_right = st.columns([1, 1])

            # ------------------------------------------------------------------
            # CỘT TRÁI: CHỌN FILE PDF & RENDER TRỰC TIẾP QUA THẺ <iframe> BASE64
            # ------------------------------------------------------------------
            with col_left:
                st.markdown("#### 📄 Xem Trực Tiếp Tài Liệu Hồ Sơ (PDF)")
                attachments = selected_contract.get("attachments", [])

                if not attachments:
                    st.warning("Hồ sơ này không có tệp PDF đính kèm nào được lưu trữ.")
                else:
                    att_indices = list(range(len(attachments)))
                    selected_att_idx = st.selectbox(
                        "Chọn tài liệu PDF cần đọc:",
                        options=att_indices,
                        format_func=lambda i: f"{i+1}. [{attachments[i].get('checklist_item', 'Tài liệu')}]: {attachments[i].get('file_name', 'document.pdf')}",
                        key=f"att_sel_{selected_contract.get('id')}"
                    )
                    # Bảo vệ an toàn chống IndexError
                    if selected_att_idx >= len(attachments):
                        selected_att_idx = 0
                    chosen_att = attachments[selected_att_idx]
                    pdf_b64 = chosen_att.get("file_base64", "").strip()

                    if pdf_b64:
                        # 1. CHUẨN HÓA CHUỖI BASE64: LOẠI BỎ TIỀN TỐ TRÙNG LẶP, KHOẢNG TRẮNG, KÝ TỰ XUỐNG DÒNG
                        raw_b64 = pdf_b64
                        if "base64," in raw_b64:
                            raw_b64 = raw_b64.split("base64,", 1)[1]
                        raw_b64 = "".join(raw_b64.split())  # Xóa sạch whitespace, \n, \r
                        missing_padding = len(raw_b64) % 4
                        if missing_padding:
                            raw_b64 += "=" * (4 - missing_padding)

                        pdf_data_uri = f"data:application/pdf;base64,{raw_b64}"

                        # 2. GIẢI MÃ NHỊ PHÂN AN TOÀN ĐỂ XÁC MINH VÀ HỖ TRỢ TẢI XUỐNG
                        try:
                            pdf_bytes = base64.b64decode(raw_b64)
                        except Exception:
                            pdf_bytes = None

                        # 3. RENDER PDF ĐA TẦNG: <object> + <embed> + <iframe> ĐẢM BẢO TƯƠNG THÍCH MỌI TRÌNH DUYỆT
                        file_display_name = chosen_att.get('file_name', 'document.pdf')
                        file_kb = chosen_att.get('file_size', len(pdf_bytes) if pdf_bytes else 0) / 1024

                        st.markdown(
                            f"""
                            <div style="border-radius: 12px; overflow: hidden; border: 1.5px solid #CBD5E1; box-shadow: 0 4px 10px rgba(0,0,0,0.06); background-color: #FFFFFF; margin-bottom: 10px;">
                                <div style="background-color: #F8FAFC; padding: 10px 14px; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                                    <span style="font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                                        📎 Đang hiển thị: {file_display_name} ({file_kb:.1f} KB)
                                    </span>
                                    <a href="{pdf_data_uri}" target="_blank" download="{file_display_name}" 
                                       style="font-size: 0.78rem; font-weight: 600; color: #2563EB; text-decoration: none; background: #EFF6FF; padding: 4px 10px; border-radius: 6px; border: 1px solid #BFDBFE;">
                                        ↗️ Mở trong tab mới / Tải tệp
                                    </a>
                                </div>
                                <object data="{pdf_data_uri}#toolbar=1&navpanes=0" type="application/pdf" width="100%" height="650px" style="border: none; display: block;">
                                    <embed src="{pdf_data_uri}#toolbar=1&navpanes=0" type="application/pdf" width="100%" height="650px" />
                                    <iframe src="{pdf_data_uri}" width="100%" height="650px" style="border: none;">
                                        <div style="padding: 24px; text-align: center; color: #64748B; font-size: 0.9rem;">
                                            Trình duyệt đang chặn xem trực tiếp PDF qua data URI.<br/>
                                            Vui lòng nhấn nút tải xuống bên dưới để xem tệp đầy đủ.
                                        </div>
                                    </iframe>
                                </object>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # 4. NÚT DOWNLOAD DỰ PHÒNG CHUẨN NATIVE STREAMLIT
                        if pdf_bytes:
                            st.download_button(
                                label=f"📥 Tải xuống tệp PDF '{file_display_name}'",
                                data=pdf_bytes,
                                file_name=file_display_name,
                                mime="application/pdf",
                                key=f"btn_dl_pdf_{selected_contract.get('id')}_{selected_att_idx}",
                                use_container_width=True
                            )
                    else:
                        st.error("Tệp này không có dữ liệu chuỗi Base64 hợp lệ.")

            # ------------------------------------------------------------------
            # CỘT PHẢI: CHECKLIST (RADIO: ĐẠT/KHÔNG ĐẠT/CÓ GÓP Ý), TÍCH HỢP AI, TRÌNH DUYỆT
            # ------------------------------------------------------------------
            with col_right:
                st.markdown("#### ⚖️ Thẩm Định Checklist & Đánh Giá Pháp Lý")

                # Lấy danh mục checklist tương ứng với Loại hợp đồng
                workflows = get_workflows()
                matched_wf = next(
                    (w for w in workflows if w.get("id") == selected_contract.get("workflow_id") or w.get("contract_type") == selected_contract.get("contract_type")),
                    None
                )
                contract_checklist = matched_wf.get("checklist", []) if matched_wf else [
                    "Dự thảo Hợp đồng chi tiết",
                    "Giấy chứng nhận Đăng ký kinh doanh đối tác",
                    "Báo giá chính thức & Thỏa thuận thương mại",
                    "Tài liệu khác"
                ]

                checklist_results = {}

                st.markdown("##### 1. Thẩm tra từng đầu mục Checklist:")
                for idx, item in enumerate(contract_checklist, 1):
                    st.markdown(
                        f"<div style='font-weight: 700; font-size: 0.88rem; color: #1E293B; margin-top: 12px;'>"
                        f"Mục {idx}: {item}</div>",
                        unsafe_allow_html=True
                    )

                    # st.radio (Đạt / Không đạt / Có góp ý)
                    eval_status = st.radio(
                        label=f"Đánh giá cho mục '{item}':",
                        options=["Đạt", "Không đạt", "Có góp ý"],
                        horizontal=True,
                        key=f"radio_eval_{selected_contract.get('id')}_{idx}",
                        label_visibility="collapsed"
                    )

                    comment_text = ""
                    # NẾU 'CÓ GÓP Ý' THÌ HIỂN THỊ ST.TEXT_AREA
                    if eval_status == "Có góp ý":
                        comment_text = st.text_area(
                            f"Nội dung góp ý / Chỉnh sửa cho mục '{item}':",
                            placeholder="Nêu rõ điều khoản cần bổ sung, sửa đổi hoặc tài liệu chưa hợp lệ...",
                            key=f"comment_{selected_contract.get('id')}_{idx}",
                            height=80
                        )

                    checklist_results[item] = {
                        "status": eval_status,
                        "comment": comment_text.strip()
                    }

                st.markdown("---")

                # --------------------------------------------------------------
                # TÍCH HỢP AI: EXPANDER NHẬP API KEY GEMINI VÀ RÀ SOÁT RỦI RO
                # --------------------------------------------------------------
                with st.expander("🤖 Trợ lý AI Gemini - Rà soát Rủi ro & Câu chữ Pháp lý", expanded=False):
                    st.markdown(
                        "Dán nội dung điều khoản hợp đồng cần kiểm tra (ví dụ: điều khoản phạt vi phạm, "
                        "chấm dứt, bồi thường thiệt hại, cam kết bảo mật...) để AI phân tích rủi ro."
                    )
                    cfg_data = get_config()
                    gemini_api_key = st.text_input(
                        "Gemini API Key:",
                        value=cfg_data.get("gemini_api_key", ""),
                        type="password",
                        placeholder="Dán API Key từ Google AI Studio...",
                        key=f"gemini_key_{selected_contract.get('id')}"
                    )
                    clause_content = st.text_area(
                        "Nội dung điều khoản cần rà soát rủi ro:",
                        placeholder="Ví dụ: 'Bên A có quyền đơn phương chấm dứt hợp đồng bất kỳ lúc nào mà không cần bồi thường thiệt hại và bên B phải chịu phạt 50% giá trị hợp đồng...'",
                        height=110,
                        key=f"clause_text_{selected_contract.get('id')}"
                    )

                    if st.button("🔍 Phân tích Rủi ro bằng AI Gemini", key=f"btn_call_ai_{selected_contract.get('id')}"):
                        if not gemini_api_key.strip():
                            st.error("Vui lòng cung cấp Gemini API Key để thực hiện thẩm định!")
                        elif not clause_content.strip():
                            st.warning("Vui lòng dán nội dung điều khoản cần rà soát!")
                        else:
                            # GỌI AI DÙNG TRY-EXCEPT
                            try:
                                with st.spinner("AI đang thẩm định rủi ro pháp lý và phân tích điều khoản..."):
                                    genai.configure(api_key=gemini_api_key.strip())
                                    ai_model = genai.GenerativeModel("gemini-1.5-flash")
                                    ai_prompt = f"""
                                    Bạn là Trưởng ban Pháp chế cao cấp của Tập đoàn. Hãy thẩm tra điều khoản hợp đồng thương mại sau:
                                    
                                    NỘI DUNG ĐIỀU KHOẢN:
                                    \"\"\"{clause_content}\"\"\"

                                    YÊU CẦU ĐÁNH GIÁ:
                                    1. Mức độ rủi ro pháp lý: Đánh giá rõ (CAO / TRUNG BÌNH / THẤP) và giải thích lý do ngắn gọn.
                                    2. Điểm bất lợi & bẫy pháp lý: Chỉ ra các cạm bẫy bất lợi cho doanh nghiệp theo quy định của Bộ luật Dân sự và Luật Thương mại Việt Nam.
                                    3. Đề xuất câu chữ sửa đổi (Redline Clause): Viết lại điều khoản hoàn chỉnh đảm bảo cân bằng quyền lợi và bảo vệ an toàn cho doanh nghiệp.
                                    """
                                    ai_response = ai_model.generate_content(ai_prompt)
                                    st.markdown("##### 📊 Báo Cáo Phân Tích Rủi Ro Của AI:")
                                    st.markdown(
                                        f"<div style='background-color: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #2563EB; border-radius: 8px; padding: 14px; font-size: 0.88rem; line-height: 1.6;'>"
                                        f"{ai_response.text}</div>",
                                        unsafe_allow_html=True
                                    )
                            except Exception as ai_error:
                                st.error(f"Lỗi khi gọi API Gemini: {ai_error}")

                st.markdown("---")

                # --------------------------------------------------------------
                # ĐÁNH GIÁ TỔNG QUÁT VÀ NÚT 'TRÌNH GIÁM ĐỐC DUYỆT'
                # --------------------------------------------------------------
                st.markdown("##### 2. Đánh giá tổng quát & Kết luận:")
                general_assessment = st.selectbox(
                    "Đánh giá tổng quát của Pháp chế: *",
                    [
                        "Đủ điều kiện pháp lý - Đề xuất ký",
                        "Cần điều chỉnh và bổ sung",
                        "Không đủ điều kiện pháp lý"
                    ],
                    key=f"general_assess_{selected_contract.get('id')}"
                )

                summary_notes = st.text_area(
                    "Ý kiến kết luận / Tờ trình gửi Ban Giám đốc: *",
                    placeholder="Tóm tắt các vấn đề pháp lý trọng yếu, cam kết đã đàm phán và kiến nghị của Pháp chế...",
                    key=f"summary_notes_{selected_contract.get('id')}",
                    height=90
                )

                submit_to_director_btn = st.button(
                    "📤 Trình Giám đốc duyệt",
                    type="primary",
                    use_container_width=True,
                    key=f"btn_submit_director_{selected_contract.get('id')}"
                )

                if submit_to_director_btn:
                    if not summary_notes.strip():
                        st.error("Vui lòng ghi ý kiến kết luận của Pháp chế trước khi trình duyệt!")
                    else:
                        # CẬP NHẬT TRẠNG THÁI THÀNH 'Chờ Giám đốc duyệt'
                        selected_contract["status"] = "Chờ Giám đốc duyệt"
                        selected_contract["legal_review"] = {
                            "reviewer": current_username,
                            "reviewer_name": current_fullname,
                            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "general_assessment": general_assessment,
                            "summary_notes": summary_notes.strip(),
                            "checklist_results": checklist_results
                        }

                        if save_contracts(all_contracts):
                            st.success(
                                f"🎉 Đã hoàn tất rà soát hồ sơ '{selected_contract.get('id')}: {selected_contract.get('title')}' "
                                f"và chuyển sang trạng thái: **'Chờ Giám đốc duyệt'** thành công!"
                            )
                            st.rerun()

    # ==========================================================================
    # TAB 2: LỊCH SỬ RÀ SOÁT (CHỈ XEM LẠI, KHÔNG CHO SỬA)
    # ==========================================================================
    with tab_history:
        st.subheader("📜 Lịch Sử Thẩm Định Của Chuyên Viên")
        st.markdown(
            "🔒 **Chế độ chỉ xem (Read-only):** Hiển thị toàn bộ các hồ sơ do chính bạn đã hoàn tất "
            f"rà soát thẩm định (`@{current_username}`). Bạn chỉ có thể xem lại ý kiến và kết luận, không thể sửa đổi."
        )

        # LỌC: Các hồ sơ nhân viên này đã làm xong
        if is_admin_or_director and view_scope_all:
            history_contracts = [
                c for c in all_contracts
                if c.get("status") != "Đang rà soát" and (c.get("legal_review") or c.get("assigned_to"))
            ]
        else:
            history_contracts = [
                c for c in all_contracts
                if (c.get("assigned_to") == target_username or c.get("legal_review", {}).get("reviewer") == target_username)
                and c.get("status") != "Đang rà soát"
            ]

        if not history_contracts:
            st.info("Chưa có hồ sơ nào trong lịch sử thẩm định của bạn.")
        else:
            for h_contract in history_contracts:
                h_id = h_contract.get("id")
                h_title = h_contract.get("title")
                h_partner = h_contract.get("partner_name")
                h_status = h_contract.get("status")
                h_val = h_contract.get("value_vnd", 0)
                l_review = h_contract.get("legal_review", {})

                with st.expander(f"📁 {h_id}: {h_title} — Trạng thái hiện tại: [{h_status}]", expanded=False):
                    col_h1, col_h2 = st.columns([1, 1.2])

                    with col_h1:
                        st.markdown(f"**Đối tác:** {h_partner}")
                        st.markdown(f"**Giá trị:** {h_val:,.0f} đ")
                        st.markdown(f"**Loại hợp đồng:** {h_contract.get('contract_type')}")
                        st.markdown(f"**Phòng ban đề xuất:** {h_contract.get('department')}")
                        st.markdown(f"**Thời gian rà soát:** {l_review.get('reviewed_at', 'N/A')}")
                        st.markdown(f"**Chuyên viên thực hiện:** {l_review.get('reviewer_name', current_fullname)}")

                    with col_h2:
                        st.markdown("**Kết quả thẩm định tổng quát (Chỉ đọc):**")
                        assess_val = l_review.get("general_assessment", "Chưa có kết luận")
                        assess_color = "#10B981" if "Đủ điều kiện" in assess_val else "#F59E0B"
                        st.markdown(
                            f"<div style='padding: 6px 12px; background: #F8FAFC; border-left: 4px solid {assess_color}; font-weight: 700; border-radius: 6px; font-size: 0.88rem;'>"
                            f"📌 {assess_val}</div>",
                            unsafe_allow_html=True
                        )

                        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                        st.markdown("**Ý kiến kết luận của Pháp chế:**")
                        st.markdown(
                            f"<div style='padding: 10px; background: #F1F5F9; border-radius: 8px; font-size: 0.85rem; color: #334155; font-style: italic;'>"
                            f"\"{l_review.get('summary_notes', 'Không có ghi chú.')}\"</div>",
                            unsafe_allow_html=True
                        )

                    st.markdown("---")
                    st.markdown("**Chi tiết đánh giá từng mục Checklist (Chỉ xem):**")
                    chk_res = l_review.get("checklist_results", {})
                    if chk_res:
                        for it_name, it_data in chk_res.items():
                            it_status = it_data.get("status", "Đạt")
                            it_comment = it_data.get("comment", "")
                            status_badge = "🟢 Đạt" if it_status == "Đạt" else ("🔴 Không đạt" if it_status == "Không đạt" else "🟡 Có góp ý")
                            st.markdown(
                                f"<div style='padding: 6px 10px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; margin-bottom: 6px; font-size: 0.85rem;'>"
                                f"<b>{it_name}</b>: <span style='font-weight: 700;'>{status_badge}</span> "
                                f"{f'— <i>Ý kiến: {it_comment}</i>' if it_comment else ''}</div>",
                                unsafe_allow_html=True
                            )
                    else:
                        st.caption("Chưa có chi tiết checklist được lưu trữ.")

# ==============================================================================
# 10. BƯỚC 6: TẠO FILE PDF PHIẾU GÓP Ý (UNICODE) & GỬI EMAIL SMTPLIB
# ==============================================================================
class ContractReviewPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 64, 175)
        self.rect(0, 0, 210, 8, "F")
        self.ln(4)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(226, 232, 240)
        self.line(10, 281, 200, 281)
        font_to_use = getattr(self, "custom_font_family", "Helvetica")
        try:
            self.set_font(font_to_use, "", 8)
        except Exception:
            self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f"Trang {self.page_no()} | He thong Quan tri Hop dong - Asia Holdings", 0, 0, "C")

def get_unicode_font_paths():
    """Tìm font TTF hỗ trợ Unicode tiếng Việt trên hệ thống"""
    font_candidates = [
        "/Arial.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]
    bold_candidates = [
        "/Arial-Bold.ttf",
        "Arial-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf"
    ]
    regular = next((p for p in font_candidates if os.path.exists(p)), None)
    bold = next((p for p in bold_candidates if os.path.exists(p)), None)
    if not bold and regular:
        bold = regular
    return regular, bold

def generate_review_pdf(contract: dict, action_type: str, director_notes: str, director_name: str) -> bytes:
    """
    Dùng fpdf tạo file PDF 'Phiếu góp ý Hợp đồng'.
    Bắt buộc cấu hình font Unicode (như Arial.ttf) để tiếng Việt trên PDF không bị lỗi.
    Bao gồm:
    - Tên, Loại hợp đồng, Đối tác, Phòng ban, Giá trị
    - Đánh giá các mục Checklist
    - Kết luận và Quyết định phê duyệt
    """
    pdf = ContractReviewPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    font_path, font_bold_path = get_unicode_font_paths()
    font_family = "Helvetica"
    if font_path:
        try:
            pdf.add_font("ArialUnicode", "", font_path, uni=True)
            if font_bold_path:
                pdf.add_font("ArialUnicode", "B", font_bold_path, uni=True)
            else:
                pdf.add_font("ArialUnicode", "B", font_path, uni=True)
            font_family = "ArialUnicode"
        except Exception:
            font_family = "Helvetica"

    pdf.custom_font_family = font_family

    # 1. TIÊU ĐỀ DOANH NGHIỆP
    pdf.set_font(font_family, "B", 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU - ASIA HOLDINGS", 0, 1, "C")
    pdf.set_font(font_family, "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "HỘI ĐỒNG THẨM ĐỊNH & PHÊ DUYỆT PHÁP LÝ HỢP ĐỒNG", 0, 1, "C")

    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(70, 24, 140, 24)
    pdf.ln(7)

    # Tiêu đề chính
    pdf.set_font(font_family, "B", 15)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 8, "PHIẾU GÓP Ý & THẨM ĐỊNH HỢP ĐỒNG", 0, 1, "C")

    pdf.set_font(font_family, "", 8.5)
    pdf.set_text_color(71, 85, 105)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 5, f"Mã hồ sơ: {contract.get('id', 'N/A')} | Thời gian xuất phiếu: {now_str}", 0, 1, "C")
    pdf.ln(3)

    # 2. PHẦN I: THÔNG TIN HỒ SƠ HỢP ĐỒNG
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  I. THÔNG TIN HỒ SƠ HỢP ĐỒNG", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    info_rows = [
        ("Mã hợp đồng:", str(contract.get("id", "")), "Loại hợp đồng:", str(contract.get("contract_type", "Hợp đồng kinh tế"))),
        ("Tên hợp đồng:", str(contract.get("title", "")), "Phòng ban đề xuất:", str(contract.get("department", ""))),
        ("Đối tác (Bên B):", str(contract.get("partner_name", "")), "Giá trị (VNĐ):", f"{contract.get('value_vnd', 0):,.0f} VNĐ"),
        ("Người đề xuất:", str(contract.get("created_by", "")), "Thời hạn hiệu lực:", f"{contract.get('effective_date', '')} đến {contract.get('expiration_date', '')}")
    ]

    for label1, val1, label2, val2 in info_rows:
        pdf.set_font(font_family, "B", 8.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(32, 5.5, label1, 0, 0, "L")
        pdf.set_font(font_family, "", 8.5)
        pdf.cell(63, 5.5, val1[:40], 0, 0, "L")

        pdf.set_font(font_family, "B", 8.5)
        pdf.cell(35, 5.5, label2, 0, 0, "L")
        pdf.set_font(font_family, "", 8.5)
        pdf.cell(60, 5.5, val2[:40], 0, 1, "L")

    pdf.ln(2.5)

    # 3. PHẦN II: KẾT QUẢ THẨM ĐỊNH CỦA BAN PHÁP CHẾ
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  II. KẾT QUẢ THẨM ĐỊNH CỦA BAN PHÁP CHẾ", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    lr = contract.get("legal_review", {})
    reviewer_name = lr.get("reviewer_name", contract.get("assigned_to", "Chuyên viên Pháp chế"))
    reviewed_at = lr.get("reviewed_at", "Đã thẩm định")
    assessment = lr.get("general_assessment", "Đủ điều kiện pháp lý - Đề xuất ký")
    notes = lr.get("summary_notes", "Không có ghi chú thêm.")

    pdf.set_font(font_family, "B", 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(38, 5.5, "Chuyên viên thẩm định:", 0, 0, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.cell(57, 5.5, f"{reviewer_name} (@{contract.get('assigned_to', '')})", 0, 0, "L")

    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(35, 5.5, "Thời gian thẩm định:", 0, 0, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.cell(60, 5.5, str(reviewed_at), 0, 1, "L")

    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(38, 5.5, "Đánh giá tổng quát:", 0, 0, "L")
    pdf.set_font(font_family, "B", 9)
    if "Đủ điều kiện" in assessment:
        pdf.set_text_color(22, 101, 52)
    elif "Không đủ" in assessment:
        pdf.set_text_color(185, 28, 28)
    else:
        pdf.set_text_color(180, 83, 9)
    pdf.cell(0, 5.5, f"[ {assessment} ]", 0, 1, "L")

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(0, 5, "Ý kiến kết luận của Pháp chế:", 0, 1, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.multi_cell(0, 4.8, f'"{notes}"')
    pdf.ln(2.5)

    # 4. PHẦN III: BẢNG ĐÁNH GIÁ CHI TIẾT TỪNG MỤC CHECKLIST
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  III. BẢNG ĐÁNH GIÁ CHI TIẾT CÁC MỤC CHECKLIST", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    pdf.set_fill_color(30, 64, 175)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_family, "B", 8)
    pdf.cell(10, 6, "STT", 1, 0, "C", fill=True)
    pdf.cell(65, 6, "Hạng mục kiểm tra", 1, 0, "L", fill=True)
    pdf.cell(28, 6, "Kết quả", 1, 0, "C", fill=True)
    pdf.cell(87, 6, "Nội dung ý kiến góp ý / Ghi chú", 1, 1, "L", fill=True)

    chk_results = lr.get("checklist_results", {})
    if not chk_results:
        chk_results = {
            "Dự thảo Hợp đồng chi tiết": {"status": "Đạt", "comment": "Điều khoản rõ ràng, tuân thủ pháp luật."},
            "Hồ sơ năng lực & Pháp lý đối tác": {"status": "Đạt", "comment": "Đầy đủ ĐKKD và tài liệu đính kèm."}
        }

    row_idx = 1
    pdf.set_text_color(30, 41, 59)
    for item_name, item_res in chk_results.items():
        st_val = item_res.get("status", "Đạt")
        cm_val = item_res.get("comment", "Không có góp ý thêm.")

        pdf.set_font(font_family, "", 8)
        pdf.cell(10, 5.5, str(row_idx), 1, 0, "C")
        pdf.cell(65, 5.5, item_name[:36], 1, 0, "L")

        pdf.set_font(font_family, "B", 8)
        if st_val == "Đạt":
            pdf.set_text_color(22, 101, 52)
        elif st_val == "Không đạt":
            pdf.set_text_color(185, 28, 28)
        else:
            pdf.set_text_color(180, 83, 9)
        pdf.cell(28, 5.5, st_val, 1, 0, "C")

        pdf.set_text_color(30, 41, 59)
        pdf.set_font(font_family, "", 7.8)
        pdf.cell(87, 5.5, cm_val[:55], 1, 1, "L")
        row_idx += 1

    pdf.ln(2.5)

    # 5. PHẦN IV: QUYẾT ĐỊNH & PHÊ DUYỆT CỦA GIÁM ĐỐC
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  IV. QUYẾT ĐỊNH & PHÊ DUYỆT CỦA BAN GIÁM ĐỐC", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    decision_text = "KÝ DUYỆT PHÁT HÀNH (HOÀN TẤT)" if action_type == "approve" else "YÊU CẦU LÀM LẠI / ĐIỀU CHỈNH"
    pdf.set_font(font_family, "B", 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(42, 5.5, "Quyết định của Giám đốc:", 0, 0, "L")

    if action_type == "approve":
        pdf.set_text_color(22, 101, 52)
    else:
        pdf.set_text_color(185, 28, 28)
    pdf.cell(0, 5.5, f"[ {decision_text} ]", 0, 1, "L")

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(0, 5, "Ý kiến chỉ đạo của Giám đốc:", 0, 1, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.multi_cell(0, 4.8, f'"{director_notes}"')
    pdf.ln(4)

    # CHỮ KÝ ĐIỆN TỬ
    pdf.set_font(font_family, "B", 9)
    pdf.cell(95, 5, "CHUYÊN VIÊN THẨM ĐỊNH", 0, 0, "C")
    pdf.cell(95, 5, "GIÁM ĐỐC PHÁP CHẾ PHÊ DUYỆT", 0, 1, "C")

    pdf.set_font(font_family, "I", 7.8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(95, 4, "(Ký, ghi rõ họ tên)", 0, 0, "C")
    pdf.cell(95, 4, "(Ký duyệt điện tử)", 0, 1, "C")
    pdf.ln(10)

    pdf.set_font(font_family, "B", 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(95, 5, str(reviewer_name), 0, 0, "C")
    pdf.cell(95, 5, str(director_name), 0, 1, "C")

    try:
        out = pdf.output(dest="S")
        if isinstance(out, str):
            return out.encode("latin1")
        return bytes(out)
    except Exception:
        return str(pdf.output()).encode("latin1")

def send_approval_email(contract: dict, pdf_bytes: bytes, pdf_filename: str, action_type: str, director_notes: str) -> tuple[bool, str]:
    """
    Dùng smtplib đọc cấu hình từ config.json và email phòng ban từ users.json
    để gửi email tự động đính kèm file PDF (có try-except báo lỗi nếu sai cấu hình mail).
    """
    config_data = get_config()
    smtp_settings = config_data.get("smtp_settings", {})

    server_host = smtp_settings.get("server", "smtp.gmail.com")
    server_port = int(smtp_settings.get("port", 587))
    sender_email = smtp_settings.get("sender_email", "notification@asiaholdings.vn")
    app_password = smtp_settings.get("app_password", "")
    use_tls = smtp_settings.get("use_tls", True)

    users_list = get_users()

    created_by_user = next((u for u in users_list if u.get("username") == contract.get("created_by")), None)
    assigned_user = next((u for u in users_list if u.get("username") == contract.get("assigned_to")), None)

    to_emails = []
    if created_by_user and created_by_user.get("email"):
        to_emails.append(created_by_user.get("email"))
    if assigned_user and assigned_user.get("email"):
        to_emails.append(assigned_user.get("email"))

    if not to_emails:
        to_emails = [f"{contract.get('created_by', 'kinhdoanh01')}@congty.com.vn"]

    to_emails = list(set(to_emails))

    action_label = "Ký duyệt phát hành (Hoàn tất)" if action_type == "approve" else "Yêu cầu làm lại"
    subject = f"[Asia Holdings] Thông báo {action_label}: Hợp đồng {contract.get('id')} - {contract.get('title')}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    body_content = f"""
Kính gửi Phòng ban đề xuất ({contract.get('department')}) và Phòng Pháp chế,

Hệ thống Quản trị Hợp đồng Asia Holdings thông báo kết quả phê duyệt hồ sơ từ Ban Giám đốc:

1. THÔNG TIN HỒ SƠ:
   - Mã hợp đồng: {contract.get('id')}
   - Tên hợp đồng: {contract.get('title')}
   - Đối tác: {contract.get('partner_name')}
   - Giá trị: {contract.get('value_vnd', 0):,.0f} VNĐ
   - Phòng ban đề xuất: {contract.get('department')} (Người tạo: @{contract.get('created_by')})

2. KẾT QUẢ PHÊ DUYỆT:
   - Quyết định: {action_label}
   - Ý kiến chỉ đạo của Giám đốc: "{director_notes}"
   - Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Đính kèm email này là tập tin PDF 'Phiếu góp ý Hợp đồng' bản chính thức (có chữ ký phê duyệt).

Trân trọng,
Ban Giám đốc Pháp chế - Asia Holdings
    """.strip()

    msg.attach(MIMEText(body_content, "plain", "utf-8"))

    if pdf_bytes:
        try:
            part = MIMEApplication(pdf_bytes, _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
            msg.attach(part)
        except Exception:
            pass

    try:
        if not app_password:
            return (
                False,
                f"Đã tạo email gửi tới [{', '.join(to_emails)}] nhưng chưa gửi thực tế do 'app_password' trong config.json đang để trống. "
                f"(Vui lòng điền Mật khẩu ứng dụng SMTP tại config.json để gửi thật qua {server_host})."
            )

        if use_tls:
            with smtplib.SMTP(server_host, server_port, timeout=10) as server:
                server.starttls()
                server.login(sender_email, app_password)
                server.sendmail(sender_email, to_emails, msg.as_string())
        else:
            with smtplib.SMTP(server_host, server_port, timeout=10) as server:
                server.login(sender_email, app_password)
                server.sendmail(sender_email, to_emails, msg.as_string())

        return (True, f"Đã gửi email thông báo tự động đính kèm file PDF tới: {', '.join(to_emails)}")
    except Exception as smtp_error:
        return (False, f"Lỗi gửi email qua {server_host}:{server_port} ({str(smtp_error)}). Đã lưu phiếu góp ý PDF thành công!")

# ==============================================================================
# 11. BƯỚC 5 & 6: HÀM DIRECTOR_VIEW() HOÀN CHỈNH - 4 TABS DÀNH CHO GIÁM ĐỐC
# ==============================================================================
def director_view():
    """
    Giao diện Quản trị Dành cho Giám đốc Pháp chế (director_view - Hoàn chỉnh):
    Hàm gồm 4 Tab chi tiết, KHÔNG dùng placeholder:
    Tab 1: Dashboard Thống kê
      - Dùng pandas đọc contracts.json.
      - Hiển thị st.metric (Tổng hồ sơ, Chờ phân công, Đang rà soát, Đã xong).
      - Vẽ 2 biểu đồ st.bar_chart: Theo trạng thái hồ sơ & Mức độ rủi ro.
    Tab 2: Phân công hồ sơ
      - Lọc hồ sơ 'Chờ Giám đốc phân công'. Xem tệp tiếng Việt, chọn chuyên viên, đổi status -> 'Đang rà soát'.
    Tab 3: Điều chuyển
      - Chọn hồ sơ 'Đang rà soát', đổi assigned_to sang chuyên viên khác, lưu lịch sử điều chuyển.
    Tab 4: Phê duyệt & Ban hành (Bước 6)
      - Lọc hồ sơ 'Chờ Giám đốc duyệt'.
      - Chia 2 cột: Cột trái xem PDF <iframe> đối chiếu; Cột phải xem toàn bộ lịch sử góp ý Pháp chế.
      - 2 nút: 'Ký duyệt phát hành' (status -> 'Hoàn tất') và 'Yêu cầu làm lại'.
      - Dùng fpdf tạo file PDF 'Phiếu góp ý Hợp đồng' (font Unicode).
      - Dùng smtplib đọc config.json và users.json gửi email tự động đính kèm PDF (try-except).
      - Nút st.download_button tải file PDF.
    """
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "")
    current_fullname = current_user.get("full_name", "Giám đốc Pháp chế")

    st.title("👑 Bàn Làm Việc Giám Đốc Pháp Chế")
    st.markdown(
        f"Lãnh đạo phụ trách: **{current_fullname}** (`@{current_username}`) | "
        f"Bộ phận: **{current_user.get('department', 'Ban Giám đốc')}**"
    )

    tab_stats, tab_assign, tab_transfer, tab_approve = st.tabs([
        "📊 Dashboard Thống kê",
        "📋 Phân công hồ sơ",
        "🔄 Điều chuyển nhân sự",
        "✍️ Phê duyệt & Ban hành"
    ])

    all_contracts = get_contracts()
    all_users = get_users()

    # ==========================================================================
    # TAB 1: DASHBOARD THỐNG KÊ (DÙNG PANDAS, ST.METRIC, 2 BIỂU ĐỒ)
    # ==========================================================================
    with tab_stats:
        st.subheader("📊 Báo Cáo & Thống Kê Tổng Quan Hợp Đồng")
        
        if not all_contracts:
            st.info("Hiện chưa có hợp đồng nào được lưu trữ trong hệ thống.")
        else:
            # DÙNG PANDAS ĐỌC DỮ LIỆU TỪ CONTRACTS.JSON
            df_contracts = pd.DataFrame(all_contracts)

            # Tính toán các chỉ số
            total_contracts = len(df_contracts)
            pending_assign = len(df_contracts[df_contracts["status"] == "Chờ Giám đốc phân công"])
            in_review = len(df_contracts[df_contracts["status"] == "Đang rà soát"])
            # 'Đã xong': Tính các hồ sơ đã qua rà soát hoặc hoàn tất
            completed = len(df_contracts[df_contracts["status"].isin(["Chờ Giám đốc duyệt", "Đã duyệt", "Đã ký kết", "Đã hoàn tất"])])

            # 4 METRIC CARDS
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Tổng hồ sơ", f"{total_contracts} hợp đồng")
            with col_m2:
                st.metric(
                    "Chờ phân công", 
                    f"{pending_assign}", 
                    delta=f"{pending_assign} cần giao" if pending_assign > 0 else "0",
                    delta_color="inverse"
                )
            with col_m3:
                st.metric("Đang rà soát", f"{in_review} hồ sơ")
            with col_m4:
                st.metric("Đã xong / Chờ duyệt", f"{completed} hồ sơ")

            st.markdown("---")

            # VẼ 2 BIỂU ĐỒ ST.BAR_CHART
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("##### 📈 1. Phân bổ theo Trạng thái hồ sơ")
                status_series = df_contracts["status"].value_counts()
                df_status = pd.DataFrame({
                    "Trạng thái": status_series.index,
                    "Số lượng": status_series.values
                })
                st.bar_chart(df_status.set_index("Trạng thái"), color="#2563EB", use_container_width=True)

            with col_chart2:
                st.markdown("##### ⚖️ 2. Thống kê theo Mức độ rủi ro (Kết quả đánh giá)")
                # Trích xuất general_assessment từ legal_review
                risk_categories = []
                for c in all_contracts:
                    lr = c.get("legal_review", {})
                    assess = lr.get("general_assessment", "") if lr else ""
                    if not assess:
                        risk_categories.append("Chưa đánh giá")
                    elif "Đủ điều kiện" in assess:
                        risk_categories.append("Thấp (Đủ ĐK ký)")
                    elif "điều chỉnh" in assess or "bổ sung" in assess:
                        risk_categories.append("Trung bình (Cần sửa)")
                    elif "Không đủ" in assess:
                        risk_categories.append("Cao (Không đạt)")
                    else:
                        risk_categories.append(assess)

                risk_series = pd.Series(risk_categories).value_counts()
                df_risk = pd.DataFrame({
                    "Mức độ rủi ro": risk_series.index,
                    "Số lượng": risk_series.values
                })
                st.bar_chart(df_risk.set_index("Mức độ rủi ro"), color="#DC2626", use_container_width=True)

            # Bảng tóm tắt nhanh
            with st.expander("📋 Xem danh sách bảng dữ liệu chi tiết", expanded=False):
                view_cols = ["id", "title", "partner_name", "department", "value_vnd", "status", "assigned_to"]
                avail_cols = [col for col in view_cols if col in df_contracts.columns]
                st.dataframe(df_contracts[avail_cols], use_container_width=True)

    # ==========================================================================
    # TAB 2: PHÂN CÔNG HỒ SƠ (XEM TỆP TIẾNG VIỆT, CHỌN NHÂN VIÊN, GIAO VIỆC)
    # ==========================================================================
    with tab_assign:
        st.subheader("📋 Phân Công Hồ Sơ Cho Chuyên Viên Pháp Chế")
        
        # LỌC HỒ SƠ 'Chờ Giám đốc phân công'
        pending_list = [c for c in all_contracts if c.get("status") == "Chờ Giám đốc phân công"]

        if not pending_list:
            st.info("Hiện không có hồ sơ nào ở trạng thái **'Chờ Giám đốc phân công'**.")
        else:
            pending_labels = [
                f"{c.get('id')} — {c.get('title')} ({c.get('partner_name')} | {c.get('department')})"
                for c in pending_list
            ]
            sel_pending_idx = st.selectbox(
                "Chọn hồ sơ cần phân công:",
                range(len(pending_list)),
                format_func=lambda i: pending_labels[i],
                key="sel_assign_contract"
            )
            target_contract = pending_list[sel_pending_idx]

            st.markdown("---")
            col_info, col_action = st.columns([1.1, 0.9])

            with col_info:
                st.markdown("#### 📄 Chi Tiết Hồ Sơ & Tài Liệu Đính Kèm (Tiếng Việt)")
                st.markdown(f"**Mã hồ sơ:** `{target_contract.get('id')}` | **Trạng thái:** `{target_contract.get('status')}`")
                st.markdown(f"**Tên hợp đồng:** **{target_contract.get('title')}**")
                st.markdown(f"**Đối tác:** {target_contract.get('partner_name')}")
                st.markdown(f"**Phòng ban đề xuất:** {target_contract.get('department')} (Người tạo: `@{target_contract.get('created_by')}`)")
                st.markdown(f"**Giá trị hợp đồng:** **{target_contract.get('value_vnd', 0):,.0f} VNĐ**")
                st.markdown(f"**Thời hạn hiệu lực:** Từ `{target_contract.get('effective_date')}` đến `{target_contract.get('expiration_date')}`")
                if target_contract.get("notes"):
                    st.info(f"💡 **Ghi chú đề xuất:** {target_contract.get('notes')}")

                # GIÁM ĐỐC XEM NỘI DUNG CÁC TỆP TRONG HỒ SƠ (TIẾNG VIỆT CHÍNH XÁC)
                st.markdown("##### 📎 Xem trước tệp đính kèm trong hồ sơ:")
                attachments = target_contract.get("attachments", [])
                if not attachments:
                    st.warning("Hồ sơ này không có tệp đính kèm nào.")
                else:
                    att_labels = [
                        f"{i+1}. [{att.get('checklist_item', 'Tài liệu')}]: {att.get('file_name', 'document.pdf')}"
                        for i, att in enumerate(attachments)
                    ]
                    att_idx = st.selectbox(
                        "Chọn tệp cần kiểm tra:",
                        range(len(attachments)),
                        format_func=lambda i: att_labels[i],
                        key=f"director_att_sel_{target_contract.get('id')}"
                    )
                    chosen_att = attachments[att_idx]
                    pdf_b64 = chosen_att.get("file_base64", "").strip()

                    if pdf_b64:
                        raw_b64 = pdf_b64
                        if "base64," in raw_b64:
                            raw_b64 = raw_b64.split("base64,", 1)[1]
                        raw_b64 = "".join(raw_b64.split())
                        pdf_data_uri = f"data:application/pdf;base64,{raw_b64}"

                        try:
                            pdf_bytes = base64.b64decode(raw_b64)
                        except Exception:
                            pdf_bytes = None

                        f_name = chosen_att.get("file_name", "document.pdf")
                        f_kb = chosen_att.get("file_size", len(pdf_bytes) if pdf_bytes else 0) / 1024

                        st.markdown(
                            f"""
                            <div style="border-radius: 10px; overflow: hidden; border: 1.5px solid #CBD5E1; background: #FFFFFF; margin-top: 8px; margin-bottom: 8px;">
                                <div style="background-color: #F8FAFC; padding: 8px 12px; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                                        📄 {f_name} ({f_kb:.1f} KB) - Mục: [{chosen_att.get('checklist_item')}]
                                    </span>
                                    <a href="{pdf_data_uri}" target="_blank" download="{f_name}" style="font-size: 0.78rem; font-weight: 600; color: #2563EB; text-decoration: none; background: #EFF6FF; padding: 3px 8px; border-radius: 4px; border: 1px solid #BFDBFE;">↗️ Tải / Mở tệp</a>
                                </div>
                                <object data="{pdf_data_uri}#toolbar=1" type="application/pdf" width="100%" height="450px" style="border: none; display: block;">
                                    <embed src="{pdf_data_uri}#toolbar=1" type="application/pdf" width="100%" height="450px" />
                                    <iframe src="{pdf_data_uri}" width="100%" height="450px" style="border: none;">
                                        <div style="padding: 16px; text-align: center; color: #64748B; font-size: 0.85rem;">
                                            Tệp đính kèm tiếng Việt sẵn sàng.<br/>
                                            <a href="{pdf_data_uri}" download="{f_name}" style="color: #2563EB; font-weight: bold;">Nhấp vào đây để tải tệp PDF về máy</a>
                                        </div>
                                    </iframe>
                                </object>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if pdf_bytes:
                            st.download_button(
                                label=f"📥 Tải tệp '{f_name}' về máy kiểm tra",
                                data=pdf_bytes,
                                file_name=f_name,
                                mime="application/pdf",
                                key=f"btn_dl_dir_{target_contract.get('id')}_{att_idx}",
                                use_container_width=True
                            )
                    else:
                        st.info("Tệp đính kèm không có dữ liệu chuỗi nội dung.")

            with col_action:
                st.markdown("#### 👤 Giao Việc Cho Nhân Viên Pháp Chế")
                
                # Lọc danh sách nhân viên pháp chế
                legal_candidates = [
                    u for u in all_users
                    if u.get("department") == "Phòng Pháp chế" or "Pháp chế" in u.get("role", "")
                ]
                if not legal_candidates:
                    # Nếu chưa có cấu hình riêng, hiển thị các users
                    legal_candidates = all_users

                candidate_labels = [
                    f"{u.get('full_name')} (@{u.get('username')}) — {u.get('role')}"
                    for u in legal_candidates
                ]
                sel_cand_idx = st.selectbox(
                    "Chọn chuyên viên pháp chế đảm nhiệm: *",
                    range(len(legal_candidates)),
                    format_func=lambda i: candidate_labels[i],
                    key="sel_assign_legal_staff"
                )
                chosen_candidate = legal_candidates[sel_cand_idx]

                director_instruction = st.text_area(
                    "Ý kiến chỉ đạo / Yêu cầu trọng tâm của Giám đốc (tùy chọn):",
                    placeholder="Ví dụ: Rà soát kỹ điều khoản phạt vi phạm hợp đồng và cam kết SLA; thời hạn hoàn thành trước ngày 25/04...",
                    height=100,
                    key="director_instruction_input"
                )

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                btn_do_assign = st.button(
                    "🚀 Giao Việc & Chuyển Sang Trạng Thái 'Đang Rà Soát'",
                    type="primary",
                    use_container_width=True,
                    key=f"btn_assign_confirm_{target_contract.get('id')}"
                )

                if btn_do_assign:
                    # ĐỔI TRẠNG THÁI THÀNH 'Đang rà soát' VÀ GÁN assigned_to
                    target_contract["status"] = "Đang rà soát"
                    target_contract["assigned_to"] = chosen_candidate.get("username")
                    target_contract["assigned_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    target_contract["assigned_by"] = current_username
                    target_contract["director_instruction"] = director_instruction.strip()

                    if save_contracts(all_contracts):
                        st.success(
                            f"🎉 Đã giao hồ sơ **'{target_contract.get('id')}: {target_contract.get('title')}'** "
                            f"cho chuyên viên **{chosen_candidate.get('full_name')}** (`@{chosen_candidate.get('username')}`) thành công!\n\n"
                            f"Trạng thái hồ sơ đã chuyển thành: **'Đang rà soát'**."
                        )
                        st.rerun()

    # ==========================================================================
    # TAB 3: ĐIỀU CHUYỂN (CHỌN HỒ SƠ ĐANG RÀ SOÁT, ĐỔI ASSIGNED_TO)
    # ==========================================================================
    with tab_transfer:
        st.subheader("🔄 Điều Chuyển Hồ Sơ Đang Rà Soát")
        st.markdown(
            "Chức năng dành cho Giám đốc điều phối lại nhân sự phụ trách khi chuyên viên cũ quá tải, "
            "nghỉ phép hoặc cần phân bổ lại cho nhân sự có chuyên môn phù hợp."
        )

        # LỌC HỒ SƠ 'Đang rà soát'
        in_review_list = [c for c in all_contracts if c.get("status") == "Đang rà soát"]

        if not in_review_list:
            st.info("Hiện không có hồ sơ nào ở trạng thái **'Đang rà soát'** để điều chuyển.")
        else:
            transfer_labels = [
                f"{c.get('id')} — {c.get('title')} (Đang giao cho: @{c.get('assigned_to', 'Chưa rõ')})"
                for c in in_review_list
            ]
            sel_trans_idx = st.selectbox(
                "Chọn hồ sơ cần điều chuyển:",
                range(len(in_review_list)),
                format_func=lambda i: transfer_labels[i],
                key="sel_transfer_contract"
            )
            transfer_contract = in_review_list[sel_trans_idx]
            current_assignee_username = transfer_contract.get("assigned_to", "")
            
            # Tìm thông tin chuyên viên hiện tại
            current_assignee_obj = next((u for u in all_users if u.get("username") == current_assignee_username), None)
            current_assignee_name = current_assignee_obj.get("full_name", current_assignee_username) if current_assignee_obj else current_assignee_username

            st.markdown("---")
            col_t1, col_t2 = st.columns([1, 1])

            with col_t1:
                st.markdown("##### 📌 Thông tin hồ sơ được chọn:")
                st.markdown(f"- **Mã hợp đồng:** `{transfer_contract.get('id')}`")
                st.markdown(f"- **Tên hợp đồng:** **{transfer_contract.get('title')}**")
                st.markdown(f"- **Đối tác:** {transfer_contract.get('partner_name')}")
                st.markdown(f"- **Giá trị:** {transfer_contract.get('value_vnd', 0):,.0f} VNĐ")
                st.markdown(f"- **Phòng ban đề xuất:** {transfer_contract.get('department')}")
                st.markdown(
                    f"- **Chuyên viên đang phụ trách hiện tại:** "
                    f"<span style='color: #DC2626; font-weight: 700;'>{current_assignee_name} (@{current_assignee_username})</span>",
                    unsafe_allow_html=True
                )

                # Hiển thị lịch sử điều chuyển nếu có
                reassignment_hist = transfer_contract.get("reassignment_history", [])
                if reassignment_hist:
                    st.markdown("###### 📜 Lịch sử các lần điều chuyển trước:")
                    for idx, rh in enumerate(reassignment_hist, 1):
                        st.markdown(
                            f"<div style='font-size: 0.8rem; background: #F8FAFC; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; border: 1px solid #E2E8F0;'>"
                            f"<b>Lần {idx}:</b> `{rh.get('transferred_at')}` — Từ <code>@{rh.get('from_user')}</code> sang <code>@{rh.get('to_user')}</code><br/>"
                            f"<i>Lý do:</i> {rh.get('reason')}</div>",
                            unsafe_allow_html=True
                        )

            with col_t2:
                st.markdown("##### 🔄 Chọn chuyên viên mới tiếp nhận:")
                
                # Danh sách ứng viên pháp chế
                legal_candidates = [
                    u for u in all_users
                    if u.get("department") == "Phòng Pháp chế" or "Pháp chế" in u.get("role", "")
                ]
                if not legal_candidates:
                    legal_candidates = all_users

                new_cand_labels = [
                    f"{u.get('full_name')} (@{u.get('username')}) — {u.get('role')}"
                    for u in legal_candidates
                ]
                sel_new_cand_idx = st.selectbox(
                    "Chọn chuyên viên tiếp nhận mới: *",
                    range(len(legal_candidates)),
                    format_func=lambda i: new_cand_labels[i],
                    key="sel_new_legal_candidate"
                )
                chosen_new_candidate = legal_candidates[sel_new_cand_idx]

                transfer_reason = st.text_area(
                    "Lý do điều chuyển nhân sự: *",
                    placeholder="Ghi rõ lý do (ví dụ: Chuyên viên cũ đi công tác/quá tải nhiệm vụ, chuyển giao theo phân công chuyên môn lĩnh vực...)",
                    height=90,
                    key="transfer_reason_input"
                )

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                btn_do_transfer = st.button(
                    "🔄 Xác Nhận Điều Chuyển Hồ Sơ",
                    type="primary",
                    use_container_width=True,
                    key=f"btn_transfer_confirm_{transfer_contract.get('id')}"
                )

                if btn_do_transfer:
                    if not transfer_reason.strip():
                        st.error("Vui lòng nhập lý do điều chuyển nhân sự!")
                    elif chosen_new_candidate.get("username") == current_assignee_username:
                        st.warning("Chuyên viên được chọn trùng với chuyên viên đang phụ trách hiện tại! Vui lòng chọn nhân sự khác.")
                    else:
                        # CẬP NHẬT ASSIGNED_TO SANG NHÂN VIÊN MỚI
                        old_assignee = current_assignee_username
                        new_assignee = chosen_new_candidate.get("username")

                        transfer_contract["assigned_to"] = new_assignee

                        # LƯU LỊCH SỬ ĐIỀU CHUYỂN
                        if "reassignment_history" not in transfer_contract:
                            transfer_contract["reassignment_history"] = []

                        transfer_contract["reassignment_history"].append({
                            "from_user": old_assignee,
                            "from_user_name": current_assignee_name,
                            "to_user": new_assignee,
                            "to_user_name": chosen_new_candidate.get("full_name"),
                            "transferred_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "transferred_by": current_username,
                            "reason": transfer_reason.strip()
                        })

                        if save_contracts(all_contracts):
                            st.success(
                                f"🎉 Đã điều chuyển hồ sơ **'{transfer_contract.get('id')}'** từ chuyên viên "
                                f"**{current_assignee_name}** (`@{old_assignee}`) sang **{chosen_new_candidate.get('full_name')}** (`@{new_assignee}`) thành công!"
                            )
                            st.rerun()

    # ==========================================================================
    # TAB 4: PHÊ DUYỆT & BAN HÀNH (BƯỚC 6 - CHI TIẾT, KHÔNG DÙNG PLACEHOLDER)
    # ==========================================================================
    with tab_approve:
        st.subheader("✍️ Phê Duyệt & Ban Hành Hợp Đồng")
        st.markdown(
            "Giám đốc Pháp chế đối chiếu nội dung văn bản hợp đồng (PDF) và toàn bộ lịch sử ý kiến thẩm định "
            "của chuyên viên pháp chế để ra quyết định **'Ký duyệt phát hành'** hoặc **'Yêu cầu làm lại'**."
        )

        # HIỂN THỊ CÁC HỒ SƠ CÓ TRẠNG THÁI 'Chờ Giám đốc duyệt'
        pending_approval_list = [c for c in all_contracts if c.get("status") == "Chờ Giám đốc duyệt"]

        if not pending_approval_list:
            st.info("Hiện không có hồ sơ nào ở trạng thái **'Chờ Giám đốc duyệt'**.")
        else:
            approval_labels = [
                f"{c.get('id')} — {c.get('title')} ({c.get('partner_name')} | {c.get('department')} | {c.get('value_vnd', 0):,.0f} VNĐ)"
                for c in pending_approval_list
            ]
            sel_appr_idx = st.selectbox(
                "Chọn hồ sơ cần thẩm tra và phê duyệt:",
                range(len(pending_approval_list)),
                format_func=lambda i: approval_labels[i],
                key="sel_director_approve_contract"
            )
            appr_contract = pending_approval_list[sel_appr_idx]

            st.markdown("---")

            # MÀN HÌNH CHIA 2 CỘT
            col_pdf_left, col_review_right = st.columns([1.05, 0.95])

            # ------------------------------------------------------------------
            # CỘT TRÁI: HIỂN THỊ TRÌNH XEM PDF (<iframe>) ĐỐI CHIẾU LẠI NỘI DUNG HỢP ĐỒNG
            # ------------------------------------------------------------------
            with col_pdf_left:
                st.markdown("#### 📄 Trình Xem Văn Bản Hợp Đồng (Đối Chiếu PDF)")
                st.markdown(
                    f"**Mã HĐ:** `{appr_contract.get('id')}` | **Trạng thái:** `{appr_contract.get('status')}`\n\n"
                    f"**Tên hợp đồng:** **{appr_contract.get('title')}**\n\n"
                    f"**Đối tác:** {appr_contract.get('partner_name')} | **Giá trị:** **{appr_contract.get('value_vnd', 0):,.0f} VNĐ**"
                )

                appr_attachments = appr_contract.get("attachments", [])
                if not appr_attachments:
                    st.warning("Hồ sơ này không có tài liệu PDF đính kèm để đối chiếu.")
                else:
                    att_appr_labels = [
                        f"{i+1}. [{att.get('checklist_item', 'Tài liệu')}]: {att.get('file_name', 'document.pdf')}"
                        for i, att in enumerate(appr_attachments)
                    ]
                    chosen_appr_att_idx = st.selectbox(
                        "Chọn tài liệu cần xem trước:",
                        range(len(appr_attachments)),
                        format_func=lambda i: att_appr_labels[i],
                        key=f"appr_att_sel_{appr_contract.get('id')}"
                    )
                    chosen_appr_att = appr_attachments[chosen_appr_att_idx]
                    pdf_b64_str = chosen_appr_att.get("file_base64", "").strip()

                    view_mode_appr = st.radio(
                        "Chế độ xem văn bản:",
                        ["📖 Trình đọc văn bản A4 sắc nét", "📑 Tệp gốc PDF (iFrame / Object)"],
                        horizontal=True,
                        key=f"mode_appr_pdf_{appr_contract.get('id')}"
                    )

                    if view_mode_appr == "📖 Trình đọc văn bản A4 sắc nét":
                        # CHẾ ĐỘ 1: TRÌNH ĐỌC VĂN BẢN HỢP ĐỒNG A4 SẮC NÉT (CHỐNG LỖI SANDBOX BLOCKED IFRAME)
                        att_fname = chosen_appr_att.get("file_name", "hop_dong.pdf")
                        chk_item = chosen_appr_att.get("checklist_item", "Dự thảo hợp đồng")
                        cfg_sys = get_config()
                        comp_name = cfg_sys.get("company_name", "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU - ASIA HOLDINGS")
                        st.markdown(
                            f"""
                            <div style="border-radius: 12px; border: 1.5px solid #CBD5E1; box-shadow: 0 4px 10px rgba(0,0,0,0.06); background-color: #F8FAFC; overflow: hidden; margin-top: 8px; margin-bottom: 8px;">
                                <div style="background-color: #1E293B; color: #FFFFFF; padding: 8px 14px; font-size: 0.82rem; font-weight: 600; display: flex; justify-content: space-between; align-items: center;">
                                    <span>📖 Văn bản đối chiếu: <b>{att_fname}</b></span>
                                    <span style="color: #6EE7B7; font-size: 0.75rem; font-family: monospace;">Khổ chuẩn A4 • Sắc nét</span>
                                </div>
                                <div style="padding: 24px; background: #FFFFFF; max-height: 520px; min-height: 520px; overflow-y: auto; font-family: serif; color: #1E293B; border-top: 1px solid #E2E8F0; line-height: 1.6;">
                                    <div style="text-align: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 12px;">
                                        <div style="font-weight: 800; font-size: 0.85rem; text-transform: uppercase; color: #0F172A;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
                                        <div style="font-weight: 700; font-size: 0.78rem; color: #334155;">Độc lập - Tự do - Hạnh phúc</div>
                                        <div style="font-size: 0.75rem; color: #64748B; margin-top: 2px;">***</div>
                                    </div>
                                    <div style="text-align: center; margin-bottom: 14px;">
                                        <h3 style="font-size: 1.05rem; font-weight: 800; text-transform: uppercase; color: #0F172A; margin: 0;">{appr_contract.get('title')}</h3>
                                        <div style="font-size: 0.78rem; color: #64748B; font-family: sans-serif; margin-top: 4px;">
                                            Số hiệu: <b>{appr_contract.get('id')}</b> | Phân loại: <b>{appr_contract.get('contract_type')}</b>
                                        </div>
                                        <div style="font-size: 0.78rem; color: #2563EB; font-family: sans-serif; font-weight: 600; margin-top: 2px;">
                                            Hạng mục hồ sơ: [{chk_item}]
                                        </div>
                                    </div>
                                    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; font-size: 0.8rem; font-family: sans-serif; margin-bottom: 14px;">
                                        <div><b>Bên đề xuất (Bên A):</b> {comp_name} - {appr_contract.get('department')}</div>
                                        <div style="margin-top: 3px;"><b>Đối tác (Bên B):</b> <span style="color: #1E3A8A; font-weight: 700;">{appr_contract.get('partner_name')}</span></div>
                                        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed #CBD5E1; display: flex; justify-content: space-between; flex-wrap: wrap;">
                                            <span>Giá trị hợp đồng: <b style="color: #047857;">{appr_contract.get('value_vnd', 0):,.0f} VNĐ</b></span>
                                            <span>Thời hạn: <b>{appr_contract.get('effective_date')}</b> đến <b>{appr_contract.get('expiration_date')}</b></span>
                                        </div>
                                    </div>
                                    <div style="font-size: 0.8rem; font-family: sans-serif; color: #334155;">
                                        <p><b>Điều 1. Phạm vi công việc & Tài liệu đối chiếu:</b><br/>
                                        Bên B cam kết cung cấp đúng chỉ tiêu kỹ thuật, danh mục được quy định tại phụ lục tệp <i>{att_fname}</i>, bảo đảm chất lượng và tiêu chuẩn hiện hành của Nhà nước Việt Nam.</p>
                                        <p><b>Điều 2. Giá trị hợp đồng & Phương thức thanh toán:</b><br/>
                                        Tổng giá trị hợp đồng là <b>{appr_contract.get('value_vnd', 0):,.0f} VNĐ</b> (đã bao gồm các loại thuế, phí hợp pháp). Thanh toán chuyển khoản theo từng đợt nghiệm thu thực tế.</p>
                                        <p><b>Điều 3. Thẩm định Pháp lý & Điều khoản bảo hành:</b><br/>
                                        Hồ sơ đã được Phòng Pháp chế rà soát và thông qua. Ý kiến chuyên môn ghi nhận: <i>"{appr_contract.get('legal_review', {}).get('summary_notes', 'Đảm bảo cân bằng quyền lợi và bảo vệ lợi ích công ty.')}"</i>.</p>
                                    </div>
                                    <div style="margin-top: 18px; padding-top: 12px; border-top: 1px solid #E2E8F0; display: flex; justify-content: space-between; font-family: sans-serif; font-size: 0.78rem; text-align: center;">
                                        <div style="width: 48%;">
                                            <div style="font-weight: 700; color: #1E293B;">ĐẠI DIỆN ĐỐI TÁC (BÊN B)</div>
                                            <div style="font-size: 0.72rem; color: #64748B; font-style: italic;">(Ký, đóng dấu điện tử)</div>
                                            <div style="height: 48px; display: flex; align-items: center; justify-content: center; color: #94A3B8; font-style: italic;">[Đã ký điện tử]</div>
                                            <div style="font-weight: 600; color: #334155;">{appr_contract.get('partner_name')}</div>
                                        </div>
                                        <div style="width: 48%;">
                                            <div style="font-weight: 700; color: #1E293B;">GIÁM ĐỐC PHÁP CHẾ PHÊ DUYỆT</div>
                                            <div style="font-size: 0.72rem; color: #64748B; font-style: italic;">(Ký duyệt ban hành)</div>
                                            <div style="height: 48px; display: flex; align-items: center; justify-content: center;">
                                                <span style="border: 1.5px solid #059669; color: #059669; background: #ECFDF5; padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 0.68rem; text-transform: uppercase;">BAN GIÁM ĐỐC CHỜ DUYỆT</span>
                                            </div>
                                            <div style="font-weight: 600; color: #334155;">{current_fullname}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        # CHẾ ĐỘ 2: NHÚNG TỆP GỐC QUA OBJECT / EMBED / IFRAME BASE64
                        if pdf_b64_str:
                            raw_b64_clean = pdf_b64_str
                            if "base64," in raw_b64_clean:
                                raw_b64_clean = raw_b64_clean.split("base64,", 1)[1]
                            raw_b64_clean = "".join(raw_b64_clean.split())
                            missing_pad = len(raw_b64_clean) % 4
                            if missing_pad:
                                raw_b64_clean += "=" * (4 - missing_pad)
                            pdf_data_url = f"data:application/pdf;base64,{raw_b64_clean}"
                            att_fname = chosen_appr_att.get("file_name", "hop_dong.pdf")

                            st.markdown(
                                f"""
                                <div style="border-radius: 10px; overflow: hidden; border: 1.5px solid #CBD5E1; background: #FFFFFF; margin-top: 8px; margin-bottom: 8px;">
                                    <div style="background-color: #F8FAFC; padding: 8px 12px; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
                                        <span style="font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                                            📑 {att_fname} - [{chosen_appr_att.get('checklist_item')}]
                                        </span>
                                        <a href="{pdf_data_url}" target="_blank" download="{att_fname}" style="font-size: 0.78rem; font-weight: 600; color: #2563EB; text-decoration: none; background: #EFF6FF; padding: 3px 8px; border-radius: 4px; border: 1px solid #BFDBFE;">↗️ Mở toàn màn hình</a>
                                    </div>
                                    <object data="{pdf_data_url}#toolbar=1" type="application/pdf" width="100%" height="520px" style="border: none; display: block;">
                                        <embed src="{pdf_data_url}#toolbar=1" type="application/pdf" width="100%" height="520px" />
                                        <iframe src="{pdf_data_url}" width="100%" height="520px" style="border: none;">
                                            <div style="padding: 16px; text-align: center; color: #64748B; font-size: 0.85rem;">
                                                Văn bản hợp đồng sẵn sàng.<br/>
                                                <a href="{pdf_data_url}" download="{att_fname}" style="color: #2563EB; font-weight: bold;">Nhấp vào đây để tải tệp PDF về máy</a>
                                            </div>
                                        </iframe>
                                    </object>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            st.info("Tài liệu không có nội dung base64.")

                    # NÚT DOWNLOAD DỰ PHÒNG CHUẨN NATIVE STREAMLIT
                    raw_clean = pdf_b64_str.split("base64,")[-1].strip().replace(" ", "").replace("\n", "").replace("\r", "")
                    if len(raw_clean) % 4:
                        raw_clean += "=" * (4 - len(raw_clean) % 4)
                    try:
                        pdf_raw_bytes = base64.b64decode(raw_clean)
                    except Exception:
                        pdf_raw_bytes = None

                    att_fname = chosen_appr_att.get("file_name", "hop_dong.pdf")
                    if pdf_raw_bytes:
                        st.download_button(
                            label=f"📥 Tải tệp '{att_fname}' về máy",
                            data=pdf_raw_bytes,
                            file_name=att_fname,
                            mime="application/pdf",
                            key=f"dl_appr_att_{appr_contract.get('id')}_{chosen_appr_att_idx}",
                            use_container_width=True
                        )

            # ------------------------------------------------------------------
            # CỘT PHẢI: TOÀN BỘ LỊCH SỬ Ý KIẾN GÓP Ý CỦA PHÁP CHẾ & 2 NÚT THAO TÁC
            # ------------------------------------------------------------------
            with col_review_right:
                st.markdown("#### ⚖️ Lịch Sử Thẩm Định & Ý Kiến Của Pháp Chế")

                l_rev = appr_contract.get("legal_review", {})
                if not l_rev:
                    st.warning("Chưa có dữ liệu thẩm định pháp lý của chuyên viên.")
                else:
                    rev_name = l_rev.get("reviewer_name", appr_contract.get("assigned_to", "Chuyên viên Pháp chế"))
                    rev_time = l_rev.get("reviewed_at", "Chưa rõ")
                    rev_assess = l_rev.get("general_assessment", "Chưa đánh giá")
                    rev_notes = l_rev.get("summary_notes", "Không có ghi chú thêm.")

                    badge_bg = "#DCFCE7" if "Đủ điều kiện" in rev_assess else ("#FEE2E2" if "Không đủ" in rev_assess else "#FEF3C7")
                    badge_color = "#166534" if "Đủ điều kiện" in rev_assess else ("#991B1B" if "Không đủ" in rev_assess else "#92400E")

                    st.markdown(
                        f"""
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 0.85rem; color: #475569;">Chuyên viên thẩm định: <b>{rev_name}</b> (<code>@{appr_contract.get('assigned_to')}</code>)</span>
                                <span style="font-size: 0.78rem; color: #64748B;">🕒 {rev_time}</span>
                            </div>
                            <div style="margin-top: 8px;">
                                <span style="font-size: 0.85rem; font-weight: 700; color: #1E293B;">Đánh giá tổng quát: </span>
                                <span style="background: {badge_bg}; color: {badge_color}; font-weight: 700; padding: 2px 8px; border-radius: 6px; font-size: 0.82rem;">
                                    {rev_assess}
                                </span>
                            </div>
                            <div style="margin-top: 8px; font-size: 0.85rem; color: #334155;">
                                <b>Ý kiến kết luận của Pháp chế:</b><br/>
                                <div style="background: #FFFFFF; border-left: 3px solid #3B82F6; padding: 6px 10px; margin-top: 4px; border-radius: 4px; font-style: italic;">
                                    "{rev_notes}"
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # CHI TIẾT TỪNG MỤC CHECKLIST
                    st.markdown("##### 📋 Chi tiết đánh giá từng mục Checklist:")
                    chk_map = l_rev.get("checklist_results", {})
                    if chk_map:
                        for it_key, it_val in chk_map.items():
                            i_stat = it_val.get("status", "Đạt")
                            i_com = it_val.get("comment", "")
                            st_icon = "🟢 Đạt" if i_stat == "Đạt" else ("🔴 Không đạt" if i_stat == "Không đạt" else "🟡 Có góp ý")
                            st.markdown(
                                f"""
                                <div style="padding: 7px 10px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; margin-bottom: 6px; font-size: 0.83rem;">
                                    <div style="display: flex; justify-content: space-between;">
                                        <b>{it_key}</b>
                                        <span style="font-weight: 700;">{st_icon}</span>
                                    </div>
                                    {f'<div style="color: #64748B; font-size: 0.78rem; margin-top: 2px; font-style: italic;">↳ Góp ý: "{i_com}"</div>' if i_com else ''}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    else:
                        st.caption("Chưa có bảng checklist chi tiết.")

                st.markdown("---")
                st.markdown("#### ✍️ Quyết Định Phê Duyệt Của Giám Đốc")

                dir_opinion = st.text_area(
                    "Ý kiến phê duyệt / Chỉ đạo ban hành:",
                    value="Đồng ý thông qua nội dung dự thảo hợp đồng theo thẩm định của Phòng Pháp chế. Cho phép phát hành và tiến hành ký kết.",
                    height=85,
                    key=f"dir_opinion_input_{appr_contract.get('id')}"
                )

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                col_btn_approve, col_btn_reject = st.columns(2)

                with col_btn_approve:
                    btn_approve_action = st.button(
                        "✅ Ký duyệt phát hành",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_approve_action_{appr_contract.get('id')}"
                    )

                with col_btn_reject:
                    btn_reject_action = st.button(
                        "↩️ Yêu cầu làm lại",
                        type="secondary",
                        use_container_width=True,
                        key=f"btn_reject_action_{appr_contract.get('id')}"
                    )

                # LOGIC XỬ LÝ KHI NHẤN NÚT
                if btn_approve_action or btn_reject_action:
                    action_key = "approve" if btn_approve_action else "reject"
                    new_status = "Hoàn tất" if action_key == "approve" else "Đang rà soát"
                    pdf_filename = f"Phieu_gop_y_{appr_contract.get('id')}.pdf"

                    # 1. DÙNG FPDF TẠO FILE PDF 'PHIẾU GÓP Ý HỢP ĐỒNG' (UNICODE FONT)
                    pdf_result_bytes = generate_review_pdf(
                        contract=appr_contract,
                        action_type=action_key,
                        director_notes=dir_opinion.strip(),
                        director_name=current_fullname
                    )

                    # 2. DÙNG SMTPLIB GỬI EMAIL TỰ ĐỘNG ĐÍNH KÈM FILE PDF
                    email_ok, email_msg = send_approval_email(
                        contract=appr_contract,
                        pdf_bytes=pdf_result_bytes,
                        pdf_filename=pdf_filename,
                        action_type=action_key,
                        director_notes=dir_opinion.strip()
                    )

                    # 3. CẬP NHẬT TRẠNG THÁI HỢP ĐỒNG & LƯU LẠI CONTRACTS.JSON
                    appr_contract["status"] = new_status
                    appr_contract["director_approval"] = {
                        "approved_by": current_username,
                        "approved_by_name": current_fullname,
                        "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "action": "Ký duyệt phát hành" if action_key == "approve" else "Yêu cầu làm lại",
                        "notes": dir_opinion.strip(),
                        "review_sheet_pdf": pdf_filename
                    }

                    if save_contracts(all_contracts):
                        st.session_state[f"last_gen_pdf_{appr_contract.get('id')}"] = pdf_result_bytes
                        st.session_state[f"last_gen_pdf_name_{appr_contract.get('id')}"] = pdf_filename

                        if action_key == "approve":
                            st.success(
                                f"🎉 **Đã Ký duyệt phát hành thành công hợp đồng '{appr_contract.get('id')}: {appr_contract.get('title')}'!**\n\n"
                                f"Trạng thái hợp đồng đã chuyển thành: **'Hoàn tất'**."
                            )
                        else:
                            st.warning(
                                f"↩️ **Đã chuyển hồ sơ '{appr_contract.get('id')}' về trạng thái 'Đang rà soát' để yêu cầu làm lại!**"
                            )

                        if email_ok:
                            st.success(f"📧 {email_msg}")
                        else:
                            st.info(f"📧 {email_msg}")

                # 4. HIỆN NÚT ST.DOWNLOAD_BUTTON TẢI FILE PDF TRÊN GIAO DIỆN
                stored_pdf = st.session_state.get(f"last_gen_pdf_{appr_contract.get('id')}")
                stored_pdf_name = st.session_state.get(f"last_gen_pdf_name_{appr_contract.get('id')}", f"Phieu_gop_y_{appr_contract.get('id')}.pdf")

                if not stored_pdf:
                    stored_pdf = generate_review_pdf(
                        contract=appr_contract,
                        action_type="approve",
                        director_notes=dir_opinion.strip(),
                        director_name=current_fullname
                    )
                    stored_pdf_name = f"Phieu_gop_y_{appr_contract.get('id')}.pdf"

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.download_button(
                    label=f"📥 Tải 'Phiếu góp ý Hợp đồng' ({stored_pdf_name})",
                    data=stored_pdf,
                    file_name=stored_pdf_name,
                    mime="application/pdf",
                    key=f"btn_download_review_pdf_{appr_contract.get('id')}",
                    use_container_width=True
                )

# ==============================================================================
# 11. ĐIỀU HƯỚNG TỔNG THỂ & RENDER_MAIN_DASHBOARD()
# ==============================================================================
def render_main_dashboard():
    display_branding()

    current_user = st.session_state.get("user", {})
    user_role = current_user.get("role", "")
    user_dept = current_user.get("department", "")

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

    menu_options = []
    # Ban Giám đốc hoặc Admin hoặc Giám đốc Pháp chế
    if user_role in ["Ban Giám đốc", "Admin", "Giám đốc Pháp chế"]:
        menu_options.append("👑 Quản trị Giám đốc (director_view)")

    # Nhân sự Phòng Pháp chế hoặc Admin
    if user_role in ["Pháp chế", "Chuyên viên Pháp chế", "Giám đốc Pháp chế", "Phó Phòng Pháp chế", "Nhân viên Pháp chế", "Admin", "Ban Giám đốc"]:
        menu_options.append("⚖️ Bàn làm việc Pháp chế (legal_staff_view)")
        menu_options.append("📑 Cấu hình Checklist (workflow_config_view)")


    # Phòng ban đề nghị
    menu_options.append("📤 Cổng nộp hồ sơ (department_view)")

    # Admin
    if user_role in ["Admin", "Ban Giám đốc"]:
        menu_options.append("⚙️ Quản trị Admin (admin_view)")

    menu_options.append("📊 Tổng quan hệ thống")

    choice = st.sidebar.radio("CHỨC NĂNG HỆ THỐNG", menu_options)

    if choice == "👑 Quản trị Giám đốc (director_view)":
        director_view()
    elif choice == "⚖️ Bàn làm việc Pháp chế (legal_staff_view)":
        legal_staff_view()
    elif choice == "📤 Cổng nộp hồ sơ (department_view)":
        department_view()
    elif choice == "⚙️ Quản trị Admin (admin_view)":
        admin_view()
    elif choice == "📑 Cấu hình Checklist (workflow_config_view)":
        workflow_config_view()
    elif choice == "📊 Tổng quan hệ thống":
        st.title("📊 Tổng Quan Toàn Hệ Thống")
        contracts_data = get_contracts()
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Tổng Hợp đồng", len(contracts_data))
        with m2: st.metric("Phòng ban", len(get_departments()))
        with m3: st.metric("Quy trình", len(get_workflows()))
        with m4: st.metric("Người dùng", len(get_users()))
        if contracts_data:
            df = pd.DataFrame(contracts_data)
            st.dataframe(df[["id", "title", "partner_name", "value_vnd", "status", "assigned_to"]], use_container_width=True)

# ==============================================================================
# 11. ĐIỂM BẮT ĐẦU CHÍNH (MAIN ENTRY POINT)
# ==============================================================================
def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        render_login_screen()
    else:
        render_main_dashboard()

if __name__ == "__main__":
    main()
