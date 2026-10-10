import os
import json
try:
    import streamlit as st
except ImportError:
    class _MockStreamlit:
        @staticmethod
        def error(msg): print(f"[ERROR] {msg}")
    st = _MockStreamlit()

# ==============================================================================
# ĐỊNH NGHĨA CÁC ĐƯỜNG DẪN TỆP DỮ LIỆU JSON
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
    "system_version": "3.0.0 (Refactored)",
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

# ==============================================================================
# CÁC HÀM NGUYÊN THỦY ĐỌC VÀ GHI TỆP JSON
# ==============================================================================
def read_json_file(file_path: str, default_data):
    """Đọc dữ liệu từ file JSON, tự động tạo nếu chưa tồn tại, bắt lỗi chống crash."""
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
    """Ghi dữ liệu vào file JSON chuẩn định dạng UTF-8, indent=2."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as error:
        st.error(f"Lỗi khi ghi dữ liệu vào '{file_path}': {error}")
        return False

# Tương thích cả 2 tên gọi quy chuẩn
load_json_file = read_json_file
save_json_file = write_json_file

# ==============================================================================
# GETTERS VÀ SETTERS CHUYÊN BIỆT CHO TỪNG TỆP JSON
# ==============================================================================
def get_users():
    """Lấy danh sách người dùng từ users.json (fallback DEFAULT_USERS)."""
    users = read_json_file(USERS_FILE, DEFAULT_USERS)
    if not users:
        users = DEFAULT_USERS
        save_users(users)
    return users

def save_users(data) -> bool:
    """Lưu danh sách người dùng vào users.json."""
    return write_json_file(USERS_FILE, data)

def get_config():
    """Lấy cấu hình hệ thống từ config.json (fallback DEFAULT_CONFIG)."""
    cfg = read_json_file(CONFIG_FILE, DEFAULT_CONFIG)
    if not cfg:
        cfg = DEFAULT_CONFIG
        save_config(cfg)
    return cfg

def save_config(data) -> bool:
    """Lưu cấu hình hệ thống vào config.json."""
    return write_json_file(CONFIG_FILE, data)

def get_workflows():
    """Lấy danh sách quy trình/loại hợp đồng từ workflows.json."""
    wfs = read_json_file(WORKFLOWS_FILE, DEFAULT_WORKFLOWS)
    if not wfs:
        wfs = DEFAULT_WORKFLOWS
        save_workflows(wfs)
    return wfs

def save_workflows(data) -> bool:
    """Lưu danh sách quy trình/loại hợp đồng vào workflows.json."""
    return write_json_file(WORKFLOWS_FILE, data)

def get_departments():
    """Lấy danh sách phòng ban từ departments.json."""
    depts = read_json_file(DEPARTMENTS_FILE, DEFAULT_DEPARTMENTS)
    if not depts:
        depts = DEFAULT_DEPARTMENTS
        save_departments(depts)
    return depts

def save_departments(data) -> bool:
    """Lưu danh sách phòng ban vào departments.json."""
    return write_json_file(DEPARTMENTS_FILE, data)

def get_contracts():
    """Lấy danh sách hợp đồng từ contracts.json."""
    return read_json_file(CONTRACTS_FILE, [])

def save_contracts(data) -> bool:
    """Lưu danh sách hợp đồng vào contracts.json."""
    return write_json_file(CONTRACTS_FILE, data)
