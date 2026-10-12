"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - TIỆN ÍCH LƯU TRỮ VÀ PHÂN CẤP GOOGLE DRIVE
File: drive_utils.py

Mô tả nghiệp vụ:
- Quản lý xác thực Google Drive API qua Service Account JSON Key (RS256 JWT assertion).
- BẮT BUỘC RÀNG BUỘC CẤU TRÚC THƯ MỤC PHÂN CẤP CHUẨN DOANH NGHIỆP:
    [ROOT_FOLDER] / [NĂM] / [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN] / [TÊN_TỆP]
  Ví dụ:
    HOP_DONG_CNS / 2026 / HD-2026-001_Hop_dong_cung_ung_dich_vu / 01_Du_thao_hop_dong.pdf
- Kiểm tra dung lượng lưu trữ (Storage Quota): Tổng mức, Đã dùng, Còn trống, Thùng rác.
- Thống kê và đồng bộ tài liệu hồ sơ hợp đồng lên Google Drive.
- Xử lý ngoại lệ an toàn, chống crash, không phụ thuộc thư viện bên ngoài chưa cài đặt.
"""

import os
import re
import json
import time
import base64
import tempfile
import subprocess
import unicodedata
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

from db_utils import get_config, save_config, get_contracts, save_contracts

# Cache token trong bộ nhớ process để không tạo lại liên tục
_TOKEN_CACHE: Dict[str, Any] = {
    "access_token": None,
    "expires_at": 0,
    "client_email": None
}

# ==============================================================================
# 1. HÀM CHUYỂN ĐỔI CHUỖI & TẠO TÊN THƯ MỤC / TỆP CHUẨN DOANH NGHIỆP
# ==============================================================================
def remove_vietnamese_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt chuẩn xác để tạo tên thư mục/tệp an toàn trên hệ thống."""
    if not text:
        return ""
    text = text.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", without_accents)

def sanitize_folder_slug(text: str, max_length: int = 50) -> str:
    """
    Rút gọn và chuẩn hóa tên hợp đồng thành chuỗi an toàn:
    - Bỏ dấu tiếng Việt
    - Bỏ ký tự đặc biệt
    - Dùng gạch dưới nối các từ
    - Giới hạn độ dài ngắn gọn, súc tích
    """
    if not text:
        return "Ho_so"
    clean_txt = remove_vietnamese_accents(text).strip()
    # Chỉ giữ chữ, số, gạch nối và khoảng trắng
    clean_txt = re.sub(r"[^\w\s-]", "", clean_txt)
    # Đổi khoảng trắng thành gạch dưới
    clean_txt = re.sub(r"[\s-]+", "_", clean_txt).strip("_")
    if not clean_txt:
        return "Ho_so"
    if len(clean_txt) > max_length:
        clean_txt = clean_txt[:max_length].rstrip("_")
    return clean_txt

def build_contract_folder_name(contract_code: str, contract_title: str) -> str:
    """
    Tạo tên thư mục hồ sơ chuẩn: [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN]
    Ví dụ: HD-2026-001_Hop_dong_dich_vu_cntt
    """
    code_clean = re.sub(r"[^\w-]", "", str(contract_code or "HD")).strip()
    slug_title = sanitize_folder_slug(contract_title or "Hop_dong", max_length=45)
    return f"{code_clean}_{slug_title}"

def format_file_size(size_bytes: int) -> str:
    """Định dạng kích thước byte thành chuỗi KB, MB, GB dễ đọc."""
    try:
        size = float(size_bytes)
    except (ValueError, TypeError):
        return "0 B"
    if size < 1024:
        return f"{size:.0f} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

