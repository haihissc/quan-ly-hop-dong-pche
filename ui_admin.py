"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - GIAO DIỆN QUẢN TRỊ ADMIN
File: ui_admin.py

Chứa:
- admin_view(): 
    1. Quản lý Phòng ban (Thêm, Sửa, Xóa).
    2. Quản lý Người dùng & Phân quyền thông minh (Tạo mới, Chỉnh sửa/Đổi tên đăng nhập đồng bộ hồ sơ, Xóa).
    3. Cấu hình Doanh nghiệp & Trung tâm Gemini AI (Nhận diện công ty, Logo, SMTP, Gemini API Key kiểm tra kết nối REST siêu nhẹ, xử lý quá tải thông minh).
    4. Quản trị Google Drive & Dung lượng Lưu trữ (Cấu trúc phân cấp chuẩn, Service Account, Quota Dashboard, Đồng bộ tệp).
- workflow_config_view():
    Cấu hình Loại hợp đồng và Checklist hồ sơ (Dành cho Pháp chế).
"""

import base64
import json
import urllib.request
import urllib.error
import pandas as pd
import streamlit as st

from db_utils import (
    get_departments, save_departments,
    get_users, save_users,
    get_config, save_config,
    get_workflows, save_workflows,
    get_contracts, save_contracts
)

from drive_utils import (
    test_drive_connection,
    get_drive_storage_quota,
    get_drive_contracts_storage_stats,
    sync_all_pending_contract_files_to_drive,
    get_saved_drive_config,
    parse_service_account_data,
    format_file_size
)

# ==============================================================================
# HÀM KIỂM TRA KẾT NỐI GOOGLE GEMINI AI (SIÊU NHẸ & XỬ LÝ QUÁ TẢI THÔNG MINH)
# ==============================================================================
def test_gemini_api_connection(api_key: str) -> tuple[bool, str, bool]:
    """
    Kiểm tra tính hợp lệ của Google Gemini API Key thông qua REST API siêu nhẹ.
    - Model ping test: gemini-2.5-flash (tránh nghẽn hạn ngạch so với các bản Pro hay model cũ).
    - Nội dung prompt: 'ping' với maxOutputTokens: 1 để tiêu tốn ít tài nguyên nhất, tránh bị từ chối do quá tải.
    - Cơ chế bắt lỗi thông minh (Graceful Handling): Nếu gặp lỗi high demand / 429 / 503,
      hệ thống xác nhận API Key về mặt cú pháp là HỢP LỆ (máy chủ Google đã nhận diện thành công)
      nhưng đang bận tạm thời. Hệ thống cho phép lưu và thông báo cảnh báo nhẹ thay vì chặn đứng bằng lỗi đỏ.
      
    Trả về: (is_valid, message, is_busy)
      - is_valid: True nếu gọi thành công hoặc gặp lỗi bận máy chủ tạm thời (key hợp lệ).
      - message: Thông báo chi tiết.
      - is_busy: True nếu máy chủ Google đang quá tải tạm thời.
    """
    if not api_key or not api_key.strip():
        return False, "API Key đang để trống. Vui lòng nhập API Key để kiểm tra.", False
    
    clean_key = api_key.strip()
    candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = ""

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "ping"}
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 1
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("candidates") or resp.status == 200:
                    return True, f"Kết nối Gemini API thành công với mô hình '{model_name}'!", False
        except urllib.error.HTTPError as e:
            err_msg_text = ""
            try:
                err_data = json.loads(e.read().decode("utf-8", errors="ignore"))
                err_msg_text = err_data.get("error", {}).get("message", str(e))
            except Exception:
                err_msg_text = str(e)
            
            last_err = err_msg_text
            lower_err = err_msg_text.lower()
            
            # Kiểm tra trường hợp quá tải tạm thời / High Demand / 429 / 503
            busy_indicators = [
                "high demand", "currently experiencing high demand",
                "resource_exhausted", "resource has been exhausted",
                "quota", "too many requests", "temporarily unavailable", "overloaded"
            ]
            if e.code in (429, 503) or any(ind in lower_err for ind in busy_indicators):
                return True, "API Key hợp lệ! Máy chủ Gemini hiện đang bận tạm thời (High demand/429/503), tính năng AI sẽ hoạt động bình thường sau ít phút.", True
            
            # Nếu model không tìm thấy (404), thử model tiếp theo trong danh sách candidate
            if "not found" in lower_err or e.code == 404:
                continue
            
            # Lỗi xác thực thực sự (ví dụ: API_KEY_INVALID, 400, 403)
            return False, f"Lỗi xác thực Gemini API ({e.code}): {err_msg_text}", False
        except Exception as e:
            last_err = str(e)
            lower_err = str(e).lower()
            if any(ind in lower_err for ind in ["high demand", "429", "503", "quota"]):
                return True, "API Key hợp lệ! Máy chủ Gemini hiện đang bận tạm thời, tính năng AI sẽ hoạt động bình thường sau ít phút.", True
            return False, f"Lỗi kết nối tới máy chủ Google API: {last_err}", False

    return False, f"Không thể kết nối với các mô hình Gemini. Lỗi cuối: {last_err}", False


# ==============================================================================
# HÀM CHÍNH: ADMIN_VIEW()
# ==============================================================================
def admin_view():
    st.title("⚙️ Bảng Điều Khiển Quản Trị Hệ Thống (Admin Panel)")
    
    tab_depts, tab_users, tab_sys_config, tab_drive = st.tabs([
        "🏢 Quản lý Phòng ban",
        "👥 Quản lý Người dùng",
        "🌐 Cấu hình Doanh nghiệp & AI",
        "☁️ Quản Trị Google Drive & Dung Lượng"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: QUẢN LÝ PHÒNG BAN
    # --------------------------------------------------------------------------
    with tab_depts:
        st.subheader("🏢 Quản Lý Danh Sách Phòng Ban")
        departments = get_departments()
        if departments:
            st.dataframe(pd.DataFrame(departments), use_container_width=True)
            
        col_add, col_edit, col_del = st.columns(3)
        with col_add:
            with st.form("form_add_dept", clear_on_submit=True):
                new_d_name = st.text_input("Tên phòng ban mới *")
                new_d_mgr = st.text_input("Trưởng bộ phận")
                new_d_mail = st.text_input("Email")
                if st.form_submit_button("Thêm phòng ban", use_container_width=True):
                    if new_d_name.strip():
                        dept_code = "DEPT_" + str(len(departments) + 1).zfill(2)
                        departments.append({
                            "id": dept_code,
                            "name": new_d_name.strip(),
                            "manager": new_d_mgr.strip() if new_d_mgr else "Chưa phân công",
                            "email": new_d_mail.strip()
                        })
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

    # --------------------------------------------------------------------------
    # TAB 2: QUẢN LÝ NGƯỜI DÙNG & PHÂN QUYỀN THÔNG MINH
    # --------------------------------------------------------------------------
    with tab_users:
        st.subheader("👥 Quản Lý Người Dùng & Phân Quyền Thông Minh")
        all_users = get_users()
        departments = get_departments()
        dept_names = [d["name"] for d in departments] if departments else ["Phòng Pháp chế", "Ban Giám đốc", "Phòng Kinh doanh & Tiếp thị"]

        # 1. BẢNG HIỂN THỊ DANH SÁCH TÀI KHOẢN
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

                            updated_user_list = [u for u in all_users if u.get("username", "").strip() != old_uname]
                            updated_user_list.append(updated_user)

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

    # --------------------------------------------------------------------------
    # TAB 3: CẤU HÌNH DOANH NGHIỆP, SMTP & GOOGLE GEMINI AI
    # --------------------------------------------------------------------------
    with tab_sys_config:
        st.subheader("🌐 Cấu Hình Nhận Diện Doanh Nghiệp & Email Gửi Đi")
        if st.session_state.get("config_save_success"):
            st.success("🎉 Cập nhật thông tin doanh nghiệp và Google Gemini API Key thành công!")
            del st.session_state["config_save_success"]
        if st.session_state.get("config_warning_msg"):
            st.warning(f"⚠️ {st.session_state.get('config_warning_msg')}")
            del st.session_state["config_warning_msg"]

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

        # CẤU HÌNH TRÍ TUỆ NHÂN TẠO (GOOGLE GEMINI AI) DÙNG CHUNG TOÀN HỆ THỐNG
        st.markdown("---")
        st.markdown("#### 🔑 Cấu Hình Trí Tuệ Nhân Tạo (Google Gemini AI)")
        st.markdown(
            """
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #2563EB; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; font-size: 0.88rem; color: #334155; line-height: 1.5;">
                <b>💡 Lưu ý nghiệp vụ:</b> Quản trị viên cấu hình <b>Google Gemini API Key</b> một lần tại đây. Khóa này sẽ được lưu cố định vào hệ thống, 
                giúp <b>Giám đốc Pháp chế</b> (phê duyệt, rà soát rủi ro toàn văn PDF, Document Q&A) và <b>Chuyên viên Pháp chế</b> (thẩm định điều khoản hợp đồng) 
                tự động có AI sẵn sàng sử dụng mà không cần phải tự cấu hình hay nhập lại nhiều lần.
            </div>
            """,
            unsafe_allow_html=True
        )

        current_saved_gemini_key = cfg.get("gemini_api_key", "").strip()

        if current_saved_gemini_key:
            masked_key = current_saved_gemini_key[:4] + "•" * max(len(current_saved_gemini_key) - 8, 4) + current_saved_gemini_key[-4:] if len(current_saved_gemini_key) > 8 else "••••••••"
            st.markdown(
                f"""
                <div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <span style="font-weight: 700; color: #065F46; font-size: 0.86rem;">
                        🟢 Trạng thái AI: ĐÃ CẤU HÌNH HỆ THỐNG (Khóa hiện tại: <code>{masked_key}</code>)
                    </span>
                    <span style="font-size: 0.80rem; background-color: #D1FAE5; color: #047857; font-weight: 600; padding: 3px 8px; border-radius: 6px;">
                        Mô hình: gemini-2.5-flash (Tự động sẵn sàng)
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
                    <span style="font-weight: 700; color: #92400E; font-size: 0.86rem;">
                        🟡 Trạng thái AI: CHƯA CẤU HÌNH API KEY HỆ THỐNG
                    </span>
                    <span style="display: block; font-size: 0.82rem; color: #B45309; margin-top: 4px;">
                        Các tính năng AI (rà soát rủi ro hợp đồng, hỏi đáp tệp PDF) sẽ tạm thời yêu cầu Giám đốc/Chuyên viên tự nhập key tạm. Hãy nhập API Key bên dưới để kích hoạt cho toàn thể nhân sự.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        col_ai_key, col_ai_test = st.columns([3, 1.2])
        with col_ai_key:
            input_gemini_key = st.text_input(
                "Google Gemini API Key *:",
                value=current_saved_gemini_key,
                type="password",
                placeholder="Nhập hoặc dán Gemini API Key (bắt đầu bằng AIzaSy...)",
                help="Nhập mã Google Gemini API Key để kích hoạt tính năng AI cho toàn hệ thống.",
                key="admin_gemini_api_key_input"
            )
            # Dòng chú thích liên kết mở tab mới rõ ràng, click được 100%
            st.markdown(
                '👉 *Chưa có mã kết nối? <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Bấm vào đây để lấy Gemini API Key miễn phí tại Google AI Studio ↗</a>*',
                unsafe_allow_html=True
            )
        with col_ai_test:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_test_gemini = st.button("🧪 Kiểm Tra Kết Nối", use_container_width=True, key="btn_test_gemini_admin")

        if btn_test_gemini:
            with st.spinner("Đang kết nối thử nghiệm tới máy chủ Google Gemini API (model gemini-2.5-flash)..."):
                is_valid, test_msg, is_busy = test_gemini_api_connection(input_gemini_key)
                if is_busy:
                    st.warning(f"⚠️ {test_msg}")
                elif is_valid:
                    st.success(f"✅ {test_msg}")
                else:
                    st.error(f"❌ {test_msg}")

        st.markdown("---")

        if st.button("💾 Lưu Cấu Hình Doanh Nghiệp & Gemini AI", use_container_width=True, type="primary"):
            cfg["company_name"], cfg["short_name"], cfg["company_address"], cfg["logo_base64"] = cfg_comp_name.strip(), cfg_short.strip(), cfg_addr.strip(), active_logo_b64
            cfg["smtp_settings"] = {
                "server": cfg_smtp_host.strip(),
                "port": int(cfg_smtp_port),
                "sender_email": cfg_sender.strip(),
                "app_password": cfg_app_pwd.strip(),
                "use_tls": True
            }
            
            clean_gemini_key = input_gemini_key.strip()
            # Nếu Admin nhập key mới khác với key đã lưu trước đó, thực hiện kiểm tra ping nhẹ
            if clean_gemini_key and clean_gemini_key != current_saved_gemini_key:
                with st.spinner("Đang xác thực Google Gemini API Key..."):
                    is_valid, test_msg, is_busy = test_gemini_api_connection(clean_gemini_key)
                
                if is_busy:
                    # Key hợp lệ về mặt xác thực nhưng máy chủ Google đang quá tải tạm thời
                    cfg["gemini_api_key"] = clean_gemini_key
                    save_config(cfg)
                    st.session_state["config_warning_msg"] = "Đã lưu API Key thành công! (Máy chủ Gemini hiện đang bận tạm thời, tính năng AI sẽ hoạt động bình thường sau ít phút)"
                    st.rerun()
                elif is_valid:
                    cfg["gemini_api_key"] = clean_gemini_key
                    save_config(cfg)
                    st.session_state["config_save_success"] = True
                    st.rerun()
                else:
                    st.error(f"❌ Không thể lưu API Key: {test_msg}")
            else:
                cfg["gemini_api_key"] = clean_gemini_key
                save_config(cfg)
                st.session_state["config_save_success"] = True
                st.rerun()

    # --------------------------------------------------------------------------
    # TAB 4: QUẢN TRỊ GOOGLE DRIVE & DUNG LƯỢNG LƯU TRỮ
    # --------------------------------------------------------------------------
    with tab_drive:
        st.subheader("☁️ Trung Tâm Quản Trị Google Drive & Dung Lượng Lưu Trữ")
        
        # 1. Khối Banner thông tin cấu trúc thư mục chuẩn
        st.markdown(
            """
            <div style="background-color: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; font-size: 0.88rem; color: #166534; line-height: 1.6;">
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 6px;">
                    📁 CẤU TRÚC LƯU TRỮ PHÂN CẤP CHUẨN DOANH NGHIỆP TRÊN GOOGLE DRIVE
                </div>
                Hệ thống tự động khởi tạo và ràng buộc cây thư mục 3 cấp độc lập, khoa học:<br>
                <code>[THƯ_MỤC_GỐC] / [NĂM] / [MÃ_HỒ_SƠ]_[TÊN_RÚT_GỌN] / [TÊN_TỆP]</code><br>
                <b>Ví dụ:</b> <code>HOP_DONG_CNS / 2026 / HD-2026-001_Hop_dong_dich_vu_cntt / 01_du_thao_hop_dong.pdf</code><br>
                <i>Cơ chế này đảm bảo hồ sơ được lưu trữ tập trung, không phân mảnh và hỗ trợ phân quyền chuẩn mực.</i>
            </div>
            """,
            unsafe_allow_html=True
        )

        cfg = get_config()
        drive_cfg = cfg.get("google_drive", {})
        if not isinstance(drive_cfg, dict):
            drive_cfg = {}

        # 2. Bảng điều khiển Quản trị Dung lượng (Storage Quota Dashboard)
        st.markdown("#### 📊 Bảng Điều Khiển Dung Lượng Lưu Trữ (Storage Quota Dashboard)")
        
        col_ref_quota, col_sync_all = st.columns([1, 1.2])
        with col_ref_quota:
            refresh_quota = st.button("🔄 Cập Nhật Dung Lượng Thực Tế", use_container_width=True, key="btn_refresh_drive_quota")
        with col_sync_all:
            sync_files_btn = st.button("⚡ Đồng Bộ Hồ Sơ Chưa Lưu Lên Drive", use_container_width=True, key="btn_sync_files_to_drive")

        if sync_files_btn:
            with st.spinner("Đang đồng bộ các tệp hợp đồng lên cấu trúc phân cấp Google Drive..."):
                sync_res = sync_all_pending_contract_files_to_drive()
                if sync_res.get("success"):
                    st.success(f"🎉 Đã đồng bộ thành công {sync_res.get('synced_count', 0)} tệp lên Google Drive!")
                else:
                    st.error(f"❌ Đồng bộ thất bại: {sync_res.get('error', 'Lỗi không xác định')}")

        # Lấy thông tin dung lượng
        quota_data = get_drive_storage_quota()
        stats_data = get_drive_contracts_storage_stats()

        if quota_data.get("connected"):
            pct = quota_data.get("percent_used", 0.0)
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("📦 Đã Sử Dụng", quota_data.get("usage_formatted", "0 B"))
            with col_m2:
                st.metric("🎯 Tổng Hạn Mức", quota_data.get("limit_formatted", "Unlimited"))
            with col_m3:
                st.metric("🟢 Còn Trống", quota_data.get("free_formatted", "N/A"))
            with col_m4:
                st.metric("📊 Tỷ Lệ Sử Dụng", f"{pct:.1f}%")

            # Thanh tiến trình
            st.progress(min(pct / 100.0, 1.0))

            # Thông tin tài khoản và thư mục hồ sơ
            st.markdown(
                f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-top: 10px; font-size: 0.85rem; color: #475569;">
                    <b>Tài khoản dịch vụ:</b> <code>{quota_data.get('user_email')}</code> &nbsp;|&nbsp; 
                    <b>Chủ sở hữu:</b> {quota_data.get('user_name')} &nbsp;|&nbsp; 
                    <b>Dung lượng trong thùng rác:</b> {quota_data.get('trash_formatted', '0 B')}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("ℹ️ Google Drive chưa được kết nối hoặc chưa cấu hình Service Account. Hãy thiết lập cấu hình bên dưới để kích hoạt Dashboard dung lượng.")

        # Thống kê hồ sơ hợp đồng
        st.markdown("##### 📁 Thống Kê Tài Liệu Hợp Đồng Hệ Thống")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Tổng Số Hồ Sơ", f"{stats_data.get('total_contracts', 0)} hồ sơ", f"Đã lưu Drive: {stats_data.get('synced_contracts', 0)}")
        with col_s2:
            st.metric("Tổng Số Tệp Đính Kèm", f"{stats_data.get('total_files', 0)} tệp", f"Đã đẩy Drive: {stats_data.get('synced_files', 0)}")
        with col_s3:
            st.metric("Tổng Dung Lượng Tệp", stats_data.get("total_size_formatted", "0 B"))

        st.markdown("---")

        # 3. Khối Cấu hình Service Account & Thư mục Gốc
        st.markdown("#### 🔐 Cấu Hình Kết Nối & Khóa Dịch Vụ Google Drive")
        st.markdown(
            """
            <div style="font-size: 0.86rem; color: #64748B; margin-bottom: 12px;">
                Quản trị viên có thể tải lên tệp <code>credentials.json</code> của Google Cloud Service Account hoặc dán trực tiếp chuỗi JSON.<br>
                <i>Hệ thống tự động sử dụng cơ chế chữ ký số RS256 chuẩn bảo mật để kết nối trực tiếp đến Google Drive API v3.</i>
            </div>
            """,
            unsafe_allow_html=True
        )

        curr_sa_json = drive_cfg.get("service_account_json", "")
        curr_root_name = drive_cfg.get("root_folder_name", "HOP_DONG_CNS") or "HOP_DONG_CNS"
        curr_root_id = drive_cfg.get("root_folder_id", "")
        curr_enabled = drive_cfg.get("enabled", False)

        # Hiển thị trạng thái kết nối
        sa_parsed = parse_service_account_data(curr_sa_json)
        if sa_parsed:
            st.success(f"🟢 **Trạng thái Drive:** Đã có Service Account Key cho `client_email`: `{sa_parsed.get('client_email')}`")
        else:
            st.warning("🟡 **Trạng thái Drive:** Chưa có Service Account Key hợp lệ.")

        col_dr1, col_dr2 = st.columns([1.5, 1])
        with col_dr1:
            uploaded_sa_file = st.file_uploader(
                "Tải lên tệp Service Account Key (JSON):",
                type=["json"],
                key="upload_sa_json_file",
                help="Tải tệp JSON từ Google Cloud Console -> IAM & Admin -> Service Accounts -> Keys."
            )
            
            # Nếu người dùng upload file, đọc nội dung
            loaded_json_content = curr_sa_json
            if uploaded_sa_file is not None:
                try:
                    loaded_json_content = uploaded_sa_file.read().decode("utf-8")
                    st.success("Đã nạp nội dung tệp JSON thành công!")
                except Exception as e:
                    st.error(f"Lỗi đọc tệp JSON: {e}")

            sa_json_input = st.text_area(
                "Hoặc dán nội dung Service Account JSON vào đây *:",
                value=loaded_json_content,
                height=180,
                key="input_sa_json_textarea",
                placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  "private_key_id": "...",\n  "private_key": "-----BEGIN PRIVATE KEY-----\\n...",\n  "client_email": "...@...iam.gserviceaccount.com"\n}'
            )

        with col_dr2:
            root_folder_name_input = st.text_input(
                "Tên Thư mục Gốc (Root Folder Name) *:",
                value=curr_root_name,
                help="Thư mục gốc cha cấp cao nhất trên Google Drive (Mặc định: HOP_DONG_CNS hoặc viết tắt công ty).",
                key="input_root_folder_name"
            )
            root_folder_id_input = st.text_input(
                "ID Thư mục Gốc (Tùy chọn nếu đã tạo sẵn trên Drive):",
                value=curr_root_id,
                help="Nếu để trống, hệ thống sẽ tự động tìm hoặc tạo thư mục có tên trên.",
                key="input_root_folder_id"
            )
            enable_drive_sync = st.checkbox(
                "Kích hoạt tự động lưu trữ và đồng bộ Google Drive",
                value=curr_enabled,
                help="Khi bật, hồ sơ mới tạo hoặc thẩm định sẽ tự động tạo thư mục phân cấp và lưu tệp lên Drive.",
                key="chk_enable_drive_sync"
            )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            btn_test_drive = st.button("🧪 Kiểm Tra Kết Nối Google Drive", use_container_width=True, key="btn_test_drive_conn")

        if btn_test_drive:
            with st.spinner("Đang xác thực Service Account và kiểm tra quyền truy cập Google Drive..."):
                conn_ok, conn_msg, conn_details = test_drive_connection(sa_json_input)
                if conn_ok:
                    st.success(f"✅ {conn_msg}")
                    st.json(conn_details)
                else:
                    st.error(f"❌ {conn_msg}")

        st.markdown("---")

        if st.button("💾 Lưu Cấu Hình Google Drive", use_container_width=True, type="primary", key="btn_save_drive_config"):
            cfg["google_drive"] = {
                "enabled": enable_drive_sync,
                "service_account_json": sa_json_input.strip(),
                "root_folder_name": root_folder_name_input.strip() or "HOP_DONG_CNS",
                "root_folder_id": root_folder_id_input.strip(),
                "client_email": parse_service_account_data(sa_json_input).get("client_email", "") if parse_service_account_data(sa_json_input) else ""
            }
            save_config(cfg)
            st.success("🎉 Đã lưu cấu hình Google Drive thành công!")
            st.rerun()


# ==============================================================================
# HÀM QUẢN LÝ QUY TRÌNH HỢP ĐỒNG (WORKFLOW_CONFIG_VIEW)
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
                    workflows.append({
                        "id": final_id,
                        "name": new_wf_name.strip(),
                        "contract_type": new_wf_name.strip(),
                        "description": new_wf_desc.strip(),
                        "checklist": items
                    })
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
