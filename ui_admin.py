"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - GIAO DIỆN QUẢN TRỊ ADMIN
File: ui_admin.py
Chứa:
- admin_view(): Quản lý phòng ban, Quản lý người dùng, Cấu hình hệ thống.
- workflow_config_view(): Cấu hình loại hợp đồng và checklist hồ sơ.
"""

import base64
import pandas as pd
import streamlit as st

from db_utils import (
    get_departments, save_departments,
    get_users, save_users,
    get_config, save_config,
    get_workflows, save_workflows,
    get_contracts, save_contracts
)

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

