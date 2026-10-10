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
# 1. CẤU HÌNH TRANG & CSS GIAO DIỆN CHUẨN DOANH NGHIỆP
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Quản Lý & Thẩm Định Hợp Đồng - Phòng Pháp Chế",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tối ưu hóa UI giao diện doanh nghiệp
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stDownloadButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 700;
    }
    iframe {
        border-radius: 8px;
        border: 1px solid #CBD5E1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. KHỞI TẠO SESSION STATE TOÀN CỤC
# ==============================================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user" not in st.session_state:
    st.session_state["user"] = None

if "role" not in st.session_state:
    st.session_state["role"] = None

# ==============================================================================
# 3. ĐỊNH NGHĨA FILE JSON & CÁC HÀM TIỆN ÍCH DỮ LIỆU
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

# BỘ DỮ LIỆU DỰ PHÒNG CHUẨN XÁC ĐẢM BẢO KHÔNG BAO GIỜ BỊ KEY ERROR
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
        "role": "Giám đốc Pháp chế",
        "department": "Ban Giám đốc",
        "email": "thang.tq@congty.com.vn",
        "zalo": "0912345678",
        "status": "active"
    },
    {
        "username": "giamdoc01",
        "password": "gd123",
        "full_name": "Trần Quang Thắng",
        "role": "Giám đốc Pháp chế",
        "department": "Ban Giám đốc",
        "email": "thang.tq@congty.com.vn",
        "zalo": "0912345678",
        "status": "active"
    },
    {
        "username": "phapche01",
        "password": "pc123",
        "full_name": "Nguyễn Văn Luật",
        "role": "Nhân viên Pháp chế",
        "department": "Phòng Pháp chế",
        "email": "luat.nv@congty.com.vn",
        "zalo": "0987654321",
        "status": "active"
    },
    {
        "username": "phapche02",
        "password": "pc456",
        "full_name": "Lê Thị Mai",
        "role": "Nhân viên Pháp chế",
        "department": "Phòng Pháp chế",
        "email": "mai.lt@congty.com.vn",
        "zalo": "0988776655",
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

DEFAULT_DEPARTMENTS = [
    {"id": "DEPT_BGD", "name": "Ban Giám đốc", "manager": "Quản trị viên Hệ thống", "email": "bod@asiaholdings.vn"},
    {"id": "DEPT_PC", "name": "Phòng Pháp chế", "manager": "Nguyễn Văn Luật", "email": "legal@asiaholdings.vn"},
    {"id": "DEPT_KT", "name": "Phòng Kế toán - Tài chính", "manager": "Trần Thị Thu", "email": "finance@asiaholdings.vn"},
    {"id": "DEPT_KD", "name": "Phòng Kinh doanh & Tiếp thị", "manager": "Lê Hoàng Nam", "email": "sales@asiaholdings.vn"},
    {"id": "DEPT_NS", "name": "Phòng Nhân sự - Hành chính", "manager": "Phạm Hồng Hạnh", "email": "hr@asiaholdings.vn"}
]

DEFAULT_WORKFLOWS = [
    {
        "id": "WF_COMMERCIAL",
        "name": "Hợp đồng Thương mại & Dịch vụ",
        "contract_type": "Hợp đồng Thương mại & Dịch vụ",
        "description": "Áp dụng cho các hợp đồng mua bán hàng hóa, cung ứng dịch vụ thương mại, hợp tác kinh doanh.",
        "checklist": [
            "Dự thảo Hợp đồng chi tiết",
            "Giấy chứng nhận ĐKKD của đối tác",
            "Báo giá chính thức & Thỏa thuận thương mại",
            "Tài liệu khác"
        ]
    },
    {
        "id": "WF_LABOR",
        "name": "Hợp đồng Lao động & Đào tạo",
        "contract_type": "Hợp đồng Lao động & Đào tạo",
        "description": "Áp dụng cho tuyển dụng nhân sự chính thức, hợp đồng đào tạo nghiệp vụ và cam kết bảo mật.",
        "checklist": [
            "Dự thảo Hợp đồng lao động",
            "Sơ yếu lý lịch & Bằng cấp chuyên môn",
            "Thỏa thuận bảo mật thông tin (NDA)",
            "Tài liệu khác"
        ]
    }
]

DEFAULT_CONFIG = {
    "company_name": "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU",
    "short_name": "ASIA HOLDINGS",
    "company_address": "Tầng 18, Tòa nhà Landmark 72, Đường Phạm Hùng, Q. Nam Từ Liêm, Hà Nội",
    "company_phone": "(024) 3788 9999",
    "company_email": "phapche@asiaholdings.vn",
    "system_version": "2.5.0 (Bước 8.1)",
    "logo_base64": DEFAULT_LOGO_SVG_B64,
    "smtp_settings": {
        "server": "smtp.gmail.com",
        "port": 587,
        "sender_email": "phapche.asiaholdings@gmail.com",
        "app_password": "",
        "use_tls": True
    },
    "gemini_api_key": ""
}

# Tương thích đồng thời 2 quy chuẩn hàm load_json_file và read_json_file
load_json_file = read_json_file
save_json_file = write_json_file

def get_users():
    users = read_json_file(USERS_FILE, DEFAULT_USERS)
    if not users:
        users = DEFAULT_USERS
        save_users(users)
    return users

def save_users(data): return write_json_file(USERS_FILE, data)

def get_config():
    cfg = read_json_file(CONFIG_FILE, DEFAULT_CONFIG)
    if not cfg:
        cfg = DEFAULT_CONFIG
        save_config(cfg)
    return cfg

def save_config(data): return write_json_file(CONFIG_FILE, data)

def get_workflows():
    wfs = read_json_file(WORKFLOWS_FILE, DEFAULT_WORKFLOWS)
    if not wfs:
        wfs = DEFAULT_WORKFLOWS
        save_workflows(wfs)
    return wfs

def save_workflows(data): return write_json_file(WORKFLOWS_FILE, data)

def get_departments():
    depts = read_json_file(DEPARTMENTS_FILE, DEFAULT_DEPARTMENTS)
    if not depts:
        depts = DEFAULT_DEPARTMENTS
        save_departments(depts)
    return depts

def save_departments(data): return write_json_file(DEPARTMENTS_FILE, data)

def get_contracts():
    return read_json_file(CONTRACTS_FILE, [])

def save_contracts(data): return write_json_file(CONTRACTS_FILE, data)

# ==============================================================================
# 4. HÀM HIỂN THỊ THƯƠNG HIỆU & LOGO BASE64
# ==============================================================================
def display_branding():
    system_config = get_config()
    company_name = system_config.get("company_name", "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU")
    short_name = system_config.get("short_name", "ASIA HOLDINGS")
    logo_b64 = system_config.get("logo_base64", DEFAULT_LOGO_SVG_B64).strip()
    system_version = system_config.get("system_version", "2.5.0")

    if logo_b64.startswith("data:image"):
        clean_b64 = logo_b64
    elif logo_b64.startswith("<svg") or "<svg" in logo_b64:
        encoded_svg = base64.b64encode(logo_b64.encode("utf-8")).decode("utf-8")
        clean_b64 = f"data:image/svg+xml;base64,{encoded_svg}"
    else:
        clean_b64 = f"data:image/png;base64,{logo_b64}"

    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 50%, #3B82F6 100%); border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="display: flex; align-items: center; gap: 16px;">
                <img src="{clean_b64}" style="width: 54px; height: 54px; border-radius: 10px; background: white; padding: 4px; object-fit: contain; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" alt="Logo"/>
                <div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px; text-transform: uppercase;">{company_name}</div>
                    <div style="font-size: 0.85rem; color: #BFDBFE; font-weight: 500;">HỆ THỐNG QUẢN LÝ VÀ THẨM ĐỊNH PHÁP CHẾ HỢP ĐỒNG DOANH NGHIỆP • {short_name}</div>
                </div>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(255, 255, 255, 0.2); color: #FFFFFF; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">Phiên bản {system_version}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP & XÁC THỰC
# ==============================================================================
def render_login_screen():
    display_branding()

    col_left, col_center, col_right = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #1E3A8A; font-weight: 800; margin-bottom: 6px;">🔐 Đăng Nhập Cổng Pháp Chế</h2>
                <p style="color: #64748B; font-size: 0.9rem;">Vui lòng nhập tài khoản được cấp hoặc chọn tài khoản dùng thử bên dưới</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        user_list = get_users()
        user_display_opts = ["-- Chọn tài khoản mẫu đăng nhập nhanh --"] + [
            f"{u.get('username')} - {u.get('full_name')} ({u.get('role')})" for u in user_list
        ]

        selected_sample = st.selectbox(
            "⚡ Chọn nhanh tài khoản kiểm thử:",
            user_display_opts,
            index=0,
            key="quick_select_user"
        )

        default_user = ""
        default_pwd = ""
        if selected_sample != "-- Chọn tài khoản mẫu đăng nhập nhanh --":
            u_name = selected_sample.split(" - ")[0]
            default_user = u_name
            matched = next((u for u in user_list if u.get("username") == u_name), None)
            if matched:
                default_pwd = matched.get("password", "")

        with st.form("form_dang_nhap", clear_on_submit=False):
            username_val = st.text_input("Tên đăng nhập", value=default_user, placeholder="admin / giamdoc / phapche01")
            password_val = st.text_input("Mật khẩu", type="password", value=default_pwd, placeholder="admin123 / 123456 / pc123")
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
                            "email": "admin@congty.com.vn",
                            "zalo": "0901234567"
                        }
                    elif u_input in ["giamdoc", "giamdoc01"] and p_input in ["123456", "gd123"]:
                        matched_account = {
                            "username": "giamdoc01",
                            "full_name": "Trần Quang Thắng",
                            "role": "Giám đốc Pháp chế",
                            "department": "Ban Giám đốc",
                            "email": "thang.tq@congty.com.vn",
                            "zalo": "0912345678"
                        }
                    elif u_input == "phapche01" and p_input == "pc123":
                        matched_account = {
                            "username": "phapche01",
                            "full_name": "Nguyễn Văn Luật",
                            "role": "Nhân viên Pháp chế",
                            "department": "Phòng Pháp chế",
                            "email": "luat.nv@congty.com.vn",
                            "zalo": "0987654321"
                        }

                if matched_account:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = matched_account
                    st.session_state["role"] = matched_account.get("role", "Phòng ban đề nghị")
                    st.success(f"Đăng nhập thành công! Chào mừng {matched_account.get('full_name')}.")
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu không chính xác! Vui lòng thử 'admin' / 'admin123'.")

        st.markdown(
            """
            <div style="margin-top: 20px; padding: 14px 16px; background-color: #F1F5F9; border-radius: 10px; border-left: 4px solid #3B82F6; font-size: 0.85rem; color: #334155;">
                <strong>Danh sách tài khoản dùng thử hệ thống:</strong><br/>
                • <b>Quản trị viên (Admin):</b> <code>admin</code> / <code>admin123</code><br/>
                • <b>Giám đốc Pháp chế:</b> <code>giamdoc</code> (<code>123456</code>) hoặc <code>giamdoc01</code> (<code>gd123</code>)<br/>
                • <b>Nhân viên Pháp chế:</b> <code>phapche01</code> / <code>pc123</code><br/>
                • <b>Phòng ban đề xuất:</b> <code>kinhdoanh01</code> / <code>kd123</code>
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
# 6. BƯỚC 2: HÀM ADMIN_VIEW() - NÂNG CẤP BƯỚC 8.1 SỬA USERNAME & PHÂN QUYỀN
# ==============================================================================
def admin_view():
    st.title("⚙️ Bảng Điều Khiển Quản Trị Hệ Thống (Admin Panel)")
    tab_depts, tab_users, tab_sys_config = st.tabs([
        "🏢 Quản Lý Phòng Ban",
        "👥 Quản Lý Người Dùng & Phân Quyền",
        "🌐 Cấu Hình Nhận Diện Doanh Nghiệp"
    ])

    with tab_depts:
        st.subheader("🏢 Danh Sách & Thiết Lập Phòng Ban Doanh Nghiệp")
        departments = get_departments()
        if departments:
            df_depts = pd.DataFrame(departments)
            st.dataframe(df_depts, use_container_width=True)
        else:
            st.info("Chưa có danh mục phòng ban nào trong departments.json!")

        col_add, col_edit, col_del = st.columns(3)
        with col_add:
            with st.form("form_add_dept"):
                st.markdown("##### ➕ Thêm Phòng Ban")
                new_d_name = st.text_input("Tên phòng ban *")
                new_d_id = st.text_input("Mã phòng ban (VD: DEPT_KD)")
                new_d_mgr = st.text_input("Trưởng phòng phụ trách")
                new_d_mail = st.text_input("Email đầu mối")
                if st.form_submit_button("Lưu Phòng Ban Mới", use_container_width=True):
                    if new_d_name.strip():
                        new_id = new_d_id.strip() if new_d_id.strip() else f"DEPT_{len(departments)+1}"
                        departments.append({"id": new_id, "name": new_d_name.strip(), "manager": new_d_mgr.strip(), "email": new_d_mail.strip()})
                        save_departments(departments)
                        st.success("Thêm thành công!")
                        st.rerun()

        with col_edit:
            if departments:
                with st.form("form_edit_dept"):
                    st.markdown("##### ✏️ Chỉnh Sửa Phòng Ban")
                    d_opts = [d["name"] for d in departments]
                    sel_d = st.selectbox("Chọn phòng ban:", d_opts)
                    target_d = next((d for d in departments if d["name"] == sel_d), None)
                    e_name = st.text_input("Tên mới:", value=target_d.get("name", "") if target_d else "")
                    e_mgr = st.text_input("Trưởng phòng:", value=target_d.get("manager", "") if target_d else "")
                    e_mail = st.text_input("Email:", value=target_d.get("email", "") if target_d else "")
                    if st.form_submit_button("Cập Nhật", use_container_width=True):
                        if target_d and e_name.strip():
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

        # 2. TABS TẠO MỚI HOẶC CHỈNH SỬA TÀI KHOẢN (BƯỚC 8.1 SỬA ĐƯỢC USERNAME)
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
                        key="add_u_auto_role"
                    )

            if st.button("Tạo Tài Khoản Mới 🚀", type="primary", use_container_width=True, key="btn_create_user"):
                if not u_name.strip():
                    st.error("❌ Tên đăng nhập không được để trống!")
                elif any(u.get("username") == u_name.strip() for u in all_users):
                    st.error(f"❌ Tên đăng nhập '{u_name.strip()}' đã tồn tại trong hệ thống!")
                elif not u_pass.strip():
                    st.error("❌ Mật khẩu không được để trống!")
                elif not u_fullname.strip():
                    st.error("❌ Họ và tên không được để trống!")
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
            st.markdown("##### ✏️ Chỉnh Sửa Thông Tin & Phân Quyền Tài Khoản (Cho phép đổi Username)")
            if all_users:
                user_select_labels = [f"{u.get('username')} - {u.get('full_name')} ({u.get('department')})" for u in all_users]
                selected_user_label = st.selectbox("Chọn tài khoản cần cập nhật:", user_select_labels, key="sel_user_to_edit")
                selected_uname = selected_user_label.split(" - ")[0]
                target_user = next((u for u in all_users if u.get("username") == selected_uname), None)

                if target_user:
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        ed_uname = st.text_input(
                            "Tên đăng nhập (Username) * (Admin có thể sửa):",
                            value=target_user.get("username", ""),
                            key=f"ed_uname_{target_user['username']}"
                        )
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
                        old_uname = target_user.get("username", "").strip()
                        new_uname = ed_uname.strip()

                        if not new_uname:
                            st.error("❌ Tên đăng nhập không được để trống!")
                        elif not ed_fullname.strip() or not ed_mail.strip() or not ed_zalo.strip():
                            st.error("❌ Vui lòng điền đủ Họ tên, Email và Số điện thoại Zalo!")
                        elif new_uname != old_uname and any(u.get("username", "").strip().lower() == new_uname.lower() for u in all_users if u.get("username", "").strip() != old_uname):
                            st.error(f"❌ Tên đăng nhập '{new_uname}' đã tồn tại! Vui lòng chọn Tên đăng nhập khác.")
                        else:
                            updated_user = {
                                "username": new_uname,
                                "password": ed_pass.strip() if ed_pass.strip() else target_user.get("password", "123456"),
                                "full_name": ed_fullname.strip(),
                                "email": ed_mail.strip(),
                                "zalo": ed_zalo.strip(),
                                "department": ed_dept,
                                "role": ed_role,
                                "status": target_user.get("status", "active")
                            }

                            # Loại bỏ bản ghi cũ và thêm bản ghi mới để không bị trùng lặp
                            updated_user_list = [u for u in all_users if u.get("username", "").strip() != old_uname]
                            updated_user_list.append(updated_user)

                            # Đồng bộ các hợp đồng liên quan nếu đổi Tên đăng nhập
                            if new_uname != old_uname:
                                all_contracts = get_contracts()
                                contracts_synced = False
                                for c in all_contracts:
                                    if c.get("created_by") == old_uname:
                                        c["created_by"] = new_uname
                                        contracts_synced = True
                                    if c.get("assigned_to") == old_uname:
                                        c["assigned_to"] = new_uname
                                        contracts_synced = True
                                if contracts_synced:
                                    save_contracts(all_contracts)

                            # Cập nhật session_state nếu chính tài khoản này đang đăng nhập
                            if st.session_state.get("user", {}).get("username") == old_uname:
                                st.session_state["user"] = updated_user
                                st.session_state["role"] = ed_role

                            if save_users(updated_user_list):
                                if new_uname != old_uname:
                                    st.success(f"🎉 Đã đổi Tên đăng nhập từ '{old_uname}' ➔ '{new_uname}' và cập nhật thông tin thành công!")
                                else:
                                    st.success(f"🎉 Đã cập nhật thành công thông tin nhân sự '{ed_fullname}'!")
                                st.rerun()

        with sub_tab_del:
            st.markdown("##### 🗑️ Xóa Tài Khoản Nhân Sự")
            if all_users:
                current_login_uname = st.session_state.get("user", {}).get("username", "admin")
                del_opts = [f"{u.get('username')} - {u.get('full_name')} [{u.get('role')}]" for u in all_users if u.get("username") != current_login_uname]
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
                    st.info("Không thể xóa chính tài khoản bạn đang đăng nhập.")

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
# 8. BƯỚC 3: HÀM DEPARTMENT_VIEW() - HỖ TRỢ ĐIỀU HƯỚNG TRÌNH / THEO DÕI HỒ SƠ
# ==============================================================================
def department_view(active_tab: str = None):
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "khach")
    current_fullname = current_user.get("full_name", "Cán bộ đề xuất")
    current_department = current_user.get("department", "Phòng ban đề nghị")

    st.title("📑 Cổng Nộp & Quản Lý Hồ Sơ Hợp Đồng")
    st.markdown(f"Đơn vị đề xuất: **{current_department}** | Cán bộ phụ trách: **{current_fullname}** (`@{current_username}`)")

    if active_tab == "submit":
        tab_submit_contract, tab_my_contracts = st.tabs(["📤 Nộp Hồ Sơ Hợp Đồng Mới", "📂 Hồ Sơ Hợp Đồng Đã Gửi"])
    else:
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
                    "workflow_id": matched_wf.get("id"),
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
                st.success(f"Nộp hồ sơ thành công! Mã hồ sơ của bạn là: {contract_code}")
                st.rerun()

# ==============================================================================
# 9. BƯỚC 4: HÀM LEGAL_STAFF_VIEW() - PHÁP CHẾ RÀ SOÁT & TÍCH HỢP AI GEMINI
# ==============================================================================
def legal_staff_view(active_tab: str = None):
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

    # Cơ chế xác định chuyên viên / phạm vi xem hồ sơ thông minh
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

    if active_tab == "history":
        tab_history, tab_reviewing = st.tabs([
            "📜 Lịch sử rà soát",
            "🔍 Đang rà soát"
        ])
    else:
        tab_reviewing, tab_history = st.tabs([
            "🔍 Đang rà soát",
            "📜 Lịch sử rà soát"
        ])

    # ==========================================================================
    # TAB 1: ĐANG RÀ SOÁT
    # ==========================================================================
    with tab_reviewing:
        if view_scope_all:
            active_contracts = [c for c in all_contracts if c.get("status") == "Đang rà soát"]
        else:
            active_contracts = [
                c for c in all_contracts
                if c.get("status") == "Đang rà soát" and c.get("assigned_to") == target_username
            ]
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
            st.info("Hiện tại không có hồ sơ nào ở trạng thái **'Đang rà soát'** phù hợp với bộ lọc hiện tại.")
            st.markdown(
                """
                <div style="margin-top: 10px; padding: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.85rem; color: #475569;">
                    💡 <b>Gợi ý kiểm tra:</b><br/>
                    • Đăng nhập tài khoản Giám đốc (<code>giamdoc01</code> / <code>gd123</code>) để phân công hồ sơ.<br/>
                    • Đăng nhập tài khoản <code>phapche01</code> (Mật khẩu: <code>pc123</code>) để thao tác trực tiếp.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
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
            col_left, col_right = st.columns([1, 1])

            # ------------------------------------------------------------------
            # CỘT TRÁI: XEM FILE PDF TRỰC TIẾP
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
                    if selected_att_idx >= len(attachments):
                        selected_att_idx = 0

                    chosen_attachment = attachments[selected_att_idx]
                    base64_content = chosen_attachment.get("file_base64", "").strip()

                    if base64_content:
                        clean_base64 = base64_content
                        if "base64," in clean_base64:
                            clean_base64 = clean_base64.split("base64,", 1)[1]
                        clean_base64 = "".join(clean_base64.split())

                        data_uri = f"data:application/pdf;base64,{clean_base64}"
                        f_name = chosen_attachment.get('file_name', 'tai_lieu.pdf')

                        try:
                            file_bytes = base64.b64decode(clean_base64)
                            file_size_kb = len(file_bytes) / 1024
                        except Exception:
                            file_bytes = None
                            file_size_kb = chosen_attachment.get("file_size", 0) / 1024

                        st.markdown(
                            f"""
                            <div style="border-radius: 10px; overflow: hidden; border: 1px solid #CBD5E1; background: #FFFFFF; margin-top: 8px; margin-bottom: 8px;">
                                <div style="background-color: #F8FAFC; padding: 8px 12px; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                                        📄 {f_name} ({file_size_kb:.1f} KB) - Mục: [{chosen_attachment.get('checklist_item')}]
                                    </span>
                                    <a href="{data_uri}" target="_blank" download="{f_name}" style="font-size: 0.78rem; font-weight: 600; color: #2563EB; text-decoration: none; background: #EFF6FF; padding: 3px 8px; border-radius: 4px; border: 1px solid #BFDBFE;">↗️ Tải / Mở tệp</a>
                                </div>
                                <object data="{data_uri}#toolbar=1" type="application/pdf" width="100%" height="520px" style="border: none; display: block;">
                                    <embed src="{data_uri}#toolbar=1" type="application/pdf" width="100%" height="520px" />
                                    <iframe src="{data_uri}" width="100%" height="520px" style="border: none;">
                                        <div style="padding: 16px; text-align: center; color: #64748B; font-size: 0.85rem;">
                                            Tệp PDF tiếng Việt sẵn sàng.<br/>
                                            <a href="{data_uri}" download="{f_name}" style="color: #2563EB; font-weight: bold;">Nhấp vào đây để tải tệp PDF về máy</a>
                                        </div>
                                    </iframe>
                                </object>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if file_bytes:
                            st.download_button(
                                label=f"📥 Tải tệp '{f_name}' về máy kiểm tra",
                                data=file_bytes,
                                file_name=f_name,
                                mime="application/pdf",
                                key=f"btn_dl_pdf_{selected_contract.get('id')}_{selected_att_idx}",
                                use_container_width=True
                            )
                    else:
                        st.info("Tệp đính kèm không có dữ liệu nội dung base64.")

            # ------------------------------------------------------------------
            # CỘT PHẢI: CHECKLIST, TRỢ LÝ AI GEMINI & TRÌNH GIÁM ĐỐC
            # ------------------------------------------------------------------
            with col_right:
                st.markdown("#### ⚖️ Thẩm Định Hồ Sơ & Đánh Giá Checklist")
                all_workflows = get_workflows()
                wf_match = next((w for w in all_workflows if w.get("id") == selected_contract.get("workflow_id")), None)
                req_checklist = wf_match.get("checklist", []) if wf_match else ["Dự thảo Hợp đồng chi tiết", "Tài liệu khác"]

                checklist_results = {}
                for idx_item, chk_item in enumerate(req_checklist, 1):
                    with st.container():
                        st.markdown(f"**{idx_item}. {chk_item}**")
                        c_radio, c_comm = st.columns([1.2, 1.8])
                        with c_radio:
                            status_choice = st.radio(
                                label=f"Trạng thái đánh giá cho {chk_item}:",
                                options=["Đạt", "Không đạt", "Có góp ý"],
                                horizontal=True,
                                key=f"rad_{selected_contract.get('id')}_{idx_item}",
                                label_visibility="collapsed"
                            )
                        with c_comm:
                            comment_text = ""
                            if status_choice == "Có góp ý":
                                comment_text = st.text_input(
                                    label=f"Nội dung góp ý cho {chk_item}:",
                                    placeholder="Ghi rõ nội dung cần điều chỉnh hoặc lưu ý...",
                                    key=f"txt_{selected_contract.get('id')}_{idx_item}",
                                    label_visibility="collapsed"
                                )
                            elif status_choice == "Không đạt":
                                comment_text = st.text_input(
                                    label=f"Lý do không đạt cho {chk_item}:",
                                    placeholder="Lý do hồ sơ không đạt chuẩn...",
                                    key=f"txt_fail_{selected_contract.get('id')}_{idx_item}",
                                    label_visibility="collapsed"
                                )
                        checklist_results[chk_item] = {"status": status_choice, "comment": comment_text.strip()}
                        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

                st.markdown("---")

                # TÍCH HỢP TRỢ LÝ AI GEMINI
                with st.expander("🤖 Trợ lý AI Gemini: Rà Soát Điều Khoản & Rủi Ro Pháp Lý", expanded=False):
                    st.caption("Sử dụng Google Gemini API để tự động phát hiện rủi ro, lỗ hổng cam kết bồi thường và kiến nghị điều khoản bảo vệ doanh nghiệp.")
                    default_gemini_key = os.environ.get("GEMINI_API_KEY", "") or get_config().get("gemini_api_key", "")
                    input_api_key = st.text_input("Gemini API Key:", value=default_gemini_key, type="password", key=f"gemini_k_{selected_contract.get('id')}")
                    clause_to_review = st.text_area("Nội dung điều khoản cần rà soát rủi ro:", placeholder="Dán nội dung điều khoản hợp đồng cần thẩm định vào đây...", key=f"clause_txt_{selected_contract.get('id')}", height=120)

                    if st.button("🔍 Phân Tích Rủi Ro Bằng AI Gemini", key=f"btn_ai_{selected_contract.get('id')}", use_container_width=True):
                        if not input_api_key.strip():
                            st.error("Vui lòng nhập Gemini API Key!")
                        elif not clause_to_review.strip():
                            st.warning("Vui lòng dán nội dung điều khoản cần phân tích!")
                        else:
                            with st.spinner("AI Gemini đang phân tích rủi ro và đối chiếu chuẩn pháp lý..."):
                                try:
                                    genai.configure(api_key=input_api_key.strip())
                                    ai_model = genai.GenerativeModel("gemini-1.5-flash")
                                    ai_prompt = (
                                        "Bạn là Luật sư cao cấp và Trưởng phòng Pháp chế doanh nghiệp Việt Nam. "
                                        "Hãy phân tích điều khoản hợp đồng sau: "
                                        f"\n\n'''{clause_to_review.strip()}'''\n\n"
                                        "Nêu rõ: 1) Các rủi ro tiềm ẩn cho doanh nghiệp; 2) Lỗ hổng pháp lý/bất lợi thương mại; 3) Kiến nghị phương án sửa đổi chi tiết theo Luật Doanh nghiệp & Thương mại hiện hành."
                                    )
                                    ai_response = ai_model.generate_content(ai_prompt)
                                    st.markdown(
                                        f"""
                                        <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #10B981; border-radius: 8px; padding: 14px; margin-top: 10px;">
                                            <div style="font-weight: 700; color: #047857; margin-bottom: 8px;">📊 Báo cáo Rà soát Rủi ro từ AI Gemini:</div>
                                            <div style="font-size: 0.9rem; color: #1E293B;">{ai_response.text}</div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                except Exception as gemini_err:
                                    st.error(f"Lỗi khi gọi API Gemini: {str(gemini_err)}")

                st.markdown("---")
                gen_assessment = st.selectbox(
                    "Đánh giá tổng quát của Pháp chế: *",
                    [
                        "Đủ điều kiện pháp lý - Đề xuất ký",
                        "Cần điều chỉnh và bổ sung",
                        "Không đủ điều kiện pháp lý"
                    ],
                    key=f"gen_assess_{selected_contract.get('id')}"
                )

                conclusion_notes = st.text_area(
                    "Ý kiến kết luận & Kiến nghị của Pháp chế: *",
                    placeholder="Ghi rõ nhận xét tổng quát, các lưu ý cần thực hiện trước khi phát hành...",
                    key=f"notes_{selected_contract.get('id')}",
                    height=90
                )

                if st.button("📤 Hoàn Tất Thẩm Định & Trình Giám Đốc Duyệt", type="primary", use_container_width=True, key=f"btn_submit_dir_{selected_contract.get('id')}"):
                    if not conclusion_notes.strip():
                        st.error("Vui lòng nhập Ý kiến kết luận của Pháp chế trước khi trình duyệt!")
                    else:
                        selected_contract["status"] = "Chờ Giám đốc duyệt"
                        selected_contract["legal_review"] = {
                            "reviewer": current_username,
                            "reviewer_name": current_fullname,
                            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "general_assessment": gen_assessment,
                            "summary_notes": conclusion_notes.strip(),
                            "checklist_results": checklist_results
                        }
                        if save_contracts(all_contracts):
                            st.success(
                                f"🎉 Đã hoàn tất thẩm định hồ sơ '{selected_contract.get('id')}'!\n\n"
                                f"Trạng thái đã được chuyển thành: **'Chờ Giám đốc duyệt'**."
                            )
                            st.rerun()

    # ==========================================================================
    # TAB 2: LỊCH SỬ RÀ SOÁT
    # ==========================================================================
    with tab_history:
        st.subheader("📜 Lịch Sử Thẩm Định Của Chuyên Viên")
        if view_scope_all:
            history_contracts = [
                c for c in all_contracts
                if c.get("legal_review") and c.get("status") != "Đang rà soát"
            ]
        else:
            history_contracts = [
                c for c in all_contracts
                if c.get("legal_review") and c.get("legal_review", {}).get("reviewer") == target_username
            ]

        if not history_contracts:
            st.info("Chưa có hồ sơ nào trong lịch sử thẩm định của bạn.")
        else:
            for h_c in history_contracts:
                l_rev = h_c.get("legal_review", {})
                with st.expander(f"📁 {h_c.get('id')}: {h_c.get('title')} — Trạng thái: [{h_c.get('status')}]"):
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        st.write(f"**Đối tác:** {h_c.get('partner_name')}")
                        st.write(f"**Phòng ban đề xuất:** {h_c.get('department')}")
                        st.write(f"**Giá trị:** {h_c.get('value_vnd', 0):,.0f} VNĐ")
                    with col_h2:
                        st.write(f"**Chuyên viên thẩm định:** {l_rev.get('reviewer_name')} (`@{l_rev.get('reviewer')}`)")
                        st.write(f"**Thời gian thẩm định:** {l_rev.get('reviewed_at')}")
                        st.write(f"**Đánh giá tổng quát:** **{l_rev.get('general_assessment')}**")

                    summary_opinion = l_rev.get('summary_notes', 'Không có ghi chú.')
                    st.info(f"💡 **Ý kiến kết luận:** {summary_opinion}")

                    st.markdown("**Kết quả checklist chi tiết:**")
                    for chk_name, chk_res in l_rev.get("checklist_results", {}).items():
                        c_stat = chk_res.get("status", "N/A")
                        c_com = chk_res.get("comment", "")
                        st.markdown(f"- **{chk_name}**: [{c_stat}] {f'*(Ghi chú: {c_com})*' if c_com else ''}")

# ==============================================================================
# 10. HÀM TẠO FILE PDF & GỬI EMAIL THÔNG BÁO TỰ ĐỘNG
# ==============================================================================
class UnicodeLegalPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        # Nạp font Unicode Arial tiếng Việt
        font_regular = "Arial.ttf" if os.path.exists("Arial.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font_bold = "Arial-Bold.ttf" if os.path.exists("Arial-Bold.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        if os.path.exists(font_regular):
            self.add_font("VN_Font", "", font_regular, uni=True)
            self.has_vn_font = True
        else:
            self.has_vn_font = False

        if os.path.exists(font_bold):
            self.add_font("VN_Font", "B", font_bold, uni=True)
            self.has_vn_bold = True
        else:
            self.has_vn_bold = False

    def header(self):
        if hasattr(self, "has_vn_font") and self.has_vn_font:
            self.set_font("VN_Font", "B", 11)
            self.cell(0, 7, "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU - PHÒNG PHÁP CHẾ", ln=True, align="C")
            self.set_font("VN_Font", "", 9)
            self.cell(0, 5, "HỆ THỐNG QUẢN LÝ VÀ PHÊ DUYỆT PHÁP CHẾ HỢP ĐỒNG", ln=True, align="C")
            self.line(15, 24, 195, 24)
            self.ln(6)
        else:
            self.set_font("Helvetica", "B", 10)
            self.cell(0, 6, "ENTERPRISE LEGAL REVIEW SYSTEM", ln=True, align="C")
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        if hasattr(self, "has_vn_font") and self.has_vn_font:
            self.set_font("VN_Font", "", 8)
            self.cell(0, 10, f"Trang {self.page_no()}/{{nb}} - Phiếu góp ý hợp đồng phát hành từ hệ thống nội bộ", align="C")
        else:
            self.set_font("Helvetica", "", 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def generate_review_pdf(contract: dict, action_type: str, director_notes: str, director_name: str) -> bytes:
    try:
        pdf = UnicodeLegalPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        f_name = "VN_Font" if getattr(pdf, "has_vn_font", False) else "Helvetica"

        # Tiêu đề tài liệu
        pdf.set_font(f_name, "B", 15)
        pdf.ln(3)
        title_text = "PHIẾU ĐÁNH GIÁ & GÓP Ý PHÁP LÝ HỢP ĐỒNG"
        pdf.cell(0, 10, title_text, ln=True, align="C")
        pdf.ln(2)

        # 1. THÔNG TIN HỢP ĐỒNG
        pdf.set_font(f_name, "B", 11)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 7, "I. THÔNG TIN CHUNG HỒ SƠ HỢP ĐỒNG", ln=True, fill=True)
        pdf.ln(2)

        pdf.set_font(f_name, "", 10)
        pdf.cell(45, 6, "• Mã hồ sơ hợp đồng:", 0, 0)
        pdf.set_font(f_name, "B", 10)
        pdf.cell(0, 6, str(contract.get("id", "N/A")), ln=True)

        pdf.set_font(f_name, "", 10)
        pdf.cell(45, 6, "• Tên dự thảo hợp đồng:", 0, 0)
        pdf.set_font(f_name, "B", 10)
        pdf.multi_cell(0, 6, str(contract.get("title", "N/A")))

        pdf.set_font(f_name, "", 10)
        pdf.cell(45, 6, "• Đối tác / Khách hàng:", 0, 0)
        pdf.cell(0, 6, str(contract.get("partner_name", "N/A")), ln=True)

        pdf.cell(45, 6, "• Đơn vị đề xuất:", 0, 0)
        pdf.cell(0, 6, f"{contract.get('department', 'N/A')} (Cán bộ: @{contract.get('created_by', 'N/A')})", ln=True)

        val_vnd = contract.get("value_vnd", 0)
        pdf.cell(45, 6, "• Giá trị hợp đồng:", 0, 0)
        pdf.cell(0, 6, f"{val_vnd:,.0f} VNĐ", ln=True)

        pdf.cell(45, 6, "• Thời hạn hiệu lực:", 0, 0)
        pdf.cell(0, 6, f"Từ {contract.get('effective_date', 'N/A')} đến {contract.get('expiration_date', 'N/A')}", ln=True)
        pdf.ln(4)

        # 2. Ý KIẾN THẨM ĐỊNH CỦA PHÒNG PHÁP CHẾ
        legal_rev = contract.get("legal_review", {})
        pdf.set_font(f_name, "B", 11)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 7, "II. KẾT QUẢ RÀ SOÁT CỦA PHÒNG PHÁP CHẾ", ln=True, fill=True)
        pdf.ln(2)

        pdf.set_font(f_name, "", 10)
        pdf.cell(45, 6, "• Chuyên viên thẩm định:", 0, 0)
        pdf.cell(0, 6, f"{legal_rev.get('reviewer_name', 'Chuyên viên')} (@{legal_rev.get('reviewer', 'N/A')})", ln=True)

        pdf.cell(45, 6, "• Thời gian hoàn tất:", 0, 0)
        pdf.cell(0, 6, str(legal_rev.get("reviewed_at", "N/A")), ln=True)

        pdf.cell(45, 6, "• Kết luận chuyên môn:", 0, 0)
        pdf.set_font(f_name, "B", 10)
        pdf.cell(0, 6, str(legal_rev.get("general_assessment", "Chưa có đánh giá")), ln=True)

        pdf.set_font(f_name, "", 10)
        pdf.cell(45, 6, "• Chi tiết ý kiến góp ý:", 0, 0)
        pdf.multi_cell(0, 6, str(legal_rev.get("summary_notes", "Không có ghi chú thêm.")))
        pdf.ln(3)

        # 3. KẾT QUẢ CHECKLIST HỒ SƠ
        chk_res = legal_rev.get("checklist_results", {})
        if chk_res:
            pdf.set_font(f_name, "B", 9)
            pdf.set_fill_color(226, 232, 240)
            pdf.cell(90, 6, "Hạng mục tài liệu hồ sơ", border=1, fill=True)
            pdf.cell(35, 6, "Đánh giá", border=1, fill=True, align="C")
            pdf.cell(55, 6, "Góp ý chi tiết", border=1, fill=True)
            pdf.ln()

            pdf.set_font(f_name, "", 8)
            for it_name, it_data in chk_res.items():
                pdf.cell(90, 6, str(it_name)[:50], border=1)
                pdf.cell(35, 6, str(it_data.get("status", "Đạt")), border=1, align="C")
                pdf.cell(55, 6, str(it_data.get("comment", ""))[:35], border=1)
                pdf.ln()
            pdf.ln(4)

        # 4. QUYẾT ĐỊNH CỦA GIÁM ĐỐC
        pdf.set_font(f_name, "B", 11)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 7, "III. KẾT LUẬN & CHỈ ĐẠO CỦA GIÁM ĐỐC PHÁP CHẾ", ln=True, fill=True)
        pdf.ln(2)

        action_display = "ĐỒNG Ý KÝ DUYỆT PHÁT HÀNH" if action_type == "approve" else "YÊU CẦU ĐIỀU CHỈNH & LÀM LẠI"
        pdf.set_font(f_name, "B", 10)
        pdf.cell(45, 6, "• Quyết định phê duyệt:", 0, 0)
        pdf.cell(0, 6, action_display, ln=True)

        pdf.set_font(f_name, "", 10)
        pdf.cell(45, 6, "• Ý kiến chỉ đạo:", 0, 0)
        pdf.multi_cell(0, 6, director_notes.strip() if director_notes else "Đồng ý theo kết quả thẩm định.")
        pdf.ln(8)

        # Chữ ký xác nhận
        pdf.set_font(f_name, "B", 10)
        pdf.cell(100, 5, "", 0, 0)
        pdf.cell(80, 5, "GIÁM ĐỐC PHÁP CHẾ", 0, 1, "C")
        pdf.set_font(f_name, "", 9)
        pdf.cell(100, 5, "", 0, 0)
        pdf.cell(80, 5, "(Đã ký điện tử và xác thực trên hệ thống)", 0, 1, "C")
        pdf.ln(12)
        pdf.set_font(f_name, "B", 10)
        pdf.cell(100, 5, "", 0, 0)
        pdf.cell(80, 5, director_name, 0, 1, "C")

        return bytes(pdf.output())
    except Exception as pdf_err:
        st.error(f"Lỗi tạo tệp PDF: {pdf_err}")
        return b"%PDF-1.4 dummy pdf bytes"

def send_approval_email(contract: dict, pdf_bytes: bytes, pdf_filename: str, action_type: str, director_notes: str) -> tuple:
    system_cfg = get_config()
    smtp_data = system_cfg.get("smtp_settings", {})
    server_host = smtp_data.get("server", "smtp.gmail.com")
    server_port = int(smtp_data.get("port", 587))
    sender_mail = smtp_data.get("sender_email", "")
    app_pwd = smtp_data.get("app_password", "")
    use_tls = smtp_data.get("use_tls", True)

    users_db = get_users()
    creator_uname = contract.get("created_by", "")
    creator_obj = next((u for u in users_db if u.get("username") == creator_uname), None)
    to_mail = creator_obj.get("email") if creator_obj else f"{creator_uname}@congty.com.vn"

    if not sender_mail or not app_pwd:
        return (False, "Chưa thiết lập App Password cho Email trong config.json (đã bỏ qua gửi email). Đã xuất file PDF thành công!")

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_mail
        msg["To"] = to_mail
        action_vn = "KÝ DUYỆT PHÁT HÀNH" if action_type == "approve" else "YÊU CẦU LÀM LẠI"
        msg["Subject"] = f"[{action_vn}] Thông báo kết quả phê duyệt hồ sơ: {contract.get('id')} - {contract.get('title')}"

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h3 style="color: #1E3A8A;">THÔNG BÁO TỪ PHÒNG PHÁP CHẾ</h3>
            <p>Kính gửi: <b>{contract.get('department')}</b> (Cán bộ đề xuất: <b>@{creator_uname}</b>),</p>
            <p>Hồ sơ hợp đồng: <b>{contract.get('id')} - {contract.get('title')}</b> đã được Giám đốc Pháp chế xử lý.</p>
            <div style="background-color: #F1F5F9; border-left: 4px solid #2563EB; padding: 12px; margin: 15px 0;">
                <p style="margin: 0;"><b>Kết quả:</b> <span style="color: {'#16A34A' if action_type == 'approve' else '#DC2626'}; font-weight: bold;">{action_vn}</span></p>
                <p style="margin: 5px 0 0 0;"><b>Ý kiến chỉ đạo của Giám đốc:</b> <i>"{director_notes}"</i></p>
            </div>
            <p>Tệp <b>'Phiếu đánh giá & góp ý pháp lý hợp đồng'</b> định dạng PDF đã được đính kèm thư này.</p>
            <br/>
            <p style="font-size: 0.85rem; color: #64748B;">Hệ thống Quản lý và Thẩm định Pháp chế Hợp đồng tự động.</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        if pdf_bytes:
            part = MIMEApplication(pdf_bytes, Name=pdf_filename)
            part["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
            msg.attach(part)

        server = smtplib.SMTP(server_host, server_port, timeout=10)
        if use_tls: server.starttls()
        server.login(sender_mail, app_pwd)
        server.sendmail(sender_mail, [to_mail], msg.as_string())
        server.quit()
        return (True, f"Đã gửi email thông báo kèm tệp PDF thành công tới: {to_mail}!")
    except Exception as smtp_error:
        return (False, f"Lỗi gửi email qua {server_host}:{server_port} ({str(smtp_error)}). Đã lưu phiếu góp ý PDF thành công!")

# ==============================================================================
# 11. BƯỚC 5 & 6: HÀM DIRECTOR_VIEW() HOÀN CHỈNH - HỖ TRỢ CHẾ ĐỘ READ-ONLY (GOD MODE)
# ==============================================================================
def director_view(readonly: bool = False, active_tab: str = None):
    """
    Giao diện Quản trị Dành cho Giám đốc Pháp chế & Giám sát Read-Only dành cho Admin:
    Hàm gồm 4 Tab chi tiết:
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

    if readonly:
        st.title("🛡️ Giám Sát Hệ Thống Hợp Đồng (Read-Only Mode)")
        st.markdown(
            """
            <div style="background: #FEF3C7; border: 1.5px solid #F59E0B; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
                <div style="font-size: 0.95rem; font-weight: 800; color: #92400E;">👑 CHẾ ĐỘ GIÁM SÁT DÀNH CHO ADMIN (READ-ONLY / GOD MODE)</div>
                <div style="font-size: 0.84rem; color: #78350F; margin-top: 4px;">
                    Bạn đang giám sát toàn bộ hoạt động của hệ thống với quyền Quản trị viên (Admin). Bạn có quyền tra cứu Dashboard thống kê, xem danh sách hồ sơ, đọc tệp PDF hợp đồng đính kèm và xem phiếu thẩm định của Pháp chế.<br/>
                    <b>Tất cả các nút hành động (Phân công, Điều chuyển, Ký duyệt, Yêu cầu làm lại) đã được vô hiệu hóa để bảo đảm tính độc lập chuyên môn của Phòng Pháp chế.</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.title("👑 Bàn Làm Việc Giám Đốc Pháp Chế")
        st.markdown(
            f"Lãnh đạo phụ trách: **{current_fullname}** (`@{current_username}`) | "
            f"Bộ phận: **{current_user.get('department', 'Ban Giám đốc')}**"
        )

    if readonly:
        tab_stats, tab_assign, tab_transfer, tab_approve = st.tabs([
            "📊 Dashboard Thống kê",
            "📋 Giám sát Phân công",
            "🔄 Giám sát Điều chuyển",
            "✍️ Giám sát Phê duyệt & Hồ sơ"
        ])
    elif active_tab == "assign":
        tab_assign, tab_transfer, tab_approve, tab_stats = st.tabs([
            "📋 Phân công hồ sơ",
            "🔄 Điều chuyển nhân sự",
            "✍️ Phê duyệt & Ban hành",
            "📊 Dashboard Thống kê"
        ])
    elif active_tab == "approve":
        tab_approve, tab_stats, tab_assign, tab_transfer = st.tabs([
            "✍️ Phê duyệt & Ban hành",
            "📊 Dashboard Thống kê",
            "📋 Phân công hồ sơ",
            "🔄 Điều chuyển nhân sự"
        ])
    else:
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
            df_contracts = pd.DataFrame(all_contracts)

            # Tính toán các chỉ số
            total_contracts = len(df_contracts)
            pending_assign = len(df_contracts[df_contracts["status"] == "Chờ Giám đốc phân công"])
            in_review = len(df_contracts[df_contracts["status"] == "Đang rà soát"])
            completed = len(df_contracts[df_contracts["status"].isin(["Chờ Giám đốc duyệt", "Đã duyệt", "Đã ký kết", "Hoàn tất"])])

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

            with st.expander("📋 Xem danh sách bảng dữ liệu chi tiết", expanded=False):
                view_cols = ["id", "title", "partner_name", "department", "value_vnd", "status", "assigned_to"]
                avail_cols = [col for col in view_cols if col in df_contracts.columns]
                st.dataframe(df_contracts[avail_cols], use_container_width=True)

    # ==========================================================================
    # TAB 2: PHÂN CÔNG HỒ SƠ
    # ==========================================================================
    with tab_assign:
        st.subheader("📋 Phân Công Hồ Sơ Cho Chuyên Viên Pháp Chế")
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
                legal_candidates = [
                    u for u in all_users
                    if u.get("department") == "Phòng Pháp chế" or "Pháp chế" in u.get("role", "")
                ]
                if not legal_candidates:
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
                if readonly:
                    st.button(
                        "🔒 Giao Việc Cho Pháp Chế (Vô hiệu hóa trong chế độ Read-Only)",
                        disabled=True,
                        use_container_width=True,
                        key=f"btn_assign_confirm_{target_contract.get('id')}"
                    )
                    st.caption("🛡️ Quyền Read-Only: Tài khoản Admin chỉ giám sát, không can thiệp giao việc thay Giám đốc.")
                    btn_do_assign = False
                else:
                    btn_do_assign = st.button(
                        "🚀 Giao Việc & Chuyển Sang Trạng Thái 'Đang Rà Soát'",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_assign_confirm_{target_contract.get('id')}"
                    )

                if btn_do_assign:
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
    # TAB 3: ĐIỀU CHUYỂN
    # ==========================================================================
    with tab_transfer:
        st.subheader("🔄 Điều Chuyển Hồ Sơ Đang Rà Soát")
        st.markdown(
            "Chức năng dành cho Giám đốc điều phối lại nhân sự phụ trách khi chuyên viên cũ quá tải, "
            "nghỉ phép hoặc cần phân bổ lại cho nhân sự có chuyên môn phù hợp."
        )

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

                reassignment_hist = transfer_contract.get("reassignment_history", [])
                if reassignment_hist:
                    st.markdown("##### 📜 Lịch sử các lần điều chuyển trước:")
                    for h_idx, h_item in enumerate(reassignment_hist, 1):
                        st.markdown(
                            f"""
                            <div style="font-size: 0.8rem; background: #F1F5F9; border-radius: 6px; padding: 6px 10px; margin-bottom: 4px;">
                                <b>Lần {h_idx}:</b> Từ <code>@{h_item.get('from_user')}</code> sang <code>@{h_item.get('to_user')}</code> | 🕒 {h_item.get('timestamp')}<br/>
                                <i>Lý do: {h_item.get('reason')}</i>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            with col_t2:
                st.markdown("##### 🔄 Chọn chuyên viên mới & Nhập lý do điều chuyển:")
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
                if readonly:
                    st.button(
                        "🔒 Xác Nhận Điều Chuyển Hồ Sơ (Vô hiệu hóa trong chế độ Read-Only)",
                        disabled=True,
                        use_container_width=True,
                        key=f"btn_transfer_confirm_{transfer_contract.get('id')}"
                    )
                    st.caption("🛡️ Quyền Read-Only: Tài khoản Admin chỉ giám sát, không thực hiện điều chuyển.")
                    btn_do_transfer = False
                else:
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
                        old_assignee = current_assignee_username
                        new_assignee = chosen_new_candidate.get("username")

                        transfer_contract["assigned_to"] = new_assignee

                        if "reassignment_history" not in transfer_contract:
                            transfer_contract["reassignment_history"] = []

                        transfer_contract["reassignment_history"].append({
                            "from_user": old_assignee,
                            "from_user_name": current_assignee_name,
                            "to_user": new_assignee,
                            "to_user_name": chosen_new_candidate.get("full_name"),
                            "reassigned_by": current_username,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "reason": transfer_reason.strip()
                        })

                        if save_contracts(all_contracts):
                            st.success(
                                f"🎉 Đã điều chuyển hồ sơ **'{transfer_contract.get('id')}'** từ chuyên viên "
                                f"**{current_assignee_name}** sang **{chosen_new_candidate.get('full_name')}** (`@{new_assignee}`) thành công!"
                            )
                            st.rerun()

    # ==========================================================================
    # TAB 4: PHÊ DUYỆT & BAN HÀNH (BƯỚC 6)
    # ==========================================================================
    with tab_approve:
        st.subheader("✍️ Phê Duyệt Hồ Sơ Hợp Đồng & Phát Hành 'Phiếu Góp Ý Hợp Đồng'")
        waiting_approve_list = [c for c in all_contracts if c.get("status") == "Chờ Giám đốc duyệt"]

        if not waiting_approve_list:
            st.info("Hiện tại không có hồ sơ nào ở trạng thái **'Chờ Giám đốc duyệt'**.")
            st.markdown(
                """
                <div style="margin-top: 10px; padding: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.85rem; color: #475569;">
                    💡 Hồ sơ sẽ xuất hiện tại đây sau khi Chuyên viên Pháp chế hoàn tất thẩm định tại <b>Bàn làm việc Pháp chế (legal_staff_view)</b> và nhấn <i>'Trình Giám đốc duyệt'</i>.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            appr_labels = [
                f"{c.get('id')} — {c.get('title')} ({c.get('partner_name')} | Đề xuất: {c.get('department')})"
                for c in waiting_approve_list
            ]
            sel_appr_idx = st.selectbox(
                "Chọn hồ sơ cần xem xét và phê duyệt:",
                range(len(waiting_approve_list)),
                format_func=lambda i: appr_labels[i],
                key="sel_contract_to_approve"
            )
            appr_contract = waiting_approve_list[sel_appr_idx]

            st.markdown("---")
            col_review_left, col_review_right = st.columns([1, 1])

            with col_review_left:
                st.markdown("#### 📄 Xem Trực Tiếp Tệp Dự Thảo Hợp Đồng (Đối Chiếu)")
                appr_attachments = appr_contract.get("attachments", [])

                if not appr_attachments:
                    st.warning("Hồ sơ này không có tệp đính kèm nào được lưu trữ.")
                else:
                    appr_att_labels = [
                        f"{i+1}. [{att.get('checklist_item', 'Tài liệu')}]: {att.get('file_name', 'document.pdf')}"
                        for i, att in enumerate(appr_attachments)
                    ]
                    chosen_appr_att_idx = st.selectbox(
                        "Chọn tài liệu đính kèm để mở đọc đối chiếu:",
                        range(len(appr_attachments)),
                        format_func=lambda i: appr_att_labels[i],
                        key=f"sel_appr_att_{appr_contract.get('id')}"
                    )
                    chosen_appr_att = appr_attachments[chosen_appr_att_idx]
                    pdf_b64_str = chosen_appr_att.get("file_base64", "").strip()

                    if pdf_b64_str:
                        clean_appr_b64 = pdf_b64_str
                        if "base64," in clean_appr_b64:
                            clean_appr_b64 = clean_appr_b64.split("base64,", 1)[1]
                        clean_appr_b64 = "".join(clean_appr_b64.split())
                        appr_data_uri = f"data:application/pdf;base64,{clean_appr_b64}"
                        att_fname = chosen_appr_att.get("file_name", "hop_dong.pdf")

                        try:
                            pdf_raw_bytes = base64.b64decode(clean_appr_b64)
                            att_fsize_kb = len(pdf_raw_bytes) / 1024
                        except Exception:
                            pdf_raw_bytes = None
                            att_fsize_kb = chosen_appr_att.get("file_size", 0) / 1024

                        st.markdown(
                            f"""
                            <div style="border-radius: 10px; overflow: hidden; border: 1.5px solid #CBD5E1; background: #FFFFFF; margin-top: 8px; margin-bottom: 8px;">
                                <div style="background-color: #F8FAFC; padding: 8px 12px; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                                        📄 {att_fname} ({att_fsize_kb:.1f} KB) - Mục: [{chosen_appr_att.get('checklist_item')}]
                                    </span>
                                    <a href="{appr_data_uri}" target="_blank" download="{att_fname}" style="font-size: 0.78rem; font-weight: 600; color: #2563EB; text-decoration: none; background: #EFF6FF; padding: 3px 8px; border-radius: 4px; border: 1px solid #BFDBFE;">↗️ Tải / Mở tệp</a>
                                </div>
                                <object data="{appr_data_uri}#toolbar=1" type="application/pdf" width="100%" height="480px" style="border: none; display: block;">
                                    <embed src="{appr_data_uri}#toolbar=1" type="application/pdf" width="100%" height="480px" />
                                    <iframe src="{appr_data_uri}" width="100%" height="480px" style="border: none;">
                                        <div style="padding: 16px; text-align: center; color: #64748B; font-size: 0.85rem;">
                                            Tệp PDF tiếng Việt sẵn sàng.<br/>
                                            <a href="{appr_data_uri}" download="{att_fname}" style="color: #2563EB; font-weight: bold;">Nhấp vào đây để tải tệp PDF về máy</a>
                                        </div>
                                    </iframe>
                                </object>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if pdf_raw_bytes:
                            st.download_button(
                                label=f"📥 Tải tệp '{att_fname}' về máy",
                                data=pdf_raw_bytes,
                                file_name=att_fname,
                                mime="application/pdf",
                                key=f"dl_appr_att_{appr_contract.get('id')}_{chosen_appr_att_idx}",
                                use_container_width=True
                            )
                    else:
                        st.info("Tài liệu không có nội dung base64.")

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
                    value="Đồng ý thông qua nội dung dự thảo hợp đồng theo thẩm định của Phòng Pháp chế. Cho phép phát hành và tiến hành ký kết." if not readonly else "Chế độ Giám sát Hệ thống (Read-Only) - Chỉ tra cứu hồ sơ và phiếu thẩm định.",
                    height=85,
                    disabled=readonly,
                    key=f"dir_opinion_input_{appr_contract.get('id')}"
                )

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                col_btn_approve, col_btn_reject = st.columns(2)

                if readonly:
                    with col_btn_approve:
                        st.button(
                            "🔒 Ký duyệt phát hành (Disabled)",
                            disabled=True,
                            use_container_width=True,
                            key=f"btn_approve_action_{appr_contract.get('id')}"
                        )
                    with col_btn_reject:
                        st.button(
                            "🔒 Yêu cầu làm lại (Disabled)",
                            disabled=True,
                            use_container_width=True,
                            key=f"btn_reject_action_{appr_contract.get('id')}"
                        )
                    st.caption("🛡️ Quyền Read-Only: Admin chỉ có quyền tra cứu tài liệu và phiếu thẩm định, không được can thiệp workflow phê duyệt.")
                    btn_approve_action = False
                    btn_reject_action = False
                else:
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

                    pdf_result_bytes = generate_review_pdf(
                        contract=appr_contract,
                        action_type=action_key,
                        director_notes=dir_opinion.strip(),
                        director_name=current_fullname
                    )

                    email_ok, email_msg = send_approval_email(
                        contract=appr_contract,
                        pdf_bytes=pdf_result_bytes,
                        pdf_filename=pdf_filename,
                        action_type=action_key,
                        director_notes=dir_opinion.strip()
                    )

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

                # HIỆN NÚT TẢI FILE PDF TRÊN GIAO DIỆN (HOẠT ĐỘNG TRÊN CẢ READ-ONLY VÀ GIÁM ĐỐC)
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
# 12. ĐIỀU HƯỚNG TỔNG THỂ & RENDER_MAIN_DASHBOARD() (SIDEBAR ISOLATION)
# ==============================================================================
def render_main_dashboard():
    display_branding()

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
# 13. ĐIỂM BẮT ĐẦU CHÍNH (MAIN ENTRY POINT)
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
