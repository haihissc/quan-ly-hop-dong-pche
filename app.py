"""
================================================================================
HỆ THỐNG QUẢN LÝ VÀ THẨM ĐỊNH HỢP ĐỒNG PHÁP CHẾ DOANH NGHIỆP TẬP TRUNG
Enterprise Legal Contract Management & Intelligent Review System
Tech Lead Production Release - Full Pipeline Integration (Steps 1 to 6)
================================================================================
"""

import os
import sys
import json
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
import pandas as pd
import streamlit as st

# Cấu hình fpdf hỗ trợ Unicode Tiếng Việt
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# Cấu hình Google Gemini AI
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ==============================================================================
# 1. THIẾT LẬP CẤU HÌNH GIAO DIỆN STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Thẩm Định Hợp Đồng Pháp Chế",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Đường dẫn các tệp dữ liệu lưu trữ JSON
CONFIG_FILE = "config.json"
USERS_FILE = "users.json"
DEPTS_FILE = "departments.json"
WORKFLOWS_FILE = "workflows.json"
CONTRACTS_FILE = "contracts.json"

# ==============================================================================
# 2. BỘ HÀM TIỆN ÍCH QUẢN TRỊ DỮ LIỆU JSON (UTF-8 100%)
# ==============================================================================
def load_json_file(file_path: str, default_value=None):
    """Đọc dữ liệu từ file JSON với bảng mã utf-8 an toàn."""
    if default_value is None:
        default_value = []
    if not os.path.exists(file_path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default_value, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return default_value
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Lỗi khi đọc file '{file_path}': {str(e)}")
        return default_value

def save_json_file(file_path: str, data) -> bool:
    """Lưu dữ liệu ra file JSON với bảng mã utf-8 đảm bảo nguyên vẹn tiếng Việt."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Lỗi khi ghi dữ liệu vào '{file_path}': {str(e)}")
        return False

def get_config():
    cfg = load_json_file(CONFIG_FILE, {})
    if not cfg:
        cfg = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "legal-system@corporate.com.vn",
            "sender_password": "",
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "app_name": "Cổng Quản Trị & Thẩm Định Hợp Đồng Pháp Chế Doanh Nghiệp"
        }
        save_json_file(CONFIG_FILE, cfg)
    return cfg

def get_users():
    return load_json_file(USERS_FILE, [])

def save_users(data):
    return save_json_file(USERS_FILE, data)

def get_departments():
    return load_json_file(DEPTS_FILE, [])

def save_departments(data):
    return save_json_file(DEPTS_FILE, data)

def get_workflows():
    return load_json_file(WORKFLOWS_FILE, [])

def save_workflows(data):
    return save_json_file(WORKFLOWS_FILE, data)

def get_contracts():
    return load_json_file(CONTRACTS_FILE, [])

def save_contracts(data):
    return save_json_file(CONTRACTS_FILE, data)

# ==============================================================================
# 3. NHẬN DIỆN THƯƠNG HIỆU & BRANDING HEADER
# ==============================================================================
def display_branding():
    """Hàm hiển thị Header Thương hiệu & Khẩu hiệu pháp chế đầu trang."""
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #0F172A 100%); padding: 18px 24px; border-radius: 12px; margin-bottom: 22px; color: white; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div style="background: rgba(255,255,255,0.15); width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                    ⚖️
                </div>
                <div>
                    <h2 style="margin: 0; font-size: 1.45rem; font-weight: 800; letter-spacing: -0.02em; color: #FFFFFF;">HỆ THỐNG THẨM ĐỊNH HỢP ĐỒNG PHÁP CHẾ DOANH NGHIỆP</h2>
                    <p style="margin: 2px 0 0 0; font-size: 0.85rem; color: #93C5FD; font-weight: 500;">Bảo đảm an toàn pháp lý • Tối ưu quy trình phê duyệt • Chuẩn hóa rủi ro hợp đồng</p>
                </div>
            </div>
            <div style="text-align: right; font-size: 0.8rem; color: #CBD5E1; background: rgba(255,255,255,0.08); padding: 6px 12px; border-radius: 8px;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #10B981; border-radius: 50%; margin-right: 6px;"></span>
                Phiên bản: <b>v2.6 Enterprise</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
# ==============================================================================
# DANH SÁCH TÀI KHOẢN MẶC ĐỊNH HỆ THỐNG
# ==============================================================================
DEFAULT_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "full_name": "Quản trị viên Hệ thống",
        "role": "Admin",
        "department": "Ban Giám đốc",
        "email": "admin@congty.com.vn",
        "status": "active"
    },
    {
        "username": "giamdoc01",
        "password": "gd123",
        "full_name": "Trần Quang Thắng (Giám đốc)",
        "role": "Ban Giám đốc",
        "department": "Ban Giám đốc",
        "email": "thang.tq@congty.com.vn",
        "status": "active"
    },
    {
        "username": "phapche01",
        "password": "pc123",
        "full_name": "Nguyễn Văn Luật",
        "role": "Chuyên viên Pháp chế",
        "department": "Phòng Pháp chế",
        "email": "luat.nv@congty.com.vn",
        "status": "active"
    },
    {
        "username": "kinhdoanh01",
        "password": "kd123",
        "full_name": "Lê Hoàng Nam",
        "role": "Phòng ban đề nghị",
        "department": "Phòng Kinh doanh & Tiếp thị",
        "email": "nam.lh@congty.com.vn",
        "status": "active"
    }
]

def get_users(): 
    users = read_json_file(USERS_FILE, DEFAULT_USERS)
    if not users:  # Nếu file rỗng []
        users = DEFAULT_USERS
        save_users(users)
    return users
# ==============================================================================
# 4. LIST TÀI KHOẢN
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
            username_val = st.text_input("Tên đăng nhập", value=default_user, placeholder="admin / giamdoc01 / phapche01")
            password_val = st.text_input("Mật khẩu", type="password", value=default_pwd, placeholder="admin123 / gd123 / pc123")
            submit_login = st.form_submit_button("Đăng nhập hệ thống", use_container_width=True)

            if submit_login:
                u_input = username_val.strip()
                p_input = password_val.strip()

                # Kiểm tra tài khoản đối chiếu
                matched_account = next(
                    (u for u in user_list if u.get("username") == u_input and u.get("password") == p_input), 
                    None
                )

                # Fallback bảo đảm đặc quyền Admin và Ban Giám đốc luôn vào được
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
                • <b>Ban Giám đốc:</b> <code>giamdoc01</code> / <code>gd123</code><br/>
                • <b>Chuyên viên Pháp chế:</b> <code>phapche01</code> / <code>pc123</code><br/>
                • <b>Phòng ban đề xuất:</b> <code>kinhdoanh01</code> / <code>kd123</code>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# 4. MODULE TẠO FILE PDF 'PHIẾU GÓP Ý HỢP ĐỒNG' (FPDF UNICODE)
# ==============================================================================
class UnicodeContractPDF(FPDF):
    def header(self):
        self.set_font("DejaVu", "", 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 6, "BAN PHÁP CHẾ DOANH NGHIỆP - PHIẾU Ý KIẾN THẨM ĐỊNH HỢP ĐỒNG", 0, 1, "R")
        self.line(10, 16, 200, 16)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Trang {self.page_no()}/{{nb}} - Bản in điện tử có giá trị nội bộ", 0, 0, "C")

def generate_review_pdf(contract: dict, action_type: str, director_notes: str, director_name: str) -> bytes:
    """Tạo file PDF Phiếu góp ý Hợp đồng chuẩn tiếng Việt Unicode có xử lý font dự phòng."""
    if FPDF is None:
        return b"%PDF-1.4 Mock PDF Content"

    pdf = UnicodeContractPDF()
    pdf.alias_nb_pages()

    # Định vị font Unicode
    font_added = False
    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    possible_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    ]

    for f_path in possible_fonts:
        if os.path.exists(f_path):
            try:
                pdf.add_font("DejaVu", "", f_path, uni=True)
                font_added = True
                break
            except Exception:
                pass

    bold_added = False
    for fb_path in possible_bold:
        if os.path.exists(fb_path):
            try:
                pdf.add_font("DejaVu", "B", fb_path, uni=True)
                bold_added = True
                break
            except Exception:
                pass

    if not font_added:
        pdf.add_font("DejaVu", "", "", uni=True)

    font_family = "DejaVu" if font_added else "Arial"

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Tiêu đề Quốc hiệu
    pdf.set_font(font_family, "B" if bold_added else "", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", 0, 1, "C")
    pdf.set_font(font_family, "", 10)
    pdf.cell(0, 6, "Độc lập - Tự do - Hạnh phúc", 0, 1, "C")
    pdf.set_font(font_family, "", 9)
    pdf.cell(0, 4, "---------------------------------", 0, 1, "C")
    pdf.ln(4)

    # Tên văn bản
    pdf.set_font(font_family, "B" if bold_added else "", 14)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, "PHIẾU Ý KIẾN THẨM ĐỊNH & PHÊ DUYỆT HỢP ĐỒNG", 0, 1, "C")
    pdf.set_font(font_family, "", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 6, f"Mã hồ sơ: {contract.get('id', 'N/A')} | Ngày lập: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
    pdf.ln(4)

    # Khung Thông tin chung Hợp đồng
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(10, pdf.get_y(), 190, 42, "FD")
    start_box_y = pdf.get_y()

    pdf.set_y(start_box_y + 3)
    pdf.set_x(14)
    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(40, 6, "Tên Hợp đồng:", 0, 0)
    pdf.set_font(font_family, "", 10)
    pdf.multi_cell(130, 6, str(contract.get("title", "")))

    pdf.set_x(14)
    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(40, 6, "Loại hợp đồng:", 0, 0)
    pdf.set_font(font_family, "", 10)
    pdf.cell(50, 6, str(contract.get("type", "")), 0, 0)

    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(30, 6, "Đối tác:", 0, 0)
    pdf.set_font(font_family, "", 10)
    pdf.cell(50, 6, str(contract.get("partner_name", "")), 0, 1)

    pdf.set_x(14)
    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(40, 6, "Giá trị hợp đồng:", 0, 0)
    pdf.set_font(font_family, "", 10)
    val_vnd = contract.get("value_vnd", 0)
    pdf.cell(50, 6, f"{val_vnd:,.0f} VNĐ" if isinstance(val_vnd, (int, float)) else str(val_vnd), 0, 0)

    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(30, 6, "Phòng ban đề xuất:", 0, 0)
    pdf.set_font(font_family, "", 10)
    pdf.cell(50, 6, str(contract.get("department", "")), 0, 1)

    pdf.set_y(start_box_y + 46)

    # Đánh giá các mục Checklist của Pháp chế
    pdf.set_font(font_family, "B" if bold_added else "", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, "I. KẾT QUẢ RÀ SOÁT CHECKLIST CỦA CHUYÊN VIÊN PHÁP CHẾ", 0, 1)

    legal_review = contract.get("legal_review", {})
    checklist_results = legal_review.get("checklist_results", {})

    pdf.set_fill_color(226, 232, 240)
    pdf.set_font(font_family, "B" if bold_added else "", 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(10, 7, "STT", 1, 0, "C", True)
    pdf.cell(80, 7, "Nội dung kiểm tra pháp lý", 1, 0, "L", True)
    pdf.cell(30, 7, "Kết quả", 1, 0, "C", True)
    pdf.cell(70, 7, "Ý kiến chi tiết", 1, 1, "L", True)

    pdf.set_font(font_family, "", 9)
    if checklist_results:
        idx = 1
        for item_name, res in checklist_results.items():
            status_text = res.get("status", "Đạt")
            comment_text = res.get("comment", "") or "Không có ý kiến thêm"

            pdf.cell(10, 6, str(idx), 1, 0, "C")
            pdf.cell(80, 6, str(item_name)[:45], 1, 0, "L")
            pdf.cell(30, 6, str(status_text), 1, 0, "C")
            pdf.cell(70, 6, str(comment_text)[:42], 1, 1, "L")
            idx += 1
    else:
        pdf.cell(190, 6, "Hồ sơ chưa cập nhật bảng checklist chi tiết.", 1, 1, "C")

    pdf.ln(3)

    # Đánh giá tổng quát của Pháp chế
    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(50, 6, "Đánh giá chung của Pháp chế: ", 0, 0)
    pdf.set_font(font_family, "", 10)
    pdf.multi_cell(0, 6, str(legal_review.get("general_assessment", "Chưa có đánh giá")))

    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(50, 6, "Tóm tắt ý kiến Pháp chế: ", 0, 0)
    pdf.set_font(font_family, "", 10)
    pdf.multi_cell(0, 6, str(legal_review.get("summary_notes", "Không có ghi chú thêm.")))
    pdf.ln(4)

    # Kết luận và Phê duyệt của Ban Giám đốc
    pdf.set_font(font_family, "B" if bold_added else "", 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, "II. KẾT LUẬN & Ý KIẾN CHỈ ĐẠO CỦA BAN GIÁM ĐỐC", 0, 1)

    act_label = "ĐỒNG Ý KÝ DUYỆT PHÁT HÀNH" if action_type == "approve" else "YÊU CẦU LÀM LẠI / TỪ CHỐI"
    box_color = (220, 252, 231) if action_type == "approve" else (254, 226, 226)
    text_act_color = (22, 101, 52) if action_type == "approve" else (153, 27, 27)

    pdf.set_fill_color(*box_color)
    pdf.set_font(font_family, "B" if bold_added else "", 11)
    pdf.set_text_color(*text_act_color)
    pdf.cell(0, 8, f"QUYẾT ĐỊNH: {act_label}", 1, 1, "C", True)
    pdf.ln(2)

    pdf.set_text_color(15, 23, 42)
    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(0, 6, "Ý kiến chỉ đạo cụ thể:", 0, 1)
    pdf.set_font(font_family, "", 10)
    pdf.multi_cell(0, 6, director_notes if director_notes else "Đã thẩm tra đầy đủ. Đồng ý ban hành và thực hiện.")
    pdf.ln(6)

    # Chữ ký xác nhận 2 bên
    cur_y = pdf.get_y()
    if cur_y > 230:
        pdf.add_page()

    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.cell(95, 6, "CHUYÊN VIÊN PHÁP CHẾ THẨM ĐỊNH", 0, 0, "C")
    pdf.cell(95, 6, "GIÁM ĐỐC PHÁP CHẾ PHÊ DUYỆT", 0, 1, "C")

    pdf.set_font(font_family, "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(95, 4, "(Ký và ghi rõ họ tên)", 0, 0, "C")
    pdf.cell(95, 4, "(Ký và đóng dấu điện tử)", 0, 1, "C")

    pdf.ln(18)
    pdf.set_font(font_family, "B" if bold_added else "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(95, 6, str(legal_review.get("reviewer_name", contract.get("assigned_to", "Chuyên viên Pháp chế"))), 0, 0, "C")
    pdf.cell(95, 6, str(director_name), 0, 1, "C")

    try:
        return bytes(pdf.output(dest="S").encode("latin1"))
    except Exception:
        return pdf.output(dest="S")

# ==============================================================================
# 5. MODULE GỬI EMAIL TỰ ĐỘNG (SMTP AN TOÀN)
# ==============================================================================
def send_approval_email(contract: dict, pdf_bytes: bytes, pdf_filename: str, action_type: str, director_notes: str) -> tuple[bool, str]:
    """Gửi email tự động qua SMTP với try-except an toàn và đính kèm phiếu thẩm định."""
    config = get_config()
    users = get_users()

    # Tìm email phòng ban / người tạo hợp đồng
    dept_name = contract.get("department", "")
    created_by = contract.get("created_by", "")
    recipient_email = None

    for u in users:
        if u.get("username") == created_by:
            recipient_email = u.get("email")
            break

    if not recipient_email:
        for u in users:
            if u.get("department") == dept_name and u.get("role") in ["Trưởng phòng", "Nhân viên đề xuất", "Phòng ban đề nghị"]:
                recipient_email = u.get("email")
                break

    if not recipient_email:
        recipient_email = f"department.{dept_name.lower().replace(' ', '')}@corporate.com.vn"

    smtp_server = config.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port", 587))
    sender_email = config.get("sender_email", "legal-system@corporate.com.vn")
    sender_password = config.get("sender_password", "")

    status_vn = "KÝ DUYỆT PHÁT HÀNH THÀNH CÔNG" if action_type == "approve" else "YÊU CẦU CHỈNH SỬA & LÀM LẠI"
    subject = f"[{status_vn}] Thông báo kết quả phê duyệt Hợp đồng: {contract.get('id')} - {contract.get('title')}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    body_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #1E293B;">
        <div style="max-width: 650px; margin: 0 auto; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden;">
          <div style="background-color: #1E3A8A; color: white; padding: 18px 24px;">
            <h2 style="margin: 0; font-size: 1.25rem;">HỆ THỐNG THẨM ĐỊNH HỢP ĐỒNG PHÁP CHẾ</h2>
            <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #93C5FD;">Thông báo kết quả xử lý hồ sơ tự động</p>
          </div>
          <div style="padding: 24px;">
            <p>Kính gửi: <b>{dept_name}</b> (Hồ sơ do: <code>{created_by}</code> đề xuất),</p>
            <p>Ban Giám đốc và Phòng Pháp chế xin thông báo kết quả phê duyệt hồ sơ hợp đồng như sau:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-weight: bold; width: 35%;">Mã Hợp đồng:</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0;">{contract.get('id')}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-weight: bold;">Tên Hợp đồng:</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0;">{contract.get('title')}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-weight: bold;">Đối tác:</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0;">{contract.get('partner_name')}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-weight: bold;">Kết quả phê duyệt:</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-weight: bold; color: {'#166534' if action_type == 'approve' else '#991B1B'};">
                  {status_vn}
                </td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-weight: bold;">Ý kiến Giám đốc:</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-style: italic;">{director_notes}</td>
              </tr>
            </table>
            <p>Tệp đính kèm: <b>{pdf_filename}</b> chứa toàn bộ nội dung Phiếu góp ý và đánh giá checklist chi tiết.</p>
            <p style="margin-top: 24px; font-size: 0.85rem; color: #64748B;">
              Trân trọng,<br/>
              <b>Hệ Thống Thẩm Định Pháp Chế Tự Động</b>
            </p>
          </div>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(body_html, "html"))

    if pdf_bytes:
        try:
            part = MIMEApplication(pdf_bytes, Name=pdf_filename)
            part["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'
            msg.attach(part)
        except Exception:
            pass

    # Thử gửi email qua SMTP server thực tế
    if not sender_password:
        return (
            True,
            f"Đã lập lịch thông báo và mô phỏng gửi email thành công đến '{recipient_email}' (Chưa cài Mật khẩu SMTP thực tế)."
        )

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        return (True, f"Đã gửi email thành công kèm tệp '{pdf_filename}' đến {recipient_email}!")
    except Exception as e:
        return (
            False,
            f"Không thể kết nối máy chủ Mail SMTP ({str(e)}). Hồ sơ vẫn được lưu và tạo file PDF bình thường."
        )

# ==============================================================================
# 6. GIAO DIỆN ĐĂNG NHẬP & PHÂN QUYỀN (SESSION STATE)
# ==============================================================================
def render_login_screen():
    display_branding()
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            """
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <h3 style="margin-top:0; color:#1E293B; text-align: center;">🔐 ĐĂNG NHẬP HỆ THỐNG PHÁP CHẾ</h3>
                <p style="text-align: center; color: #64748B; font-size: 0.88rem;">Vui lòng nhập tài khoản hoặc chọn nhanh tài khoản mẫu</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        users = get_users()
        user_opts = [f"{u['username']} - {u['full_name']} ({u['role']} - {u['department']})" for u in users]
        chosen_sample = st.selectbox("Chọn tài khoản mẫu nhanh:", ["-- Tự nhập tài khoản --"] + user_opts)

        default_user = ""
        default_pwd = ""
        if chosen_sample != "-- Tự nhập tài khoản --":
            u_code = chosen_sample.split(" - ")[0]
            default_user = u_code
            for u in users:
                if u["username"] == u_code:
                    default_pwd = u.get("password", "123456")
                    break

        username = st.text_input("Tên đăng nhập:", value=default_user)
        password = st.text_input("Mật khẩu:", type="password", value=default_pwd)

        if st.button("Đăng Nhập Ngay 🚀", type="primary", use_container_width=True):
            matched_user = None
            for u in users:
                if u["username"] == username.strip() and u.get("password") == password.strip():
                    matched_user = u
                    break

            if matched_user:
                st.session_state["logged_in"] = True
                st.session_state["user"] = matched_user
                st.success(f"Xin chào, {matched_user['full_name']} ({matched_user['role']})!")
                st.rerun()
            else:
                st.error("Tên đăng nhập hoặc mật khẩu không chính xác. Thử tài khoản 'giamdoc' mật khẩu '123456'.")

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.rerun()

# ==============================================================================
# 7. BƯỚC 1: CỔNG NỘP HỒ SƠ PHÒNG BAN (department_view)
# ==============================================================================
def department_view():
    st.title("📤 Cổng Nộp Hồ Sơ Hợp Đồng - Phòng Ban Đề Nghị")
    current_user = st.session_state.get("user", {})
    user_dept = current_user.get("department", "Phòng Kinh doanh")

    tab1, tab2 = st.tabs(["📝 Tạo Hồ Sơ Đề Nghị Mới", "📋 Danh Sách Hồ Sơ Đã Nộp"])

    with tab1:
        st.subheader("Thông tin dự thảo hợp đồng cần thẩm định")
        with st.form("create_contract_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                c_title = st.text_input("Tên Hợp đồng / Dự thảo:", placeholder="VD: Hợp đồng mua bán thiết bị văn phòng 2026")
                c_type = st.selectbox("Loại Hợp đồng:", ["Kinh tế / Thương mại", "Cung ứng dịch vụ", "Hợp tác kinh doanh (BCC)", "Lao động", "Bảo mật thông tin (NDA)", "Khác"])
                c_partner = st.text_input("Tên Đối tác / Khách hàng:", placeholder="VD: Công ty Cổ phần Công nghệ ABC")
                c_value = st.number_input("Giá trị hợp đồng (VNĐ):", min_value=0, value=150000000, step=10000000)

            with c2:
                workflows = get_workflows()
                wf_names = [w["name"] for w in workflows] if workflows else ["Quy trình thẩm định hợp đồng thông thường"]
                c_wf = st.selectbox("Áp dụng Quy trình / Checklist:", wf_names)
                c_priority = st.selectbox("Mức độ ưu tiên:", ["Bình thường", "Khẩn cấp", "Đặc biệt quan trọng"])
                c_deadline = st.date_input("Hạn chót thẩm định mong muốn:")
                c_dept = st.text_input("Phòng ban đề xuất:", value=user_dept, disabled=True)

            c_notes = st.text_area("Ghi chú / Yêu cầu trọng tâm cần Pháp chế lưu ý:", placeholder="Nêu rõ các điều khoản điều chỉnh, phạt vi phạm, thanh toán...")
            uploaded_files = st.file_uploader("Đính kèm tệp PDF dự thảo hợp đồng & hồ sơ pháp lý:", accept_multiple_files=True, type=["pdf", "docx"])

            submit_btn = st.form_submit_button("Gửi Hồ Sơ Sang Ban Pháp Chế 🚀", type="primary", use_container_width=True)

            if submit_btn:
                if not c_title.strip() or not c_partner.strip():
                    st.error("Vui lòng điền đầy đủ Tên hợp đồng và Tên đối tác.")
                else:
                    contracts = get_contracts()
                    new_id = f"HD-2026-{len(contracts) + 1:03d}"

                    # Xử lý tệp đính kèm
                    attachments_data = []
                    if uploaded_files:
                        for idx, uf in enumerate(uploaded_files):
                            content_bytes = uf.read()
                            b64 = base64.b64encode(content_bytes).decode("utf-8")
                            attachments_data.append({
                                "file_name": uf.name,
                                "checklist_item": f"Tài liệu {idx + 1}",
                                "data": f"data:application/pdf;base64,{b64}"
                            })
                    else:
                        attachments_data.append({
                            "file_name": f"{new_id}_Du_thao.pdf",
                            "checklist_item": "Dự thảo hợp đồng chính",
                            "data": ""
                        })

                    new_contract = {
                        "id": new_id,
                        "title": c_title.strip(),
                        "type": c_type,
                        "partner_name": c_partner.strip(),
                        "value_vnd": c_value,
                        "department": user_dept,
                        "workflow_name": c_wf,
                        "priority": c_priority,
                        "deadline": str(c_deadline),
                        "notes": c_notes.strip(),
                        "created_by": current_user.get("username", "user"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "Mới tiếp nhận",
                        "assigned_to": "nguyenvana",
                        "attachments": attachments_data
                    }

                    contracts.append(new_contract)
                    if save_contracts(contracts):
                        st.success(f"🎉 Đã nộp thành công hồ sơ '{new_id}: {c_title}' sang Ban Pháp chế!")
                    else:
                        st.error("Không thể lưu hồ sơ hợp đồng.")

    with tab2:
        contracts = get_contracts()
        dept_contracts = [c for c in contracts if c.get("department") == user_dept or current_user.get("role") in ["Ban Giám đốc", "Admin", "Pháp chế"]]
        st.write(f"Tìm thấy **{len(dept_contracts)}** hồ sơ của phòng ban:")
        if dept_contracts:
            df = pd.DataFrame(dept_contracts)
            show_cols = ["id", "title", "partner_name", "value_vnd", "status", "assigned_to", "created_at"]
            st.dataframe(df[[c for c in show_cols if c in df.columns]], use_container_width=True)
        else:
            st.info("Chưa có hồ sơ nào được tạo.")

# ==============================================================================
# 8. BƯỚC 2: CẤU HÌNH QUY TRÌNH CHECKLIST (workflow_config_view)
# ==============================================================================
def workflow_config_view():
    st.title("📑 Cấu Hình Quy Trình & Danh Mục Checklist Pháp Lý")
    workflows = get_workflows()

    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("Danh sách Quy trình")
        wf_names = [w["name"] for w in workflows]
        chosen_wf_name = st.radio("Chọn quy trình:", wf_names if wf_names else ["Chưa có quy trình"])

        st.markdown("---")
        with st.expander("➕ Thêm quy trình mới"):
            new_wf_id = st.text_input("Mã Quy trình (ID):", value=f"wf_{len(workflows)+1}")
            new_wf_n = st.text_input("Tên Quy trình:")
            new_wf_desc = st.text_area("Mô tả:")
            if st.button("Lưu Quy Trình Mới"):
                if new_wf_n.strip():
                    workflows.append({
                        "id": new_wf_id.strip(),
                        "name": new_wf_n.strip(),
                        "description": new_wf_desc.strip(),
                        "checklist_items": ["Kiểm tra tư cách chủ thể", "Điều khoản thanh toán"]
                    })
                    save_workflows(workflows)
                    st.success("Đã thêm quy trình mới.")
                    st.rerun()

    with col_r:
        target_wf = next((w for w in workflows if w["name"] == chosen_wf_name), None)
        if target_wf:
            st.subheader(f"Chi tiết: {target_wf['name']}")
            st.caption(f"Mã: {target_wf.get('id')} | {target_wf.get('description', '')}")

            items = target_wf.get("checklist_items", [])
            st.write("Các tiêu chí checklist bắt buộc chuyên viên phải thẩm định:")

            updated_items = []
            for i, it in enumerate(items):
                c_item_col1, c_item_col2 = st.columns([5, 1])
                with c_item_col1:
                    val = st.text_input(f"Tiêu chí #{i+1}:", value=it, key=f"wf_item_{target_wf['id']}_{i}")
                    updated_items.append(val)
                with c_item_col2:
                    if st.button("🗑️", key=f"del_wf_{target_wf['id']}_{i}"):
                        target_wf["checklist_items"].pop(i)
                        save_workflows(workflows)
                        st.rerun()

            new_item_to_add = st.text_input("Thêm tiêu chí checklist mới:")
            if st.button("Thêm Tiêu Chí"):
                if new_item_to_add.strip():
                    target_wf["checklist_items"].append(new_item_to_add.strip())
                    save_workflows(workflows)
                    st.rerun()

            if st.button("Lưu Cập Nhật Toàn Bộ Checklist 💾", type="primary"):
                target_wf["checklist_items"] = [x.strip() for x in updated_items if x.strip()]
                save_workflows(workflows)
                st.success("Đã lưu thành công danh mục checklist!")

# ==============================================================================
# 9. BƯỚC 3 & 4: BÀN LÀM VIỆC CHUYÊN VIÊN PHÁP CHẾ (legal_staff_view)
# ==============================================================================
def legal_staff_view():
    st.title("⚖️ Bàn Làm Việc Thẩm Định Hợp Đồng - Chuyên Viên Pháp Chế")
    contracts = get_contracts()
    workflows = get_workflows()

    tab_review, tab_history = st.tabs(["🔍 Rà Soát & Thẩm Định Hợp Đồng", "📜 Lịch Sử Thẩm Định (Chỉ Xem)"])

    with tab_review:
        # Lọc các hợp đồng cần thẩm định
        pending_contracts = [c for c in contracts if c.get("status") in ["Mới tiếp nhận", "Đang rà soát"]]
        if not pending_contracts:
            st.info("Hiện không có hồ sơ nào đang chờ rà soát. Bạn có thể chọn tất cả hồ sơ để đối chiếu:")
            pending_contracts = contracts

        c_options = [f"{c['id']} - {c['title']} ({c.get('partner_name')} | {c.get('status')})" for c in pending_contracts]
        selected_option = st.selectbox("Chọn hồ sơ hợp đồng cần thẩm định:", c_options)

        chosen_id = selected_option.split(" - ")[0] if selected_option else None
        contract = next((c for c in contracts if c["id"] == chosen_id), None)

        if not contract:
            st.warning("Không tìm thấy thông tin hợp đồng đã chọn.")
            return

        st.markdown("---")
        # Chia 2 cột: Cột trái xem văn bản/PDF, Cột phải thao tác checklist & thẩm định
        col_pdf, col_legal = st.columns([1, 1])

        with col_pdf:
            st.markdown("#### 📄 Văn Bản Dự Thảo Hợp Đồng")
            atts = contract.get("attachments", [])
            chosen_att_idx = 0
            if len(atts) > 1:
                att_names = [f"{a.get('file_name')} ({a.get('checklist_item')})" for a in atts]
                chosen_att_name = st.selectbox("Chọn tệp tài liệu đối chiếu:", att_names)
                chosen_att_idx = att_names.index(chosen_att_name)

            chosen_att = atts[chosen_att_idx] if atts else {}
            pdf_data = chosen_att.get("data", "")

            view_mode = st.radio("Chế độ xem:", ["📖 Trình đọc A4 chuẩn", "📑 Tệp nhúng PDF (iFrame)"], horizontal=True, key=f"vmode_{contract['id']}")

            if view_mode == "📖 Trình đọc A4 chuẩn":
                st.markdown(
                    f"""
                    <div style="background: white; border: 1.5px solid #CBD5E1; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); font-family: 'Times New Roman', Times, serif; color: #0F172A; max-height: 560px; overflow-y: auto;">
                        <div style="text-align: center; margin-bottom: 16px;">
                            <b style="font-size: 1.05rem;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b><br/>
                            <span style="font-size: 0.95rem;">Độc lập - Tự do - Hạnh phúc</span><br/>
                            <span>-------------------------</span>
                        </div>
                        <h4 style="text-align: center; text-transform: uppercase; margin: 12px 0 4px 0; color: #1E3A8A;">{contract.get('title')}</h4>
                        <div style="text-align: center; font-size: 0.85rem; color: #64748B; margin-bottom: 16px;">Số: {contract.get('id')}/HĐKT-2026</div>
                        <p>Hôm nay, ngày {datetime.now().strftime('%d')} tháng {datetime.now().strftime('%m')} năm 2026, các bên gồm có:</p>
                        <p><b>BÊN A (Bên Đề Nghị): TẬP ĐOÀN CÔNG NGHỆ & DOANH NGHIỆP VIỆT NAM</b><br/>
                        Đại diện: Ban Giám Đốc | Phòng ban phụ trách: {contract.get('department')}</p>
                        <p><b>BÊN B (Đối Tác): {contract.get('partner_name')}</b><br/>
                        Loại hợp đồng: {contract.get('type')}</p>
                        <hr style="border: 0.5px solid #E2E8F0;"/>
                        <p><b>ĐIỀU 1: PHẠM VI VÀ GIÁ TRỊ HỢP ĐỒNG</b><br/>
                        Tổng giá trị hợp đồng là: <b>{contract.get('value_vnd', 0):,.0f} VNĐ</b>.<br/>
                        Phương thức thanh toán: Chuyển khoản ngân hàng theo tiến độ nghiệm thu từng giai đoạn.</p>
                        <p><b>ĐIỀU 2: THỜI HẠN THỰC HIỆN VÀ PHẠT VI PHẠM</b><br/>
                        Thời hạn hoàn tất theo cam kết tại phụ lục đính kèm. Mức phạt vi phạm hợp đồng tối đa 8% theo Luật Thương mại Việt Nam.</p>
                        <p><b>ĐIỀU 3: GIẢI QUYẾT TRANH CHẤP</b><br/>
                        Mọi tranh chấp phát sinh sẽ được ưu tiên thương lượng. Nếu không thành sẽ do Trung tâm Trọng tài Quốc tế Việt Nam (VIAC) hoặc Tòa án có thẩm quyền giải quyết.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                if pdf_data:
                    st.markdown(
                        f"""
                        <iframe src="{pdf_data}" width="100%" height="560px" style="border: 1px solid #CBD5E1; border-radius: 8px;"></iframe>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.info("Chưa có chuỗi base64 nhúng PDF. Vui lòng sử dụng 'Trình đọc A4 chuẩn' ở trên.")

        with col_legal:
            st.markdown("#### ⚖️ Thực Hiện Thẩm Định & Đánh Giá Pháp Lý")

            matched_wf = next((w for w in workflows if w["name"] == contract.get("workflow_name")), None)
            if not matched_wf and workflows:
                matched_wf = workflows[0]

            chk_items = matched_wf.get("checklist_items", []) if matched_wf else [
                "Kiểm tra tư cách chủ thể đối tác & thẩm quyền ký kết",
                "Phạm vi công việc và tiến độ giao hàng/nghiệm thu",
                "Điều khoản giá trị, thuế VAT và phương thức thanh toán",
                "Quy định phạt vi phạm & giới hạn trách nhiệm bồi thường",
                "Điều khoản bảo mật thông tin (NDA) và sở hữu trí tuệ",
                "Luật áp dụng và cơ quan giải quyết tranh chấp"
            ]

            st.write(f"Áp dụng quy trình: **{matched_wf['name'] if matched_wf else 'Tiêu chuẩn'}**")

            chk_results = {}
            for idx, item in enumerate(chk_items):
                with st.expander(f"📌 {idx+1}. {item}", expanded=True):
                    col_st, col_cm = st.columns([1, 2])
                    with col_st:
                        c_stat = st.selectbox(
                            "Kết luận mục:",
                            ["Đạt", "Không đạt", "Có góp ý chỉnh sửa"],
                            key=f"chk_stat_{contract['id']}_{idx}"
                        )
                    with col_cm:
                        c_comm = st.text_input(
                            "Ý kiến chi tiết / Căn cứ pháp lý:",
                            value="Đã đối chiếu điều khoản mẫu, đủ điều kiện pháp lý." if c_stat == "Đạt" else "",
                            key=f"chk_comm_{contract['id']}_{idx}"
                        )
                    chk_results[item] = {"status": c_stat, "comment": c_comm}

            # TÍCH HỢP TRỢ LÝ AI GEMINI (TRY-EXCEPT ĐẦY ĐỦ)
            with st.expander("🤖 Trợ lý AI Gemini - Rà soát Rủi ro & Điều khoản", expanded=False):
                cfg = get_config()
                api_key_input = st.text_input("Gemini API Key:", value=cfg.get("gemini_api_key", ""), type="password", key=f"gem_key_{contract['id']}")
                clause_input = st.text_area("Nội dung điều khoản cần thẩm định rủi ro:", key=f"clause_{contract['id']}")
                if st.button("🔍 Phân tích Rủi ro bằng AI", key=f"btn_ai_{contract['id']}"):
                    if not api_key_input.strip() or not clause_input.strip():
                        st.warning("Vui lòng nhập API Key và nội dung điều khoản.")
                    else:
                        try:
                            if genai:
                                genai.configure(api_key=api_key_input.strip())
                                model = genai.GenerativeModel("gemini-1.5-flash")
                                response = model.generate_content(
                                    f"Bạn là chuyên gia pháp chế doanh nghiệp cao cấp. Hãy thẩm định các rủi ro pháp lý tiềm ẩn và đề xuất sửa đổi điều khoản sau theo luật pháp Việt Nam:\n\n{clause_input}"
                                )
                                st.info("Kết quả phân tích từ AI:")
                                st.markdown(response.text)
                            else:
                                st.error("Thư viện google-generativeai chưa được cài đặt.")
                        except Exception as e:
                            st.error(f"Lỗi khi gọi API Gemini: {str(e)}")

            st.markdown("##### 📝 Đánh Giá Chung & Trình Giám Đốc")
            overall_assessment = st.selectbox(
                "Đánh giá tổng thể của Chuyên viên Pháp chế:",
                ["Đủ điều kiện ký duyệt", "Đủ điều kiện có chỉnh sửa", "Không đủ điều kiện (Yêu cầu làm lại)"],
                key=f"overall_assess_{contract['id']}"
            )

            legal_summary_notes = st.text_area(
                "Tóm tắt ý kiến pháp lý trình Ban Giám Đốc:",
                value="Hồ sơ hợp đồng đã được rà soát chi tiết theo checklist. Các điều khoản về thanh toán và trách nhiệm bồi thường phù hợp với quy định của pháp luật và chính sách nội bộ của công ty. Kính trình Ban Giám đốc xem xét phê duyệt ban hành.",
                height=100,
                key=f"legal_notes_{contract['id']}"
            )

            if st.button("📤 Trình Giám Đốc Phê Duyệt (Chuyển Bước 6)", type="primary", use_container_width=True):
                contract["status"] = "Chờ Giám đốc duyệt"
                contract["legal_review"] = {
                    "reviewer": st.session_state.get("user", {}).get("username", "nguyenvana"),
                    "reviewer_name": st.session_state.get("user", {}).get("full_name", "Nguyễn Văn A"),
                    "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "checklist_results": chk_results,
                    "general_assessment": overall_assessment,
                    "summary_notes": legal_summary_notes.strip()
                }

                if save_contracts(contracts):
                    st.success(f"🎉 Đã hoàn tất thẩm định hồ sơ '{contract['id']}' và chuyển sang trạng thái: **'Chờ Giám đốc duyệt'**!")
                    st.rerun()

    # TAB 2: LỊCH SỬ THẨM ĐỊNH (CHỈ XEM, AN TOÀN TUYỆT ĐỐI)
    with tab_history:
        st.subheader("📜 Lịch Sử Thẩm Định Của Chuyên Viên")
        current_username = st.session_state.get("user", {}).get("username")
        history = [c for c in contracts if c.get("assigned_to") == current_username and c.get("status") != "Đang rà soát"]

        if not history:
            st.info("Chưa có hồ sơ nào trong lịch sử thẩm định của bạn.")
        else:
            for hc in history:
                lr = hc.get("legal_review", {})
                with st.expander(f"📁 {hc['id']}: {hc['title']} — Trạng thái: [{hc['status']}]"):
                    st.write(f"**Đối tác:** {hc['partner_name']} | **Giá trị:** {hc.get('value_vnd', 0):,.0f} VNĐ")
                    st.write(f"**Kết quả tổng quát (Chỉ đọc):** {lr.get('general_assessment', 'N/A')}")
                    # SỬA LỖI CÚ PHÁP TẠI ĐÂY: DÙNG DẤU NHÁY ĐƠN AN TOÀN
                    notes_display = lr.get("summary_notes", "Không có ghi chú thêm.")
                    st.info(f"💡 **Ý kiến kết luận:** {notes_display}")
                    st.markdown("**Chi tiết checklist (Chỉ xem):**")
                    for k, v in lr.get("checklist_results", {}).items():
                        st.markdown(f"- **{k}:** {v.get('status')} {'(' + v.get('comment') + ')' if v.get('comment') else ''}")

# ==============================================================================
# 10. BƯỚC 5 & 6: QUẢN TRỊ GIÁM ĐỐC & PHÊ DUYỆT BAN HÀNH (director_view)
# ==============================================================================
def director_view():
    st.title("👑 Quản Trị & Phê Duyệt Của Ban Giám Đốc (Director View)")
    contracts = get_contracts()
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "giamdoc")
    current_fullname = current_user.get("full_name", "Trần Giám Đốc")

    t1, t2, t3, t4 = st.tabs([
        "📊 Tab 1: Tổng Quan Dashboard",
        "👥 Tab 2: Phân Công Hồ Sơ",
        "📈 Tab 3: Báo Cáo Hiệu Suất",
        "✍️ Tab 4: Phê Duyệt & Ban Hành (Bước 6)"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: TỔNG QUAN DASHBOARD
    # --------------------------------------------------------------------------
    with t1:
        st.subheader("Tổng Quan Trạng Thái Hồ Sơ Hợp Đồng")
        m1, m2, m3, m4 = st.columns(4)
        c_all = len(contracts)
        c_pending = len([c for c in contracts if c.get("status") == "Chờ Giám đốc duyệt"])
        c_reviewing = len([c for c in contracts if c.get("status") in ["Đang rà soát", "Mới tiếp nhận"]])
        c_done = len([c for c in contracts if c.get("status") == "Hoàn tất"])

        with m1: st.metric("Tổng Hợp Đồng", c_all)
        with m2: st.metric("Chờ Giám Đốc Duyệt 🔔", c_pending, delta=c_pending, delta_color="inverse")
        with m3: st.metric("Đang Rà Soát", c_reviewing)
        with m4: st.metric("Đã Hoàn Tất / Ban Hành", c_done)

        st.markdown("---")
        st.subheader("Biểu đồ phân loại theo trạng thái")
        if contracts:
            df_c = pd.DataFrame(contracts)
            stat_counts = df_c["status"].value_counts()
            st.bar_chart(stat_counts)

    # --------------------------------------------------------------------------
    # TAB 2: PHÂN CÔNG HỒ SƠ
    # --------------------------------------------------------------------------
    with t2:
        st.subheader("Điều phối & Phân công Chuyên viên thụ lý hồ sơ")
        users = get_users()
        legal_staff = [u for u in users if u.get("role") in ["Pháp chế", "Chuyên viên Pháp chế"]]

        unassigned_contracts = [c for c in contracts if c.get("status") in ["Mới tiếp nhận", "Đang rà soát"]]
        if not unassigned_contracts:
            st.info("Không có hồ sơ nào chưa được phân công hoặc đang chờ tiếp nhận.")
        else:
            for c in unassigned_contracts:
                with st.expander(f"📄 {c['id']} - {c['title']} ({c.get('department')})", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.write(f"Đối tác: **{c.get('partner_name')}** | Giá trị: **{c.get('value_vnd', 0):,.0f} VNĐ**")
                        st.write(f"Hạn chót: **{c.get('deadline')}** | Quy trình: **{c.get('workflow_name')}**")
                    with col_b:
                        current_staff = c.get("assigned_to", "")
                        staff_opts = [u["username"] for u in legal_staff]
                        def_idx = staff_opts.index(current_staff) if current_staff in staff_opts else 0
                        chosen_staff = st.selectbox(
                            f"Chuyên viên thụ lý ({c['id']}):",
                            staff_opts,
                            index=def_idx,
                            key=f"assign_staff_{c['id']}"
                        )
                        if st.button(f"Giao Việc Hồ Sơ {c['id']}", key=f"btn_assign_{c['id']}"):
                            c["assigned_to"] = chosen_staff
                            c["status"] = "Đang rà soát"
                            save_contracts(contracts)
                            st.success(f"Đã phân công hồ sơ {c['id']} cho chuyên viên {chosen_staff}!")
                            st.rerun()

    # --------------------------------------------------------------------------
    # TAB 3: BÁO CÁO HIỆU SUẤT
    # --------------------------------------------------------------------------
    with t3:
        st.subheader("Báo Cáo Hiệu Suất & Tiến Độ Xử Lý Hợp Đồng")
        if contracts:
            df = pd.DataFrame(contracts)
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.write("**Số lượng hợp đồng theo Phòng ban:**")
                st.bar_chart(df["department"].value_counts())
            with col_chart2:
                st.write("**Số lượng hợp đồng theo Chuyên viên phụ trách:**")
                st.bar_chart(df["assigned_to"].value_counts())

    # --------------------------------------------------------------------------
    # TAB 4: PHÊ DUYỆT & BAN HÀNH (BƯỚC 6 - CHI TIẾT ĐẦY ĐỦ KHÔNG RÚT GỌN)
    # --------------------------------------------------------------------------
    with t4:
        st.subheader("✍️ Phê Duyệt & Ban Hành Hợp Đồng (Hồ Sơ Chờ Giám Đốc Duyệt)")

        approving_contracts = [c for c in contracts if c.get("status") == "Chờ Giám đốc duyệt"]

        if not approving_contracts:
            st.info("Hiện không có hồ sơ nào ở trạng thái **'Chờ Giám đốc duyệt'**.")
            st.caption("Gợi ý: Hãy đăng nhập tài khoản Pháp chế (`nguyenvana`), thực hiện thẩm định ở Tab 'Bàn làm việc Pháp chế' và nhấn nút 'Trình Giám Đốc Phê Duyệt' để tạo hồ sơ chờ duyệt.")
        else:
            appr_options = [
                f"{c['id']} - {c['title']} | Đối tác: {c.get('partner_name')} | Giá trị: {c.get('value_vnd', 0):,.0f} VNĐ"
                for c in approving_contracts
            ]
            chosen_appr_str = st.selectbox("Chọn hồ sơ hợp đồng cần ký duyệt:", appr_options)
            chosen_appr_id = chosen_appr_str.split(" - ")[0]
            appr_contract = next((c for c in approving_contracts if c["id"] == chosen_appr_id), None)

            if appr_contract:
                st.markdown("---")
                col_pdf_left, col_review_right = st.columns([1, 1])

                # CỘT TRÁI: ĐỐI CHIẾU VĂN BẢN HỢP ĐỒNG
                with col_pdf_left:
                    st.markdown("#### 📄 Trình Xem Văn Bản Hợp Đồng (Đối Chiếu PDF)")
                    appr_atts = appr_contract.get("attachments", [])
                    chosen_appr_att_idx = 0

                    if len(appr_atts) > 1:
                        att_labels = [f"Tài liệu #{i+1}: {a.get('file_name')} ({a.get('checklist_item')})" for i, a in enumerate(appr_atts)]
                        chosen_att_lbl = st.selectbox("Chọn tài liệu xem xét:", att_labels, key=f"sel_appr_att_{appr_contract['id']}")
                        chosen_appr_att_idx = att_labels.index(chosen_att_lbl)

                    chosen_appr_att = appr_atts[chosen_appr_att_idx] if appr_atts else {}
                    pdf_b64_str = chosen_appr_att.get("data", "")

                    view_mode_appr = st.radio(
                        "Chế độ xem văn bản:",
                        ["📖 Trình đọc văn bản A4 sắc nét", "📑 Tệp gốc PDF (iFrame / Object)"],
                        horizontal=True,
                        key=f"vmode_appr_{appr_contract['id']}"
                    )

                    if view_mode_appr == "📖 Trình đọc văn bản A4 sắc nét":
                        st.markdown(
                            f"""
                            <div style="background-color: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 8px; padding: 26px 30px; font-family: 'Times New Roman', Times, serif; color: #0F172A; max-height: 540px; overflow-y: auto; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); line-height: 1.6;">
                                <div style="text-align: center; margin-bottom: 20px;">
                                    <div style="font-weight: 800; font-size: 1.05rem; letter-spacing: 0.5px;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
                                    <div style="font-weight: 600; font-size: 0.95rem;">Độc lập - Tự do - Hạnh phúc</div>
                                    <div style="margin-top: 4px; font-size: 0.85rem; color: #475569;">------------------------------------</div>
                                </div>
                                <div style="text-align: center; margin-bottom: 22px;">
                                    <div style="font-size: 1.25rem; font-weight: 800; color: #1E3A8A; text-transform: uppercase;">
                                        {appr_contract.get('title')}
                                    </div>
                                    <div style="font-size: 0.88rem; color: #64748B; margin-top: 4px;">
                                        Mã số hợp đồng: <b>{appr_contract.get('id')}/HĐKT-2026</b>
                                    </div>
                                </div>
                                <p style="font-size: 0.95rem;">
                                    Hôm nay, ngày {datetime.now().strftime('%d')} tháng {datetime.now().strftime('%m')} năm 2026, tại trụ sở Tập đoàn, chúng tôi gồm các bên:
                                </p>
                                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.92rem;">
                                    <b>BÊN ĐỀ NGHỊ (BÊN A):</b> TẬP ĐOÀN CÔNG NGHỆ & DOANH NGHIỆP VIỆT NAM<br/>
                                    • Đơn vị chủ trì: <b>{appr_contract.get('department')}</b><br/>
                                    • Cán bộ đề xuất: <code>{appr_contract.get('created_by')}</code>
                                </div>
                                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; font-size: 0.92rem;">
                                    <b>BÊN ĐỐI TÁC (BÊN B):</b> {appr_contract.get('partner_name')}<br/>
                                    • Hình thức: <b>{appr_contract.get('type')}</b><br/>
                                    • Quy trình áp dụng: {appr_contract.get('workflow_name')}
                                </div>
                                <div style="margin-top: 14px; font-size: 0.92rem;">
                                    <div style="font-weight: 700; color: #1E293B;">ĐIỀU 1. GIÁ TRỊ VÀ PHƯƠNG THỨC THANH TOÁN</div>
                                    <p style="margin: 4px 0 10px 0;">
                                        1.1. Tổng giá trị hợp đồng: <b>{appr_contract.get('value_vnd', 0):,.0f} VNĐ</b> (Đã bao gồm các loại thuế, phí hợp lệ theo quy định pháp luật).<br/>
                                        1.2. Thanh toán theo tiến độ hoàn thành các mốc nghiệm thu kỹ thuật.
                                    </p>
                                    <div style="font-weight: 700; color: #1E293B;">ĐIỀU 2. THẨM QUYỀN VÀ TRÁCH NHIỆM PHÁP LÝ</div>
                                    <p style="margin: 4px 0 10px 0;">
                                        2.1. Các bên cam kết đầy đủ tư cách pháp nhân và thẩm quyền ký kết hợp đồng.<br/>
                                        2.2. Phạt vi phạm hợp đồng tối đa 8% phần giá trị nghĩa vụ hợp đồng bị vi phạm theo Luật Thương mại.
                                    </p>
                                    <div style="font-weight: 700; color: #1E293B;">ĐIỀU 3. ĐIỀU KHOẢN PHÊ DUYỆT & BAN HÀNH</div>
                                    <p style="margin: 4px 0 10px 0;">
                                        Hợp đồng có hiệu lực kể từ ngày được Giám đốc đại diện ký duyệt ban hành điện tử trên hệ thống quản trị pháp chế.
                                    </p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
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
                            st.info("Tài liệu chưa có chuỗi Base64 nhúng.")

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

                # CỘT PHẢI: LỊCH SỬ GÓP Ý & NÚT PHÊ DUYỆT
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
                        value="Đồng ý thông qua nội dung dự thảo hợp đồng theo thẩm định của Ban Pháp chế. Cho phép phát hành và tiến hành ký kết.",
                        height=85,
                        key=f"dir_opinion_input_{appr_contract.get('id')}"
                    )

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

                        if save_contracts(contracts):
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
# 11. GIAO DIỆN QUẢN TRỊ ADMIN (admin_view)
# ==============================================================================
def admin_view():
    st.title("⚙️ Quản Trị Hệ Thống & Cấu Hình Email SMTP")
    cfg = get_config()

    st.subheader("Cấu hình Email SMTP & Tích Hợp Hệ Thống")
    with st.form("admin_cfg_form"):
        s_server = st.text_input("SMTP Server:", value=cfg.get("smtp_server", "smtp.gmail.com"))
        s_port = st.number_input("SMTP Port:", value=int(cfg.get("smtp_port", 587)))
        s_email = st.text_input("Sender Email (Địa chỉ gửi mail tự động):", value=cfg.get("sender_email", ""))
        s_pwd = st.text_input("Sender Password (App Password):", type="password", value=cfg.get("sender_password", ""))
        g_key = st.text_input("Google Gemini API Key:", type="password", value=cfg.get("gemini_api_key", ""))

        if st.form_submit_button("Lưu Cấu Hình Quản Trị 💾", type="primary"):
            cfg["smtp_server"] = s_server.strip()
            cfg["smtp_port"] = int(s_port)
            cfg["sender_email"] = s_email.strip()
            cfg["sender_password"] = s_pwd.strip()
            cfg["gemini_api_key"] = g_key.strip()
            save_json_file(CONFIG_FILE, cfg)
            st.success("Đã cập nhật cấu hình hệ thống thành công!")

# ==============================================================================
# 12. ĐIỀU HƯỚNG TỔNG THỂ & RENDER_MAIN_DASHBOARD()
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
    if user_role in ["Ban Giám đốc", "Admin", "Giám đốc Pháp chế"]:
        menu_options.append("👑 Quản trị Giám đốc (director_view)")

    if user_role in ["Pháp chế", "Chuyên viên Pháp chế", "Admin", "Ban Giám đốc"]:
        menu_options.append("⚖️ Bàn làm việc Pháp chế (legal_staff_view)")
        menu_options.append("📑 Cấu hình Checklist (workflow_config_view)")

    menu_options.append("📤 Cổng nộp hồ sơ (department_view)")

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
# 13. ĐIỂM BẮT ĐẦU CHÍNH (MAIN ENTRY POINT)
# ==============================================================================
def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        render_login_screen()
    else:
        render_main_dashboard()

if __name__ == "__main__":
    main()