# ==============================================================================
# 2. XÁC THỰC GOOGLE DRIVE SERVICE ACCOUNT QUA RS256 JWT
# ==============================================================================
def parse_service_account_data(raw_input: Any) -> Optional[Dict[str, Any]]:
    """Phân tích và trích xuất thông tin Service Account từ chuỗi JSON, dict hoặc file path."""
    if not raw_input:
        return None
    if isinstance(raw_input, dict):
        if "client_email" in raw_input and "private_key" in raw_input:
            return raw_input
        return None
    if isinstance(raw_input, str):
        raw_str = raw_input.strip()
        if not raw_str:
            return None
        # Kiểm tra nếu là đường dẫn tệp
        if os.path.exists(raw_str) and os.path.isfile(raw_str):
            try:
                with open(raw_str, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "client_email" in data:
                        return data
            except Exception:
                pass
        # Thử parse chuỗi JSON
        try:
            data = json.loads(raw_str)
            if isinstance(data, dict) and "client_email" in data and "private_key" in data:
                return data
        except Exception:
            pass
    return None

def get_saved_drive_config() -> Dict[str, Any]:
    """Lấy cấu hình Google Drive từ config.json."""
    cfg = get_config()
    drive_cfg = cfg.get("google_drive", {})
    if not isinstance(drive_cfg, dict):
        drive_cfg = {}
    return {
        "enabled": bool(drive_cfg.get("enabled", False)),
        "service_account_json": drive_cfg.get("service_account_json", ""),
        "root_folder_id": drive_cfg.get("root_folder_id", "").strip(),
        "root_folder_name": drive_cfg.get("root_folder_name", "HOP_DONG_CNS").strip() or "HOP_DONG_CNS",
        "client_email": drive_cfg.get("client_email", "").strip()
    }

def b64url_encode(data: bytes) -> str:
    """Encode bytes sang Base64 URL-safe không padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def sign_jwt_rs256_openssl(signing_input: str, private_key_pem: str) -> Optional[str]:
    """Ký số chuỗi header.payload bằng RSA SHA-256 (RS256) thông qua openssl dgst."""
    clean_key = private_key_pem.strip()
    if "\\n" in clean_key and "\n" not in clean_key:
        clean_key = clean_key.replace("\\n", "\n")
    
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".pem") as kf:
        kf.write(clean_key)
        kf_path = kf.name

    try:
        p = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", kf_path],
            input=signing_input.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        if p.returncode == 0 and p.stdout:
            return b64url_encode(p.stdout)
        return None
    except Exception:
        return None
    finally:
        if os.path.exists(kf_path):
            try:
                os.remove(kf_path)
            except Exception:
                pass

def get_drive_access_token(sa_dict: Optional[Dict[str, Any]] = None, force_refresh: bool = False) -> Tuple[Optional[str], str]:
    """
    Tạo hoặc lấy Bearer Access Token cho Google Drive API.
    Sử dụng JWT Bearer Assertion gửi tới https://oauth2.googleapis.com/token.
    Có cơ chế cache token trong bộ nhớ tiến trình để tối ưu hiệu năng.
    """
    global _TOKEN_CACHE

    if sa_dict is None:
        cfg = get_saved_drive_config()
        sa_dict = parse_service_account_data(cfg.get("service_account_json"))
        if not sa_dict:
            return None, "Chưa cấu hình Service Account JSON cho Google Drive trong hệ thống."

    client_email = sa_dict.get("client_email", "").strip()
    private_key = sa_dict.get("private_key", "").strip()
    token_uri = sa_dict.get("token_uri", "https://oauth2.googleapis.com/token")

    if not client_email or not private_key:
        return None, "Dữ liệu Service Account không hợp lệ (thiếu client_email hoặc private_key)."

    now = int(time.time())
    if not force_refresh and _TOKEN_CACHE.get("access_token") and _TOKEN_CACHE.get("client_email") == client_email:
        if _TOKEN_CACHE.get("expires_at", 0) > now + 60:
            return _TOKEN_CACHE["access_token"], "OK (Cached Token)"

    header = {"alg": "RS256", "typ": "JWT"}
    scope = "https://www.googleapis.com/auth/drive"
    exp = now + 3600
    claims = {
        "iss": client_email,
        "scope": scope,
        "aud": token_uri,
        "exp": exp,
        "iat": now
    }

    header_b64 = b64url_encode(json.dumps(header).encode("utf-8"))
    claims_b64 = b64url_encode(json.dumps(claims).encode("utf-8"))
    signing_input = f"{header_b64}.{claims_b64}"

    signature_b64 = sign_jwt_rs256_openssl(signing_input, private_key)
    if not signature_b64:
        return None, "Lỗi ký số RS256: Không thể ký assertion bằng OpenSSL với Private Key được cung cấp."

    jwt_token = f"{signing_input}.{signature_b64}"

    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token
    }
    encoded_body = urllib.parse.urlencode(payload).encode("utf-8")

    req = urllib.request.Request(
        token_uri,
        data=encoded_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            access_token = data.get("access_token")
            expires_in = int(data.get("expires_in", 3600))
            if access_token:
                _TOKEN_CACHE["access_token"] = access_token
                _TOKEN_CACHE["expires_at"] = now + expires_in
                _TOKEN_CACHE["client_email"] = client_email
                return access_token, "OK"
            return None, "Máy chủ OAuth không trả về access_token."
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8", errors="ignore"))
            err_msg = err_body.get("error_description", err_body.get("error", str(e)))
        except Exception:
            err_msg = str(e)
        return None, f"Lỗi xác thực Google OAuth (HTTP {e.code}): {err_msg}"
    except Exception as e:
        return None, f"Lỗi kết nối tới máy chủ Google OAuth: {e}"

# ==============================================================================
# 3. GỌI REST API GOOGLE DRIVE V3 (URLLIB)
# ==============================================================================
def drive_api_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None
) -> Tuple[bool, Any, str]:
    """Hàm lõi gọi Google Drive REST API v3 an toàn và bắt ngoại lệ."""
    if not token:
        token, token_err = get_drive_access_token()
        if not token:
            return False, None, token_err

    url = endpoint
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    body = None
    if json_data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(json_data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_bytes = resp.read()
            if not resp_bytes:
                return True, {}, "OK"
            data = json.loads(resp_bytes.decode("utf-8"))
            return True, data, "OK"
    except urllib.error.HTTPError as e:
        try:
            err_info = json.loads(e.read().decode("utf-8", errors="ignore"))
            msg = err_info.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return False, None, f"Drive API Error (HTTP {e.code}): {msg}"
    except Exception as e:
        return False, None, f"Lỗi kết nối Drive API: {e}"

# ==============================================================================
# 4. QUẢN LÝ DUNG LƯỢNG LƯU TRỮ (STORAGE QUOTA MANAGEMENT)
# ==============================================================================
def get_drive_storage_quota() -> Dict[str, Any]:
    """
    Truy vấn thông tin hạn mức và dung lượng Drive từ Google Drive v3 About API.
    GET https://www.googleapis.com/drive/v3/about?fields=storageQuota,user,maxUploadSize
    """
    ok, data, err = drive_api_request(
        "https://www.googleapis.com/drive/v3/about",
        params={"fields": "storageQuota,user,maxUploadSize"}
    )
    if not ok or not data:
        return {
            "success": False,
            "error": err,
            "connected": False,
            "usage": 0,
            "limit": 0,
            "usage_formatted": "0 B",
            "limit_formatted": "Không xác định",
            "free_formatted": "Không xác định",
            "percent_used": 0.0,
            "user_email": "Chưa kết nối",
            "user_name": "Chưa kết nối"
        }

    quota = data.get("storageQuota", {})
    user = data.get("user", {})

    usage = int(quota.get("usage", 0))
    limit = int(quota.get("limit", 0))
    usage_in_drive = int(quota.get("usageInDrive", 0))
    usage_in_trash = int(quota.get("usageInDriveTrash", 0))

    if limit > 0:
        free = max(0, limit - usage)
        pct = min(100.0, round((usage / limit) * 100, 2))
        limit_str = format_file_size(limit)
        free_str = format_file_size(free)
    else:
        free = 0
        pct = 0.0
        limit_str = "Không giới hạn (Enterprise)"
        free_str = "Không giới hạn"

    return {
        "success": True,
        "connected": True,
        "usage": usage,
        "limit": limit,
        "usage_in_drive": usage_in_drive,
        "usage_in_trash": usage_in_trash,
        "free": free,
        "percent_used": pct,
        "usage_formatted": format_file_size(usage),
        "limit_formatted": limit_str,
        "free_formatted": free_str,
        "trash_formatted": format_file_size(usage_in_trash),
        "user_email": user.get("emailAddress", "Service Account"),
        "user_name": user.get("displayName", "Google Cloud Service Account")
    }

# ==============================================================================
# 5. CƠ CHẾ LƯU TRỮ PHÂN CẤP CHUẨN DOANH NGHIỆP:
#    [ROOT_FOLDER] / [NĂM] / [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN] / [TÊN_TỆP]
# ==============================================================================
def find_folder_by_name(folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Tìm ID thư mục trên Drive theo tên và thư mục cha (không nằm trong Thùng rác)."""
    q_parts = [
        f"name = '{folder_name}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false"
    ]
    if parent_id:
        q_parts.append(f"'{parent_id}' in parents")

    query = " and ".join(q_parts)
    ok, data, _ = drive_api_request(
        "https://www.googleapis.com/drive/v3/files",
        params={
            "q": query,
            "fields": "files(id, name, webViewLink)",
            "pageSize": "1",
            "spaces": "drive"
        }
    )
    if ok and data and data.get("files"):
        return data["files"][0].get("id")
    return None

def create_drive_folder(folder_name: str, parent_id: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Tạo thư mục mới trên Google Drive với tên và thư mục cha chỉ định."""
    metadata: Dict[str, Any] = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    ok, data, err = drive_api_request(
        "https://www.googleapis.com/drive/v3/files",
        method="POST",
        json_data=metadata
    )
    if ok and data and "id" in data:
        return data["id"], "OK"
    return None, f"Không thể tạo thư mục '{folder_name}': {err}"

def get_or_create_subfolder(folder_name: str, parent_id: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Tìm thư mục con đã có, nếu chưa có thì tạo mới."""
    existing_id = find_folder_by_name(folder_name, parent_id)
    if existing_id:
        return existing_id, "OK"
    return create_drive_folder(folder_name, parent_id)

def get_or_create_root_folder() -> Tuple[Optional[str], str]:
    """
    Lấy hoặc tạo Thư mục Gốc của Hệ thống [ROOT_FOLDER] trên Google Drive.
    Ưu tiên root_folder_id đã lưu trong config. Nếu chưa có hoặc không hợp lệ, tìm/tạo root_folder_name.
    """
    cfg = get_saved_drive_config()
    saved_root_id = cfg.get("root_folder_id", "").strip()
    root_name = cfg.get("root_folder_name", "HOP_DONG_CNS").strip() or "HOP_DONG_CNS"

    if saved_root_id:
        ok, data, _ = drive_api_request(
            f"https://www.googleapis.com/drive/v3/files/{saved_root_id}",
            params={"fields": "id, name, trashed"}
        )
        if ok and data and not data.get("trashed"):
            return saved_root_id, "OK"

    root_id, err = get_or_create_subfolder(root_name, parent_id=None)
    if root_id:
        full_cfg = get_config()
        if "google_drive" not in full_cfg:
            full_cfg["google_drive"] = {}
        full_cfg["google_drive"]["root_folder_id"] = root_id
        full_cfg["google_drive"]["root_folder_name"] = root_name
        save_config(full_cfg)
        return root_id, "OK"

    return None, f"Lỗi tạo/tìm thư mục gốc '{root_name}': {err}"

def get_or_create_contract_folder_hierarchy(
    contract_code: str,
    contract_title: str,
    created_at_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    XÂY DỰNG VÀ ĐẢM BẢO CÂY THƯ MỤC PHÂN CẤP CHUẨN DOANH NGHIỆP:
        [ROOT_FOLDER] / [NĂM] / [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN]
    Ví dụ:
        HOP_DONG_CNS / 2026 / HD-2026-001_Hop_dong_dich_vu_cntt
    """
    root_id, root_err = get_or_create_root_folder()
    if not root_id:
        return {
            "success": False,
            "error": f"Không thể xác định Thư mục Gốc: {root_err}",
            "folder_path": ""
        }

    cfg = get_saved_drive_config()
    root_name = cfg.get("root_folder_name", "HOP_DONG_CNS")

    year_str = str(datetime.now().year)
    if created_at_str:
        try:
            match = re.search(r"\b(20\d{2})\b", created_at_str)
            if match:
                year_str = match.group(1)
        except Exception:
            pass

    year_id, year_err = get_or_create_subfolder(year_str, parent_id=root_id)
    if not year_id:
        return {
            "success": False,
            "error": f"Không thể tạo Thư mục Năm [{year_str}]: {year_err}",
            "folder_path": f"{root_name} / {year_str}"
        }

    contract_folder_name = build_contract_folder_name(contract_code, contract_title)
    contract_folder_id, folder_err = get_or_create_subfolder(contract_folder_name, parent_id=year_id)
    if not contract_folder_id:
        return {
            "success": False,
            "error": f"Không thể tạo Thư mục Hồ sơ [{contract_folder_name}]: {folder_err}",
            "folder_path": f"{root_name} / {year_str} / {contract_folder_name}"
        }

    folder_path = f"{root_name} / {year_str} / {contract_folder_name}"
    web_view_link = f"https://drive.google.com/drive/folders/{contract_folder_id}"

    return {
        "success": True,
        "root_folder_id": root_id,
        "year_folder_id": year_id,
        "contract_folder_id": contract_folder_id,
        "year": year_str,
        "contract_folder_name": contract_folder_name,
        "folder_path": folder_path,
        "web_view_link": web_view_link,
        "error": ""
    }

# ==============================================================================
# 6. TẢI TỆP LÊN GOOGLE DRIVE (MULTIPART UPLOAD) THEO CẤU TRÚC PHÂN CẤP
# ==============================================================================
def upload_file_bytes_to_drive(
    file_bytes: bytes,
    file_name: str,
    parent_folder_id: str,
    mime_type: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Tải file lên đúng thư mục chỉ định qua Google Drive Multipart Upload:
    POST https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart
    """
    token, token_err = get_drive_access_token()
    if not token:
        return False, None, token_err

    if not mime_type:
        ext = os.path.splitext(file_name)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".txt": "text/plain",
            ".json": "application/json"
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

    boundary = f"=====DRIVE_UPLOAD_{int(time.time()*1000)}====="
    metadata = {
        "name": file_name,
        "parents": [parent_folder_id],
        "mimeType": mime_type
    }

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b"Content-Type: application/json; charset=UTF-8\r\n\r\n")
    body.extend(json.dumps(metadata).encode("utf-8"))
    body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size,mimeType,webViewLink,webContentLink,createdTime"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body))
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data, "OK"
    except urllib.error.HTTPError as e:
        try:
            err_info = json.loads(e.read().decode("utf-8", errors="ignore"))
            msg = err_info.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return False, None, f"Lỗi Upload Drive (HTTP {e.code}): {msg}"
    except Exception as e:
        return False, None, f"Lỗi mạng khi tải tệp lên Drive: {e}"

def upload_contract_attachment_to_drive(
    contract_id: str,
    contract_title: str,
    file_name: str,
    file_bytes: bytes,
    checklist_item: str = "",
    created_at_str: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Quy trình chuẩn:
    1. Tạo hoặc tìm cây thư mục phân cấp: [ROOT_FOLDER] / [NĂM] / [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN]
    2. Tải tệp vào đúng thư mục hồ sơ đó.
    3. Trả về metadata và đường dẫn thư mục chuẩn.
    """
    hierarchy = get_or_create_contract_folder_hierarchy(
        contract_code=contract_id,
        contract_title=contract_title,
        created_at_str=created_at_str
    )
    if not hierarchy.get("success"):
        return False, None, hierarchy.get("error", "Lỗi tạo cấu trúc cây thư mục")

    target_folder_id = hierarchy["contract_folder_id"]
    folder_path = hierarchy["folder_path"]

    safe_name = re.sub(r"[^\w.-]", "_", remove_vietnamese_accents(file_name)).strip("_")
    if not safe_name:
        safe_name = "tai_lieu_dinh_kem.pdf"

    ok, file_meta, err = upload_file_bytes_to_drive(
        file_bytes=file_bytes,
        file_name=safe_name,
        parent_folder_id=target_folder_id
    )

    if ok and file_meta:
        file_meta["folder_path"] = folder_path
        file_meta["contract_folder_id"] = target_folder_id
        file_meta["contract_folder_url"] = hierarchy["web_view_link"]
        file_meta["checklist_item"] = checklist_item
        return True, file_meta, "OK"

    return False, None, err

# ==============================================================================
# 7. KIỂM TRA KẾT NỐI TOÀN DIỆN CHO ADMIN
# ==============================================================================
def test_drive_connection(service_account_input: Optional[Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Kiểm tra tính hợp lệ của Service Account Key, quyền truy cập API và khả năng tạo thư mục phân cấp.
    Trả về (success, message, details).
    """
    sa_dict = parse_service_account_data(service_account_input) if service_account_input else None
    if not sa_dict:
        cfg = get_saved_drive_config()
        sa_dict = parse_service_account_data(cfg.get("service_account_json"))
        if not sa_dict:
            return False, "Chưa cung cấp Service Account JSON hợp lệ để kiểm tra kết nối.", {}

    token, token_err = get_drive_access_token(sa_dict, force_refresh=True)
    if not token:
        return False, f"Xác thực thất bại: {token_err}", {}

    quota_info = get_drive_storage_quota()
    if not quota_info.get("success"):
        return False, f"Kết nối OAuth thành công nhưng không truy vấn được About/Quota: {quota_info.get('error')}", {}

    root_id, root_err = get_or_create_root_folder()
    if not root_id:
        return False, f"Xác thực thành công nhưng không thể tạo/truy cập Thư mục Gốc trên Drive: {root_err}", quota_info

    details = {
        "client_email": sa_dict.get("client_email"),
        "project_id": sa_dict.get("project_id", "N/A"),
        "root_folder_id": root_id,
        "storage_used": quota_info.get("usage_formatted"),
        "storage_limit": quota_info.get("limit_formatted"),
        "user_name": quota_info.get("user_name"),
        "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return True, f"Kết nối Google Drive thành công! Tài khoản: {sa_dict.get('client_email')} | Thư mục Gốc sẵn sàng.", details

# ==============================================================================
# 8. ĐỒNG BỘ DỮ LIỆU TÀI LIỆU HỢP ĐỒNG (SYNC BATCH)
# ==============================================================================
def get_drive_contracts_storage_stats() -> Dict[str, Any]:
    """Thống kê chi tiết tài liệu hồ sơ trong hệ thống đối chiếu với Google Drive."""
    contracts = get_contracts()
    total_contracts = len(contracts)
    synced_contracts = 0
    total_files = 0
    synced_files = 0
    total_bytes = 0

    for c in contracts:
        atts = c.get("attachments", [])
        c_synced = False
        for att in atts:
            total_files += 1
            f_size = int(att.get("file_size", 0))
            total_bytes += f_size
            if att.get("drive_file_id"):
                synced_files += 1
                c_synced = True
        if c_synced:
            synced_contracts += 1

    return {
        "total_contracts": total_contracts,
        "synced_contracts": synced_contracts,
        "total_files": total_files,
        "synced_files": synced_files,
        "total_size_bytes": total_bytes,
        "total_size_formatted": format_file_size(total_bytes)
    }

def sync_all_pending_contract_files_to_drive() -> Dict[str, Any]:
    """
    Quét tất cả hợp đồng trong hệ thống. Nếu tệp nào có file_base64 mà chưa có
    drive_file_id, tự động tải lên Google Drive theo đúng cây thư mục phân cấp chuẩn:
    [ROOT_FOLDER] / [NĂM] / [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN] / [TÊN_TỆP]
    """
    cfg = get_saved_drive_config()
    sa_dict = parse_service_account_data(cfg.get("service_account_json"))
    if not sa_dict:
        return {"success": False, "synced_count": 0, "error": "Google Drive chưa được cấu hình Service Account."}

    contracts = get_contracts()
    uploaded_count = 0
    errors: List[str] = []

    for c in contracts:
        c_id = c.get("id", "HD-UNKNOWN")
        c_title = c.get("title", "Hop_dong")
        c_created = c.get("created_at")
        atts = c.get("attachments", [])
        contract_changed = False

        for att in atts:
            if not att.get("drive_file_id") and att.get("file_base64"):
                try:
                    f_bytes = base64.b64decode(att["file_base64"])
                    f_name = att.get("file_name", "tai_lieu.pdf")
                    chk_item = att.get("checklist_item", "")

                    ok, meta, err = upload_contract_attachment_to_drive(
                        contract_id=c_id,
                        contract_title=c_title,
                        file_name=f_name,
                        file_bytes=f_bytes,
                        checklist_item=chk_item,
                        created_at_str=c_created
                    )
                    if ok and meta:
                        att["drive_file_id"] = meta.get("id")
                        att["drive_web_view_link"] = meta.get("webViewLink")
                        att["drive_folder_id"] = meta.get("contract_folder_id")
                        att["drive_folder_path"] = meta.get("folder_path")
                        c["drive_folder_url"] = meta.get("contract_folder_url")
                        c["drive_folder_path"] = meta.get("folder_path")
                        uploaded_count += 1
                        contract_changed = True
                    else:
                        errors.append(f"{c_id} ({f_name}): {err}")
                except Exception as ex:
                    errors.append(f"{c_id}: {ex}")

        if contract_changed:
            save_contracts(contracts)

    return {
        "success": True,
        "synced_count": uploaded_count,
        "errors": errors
    }
