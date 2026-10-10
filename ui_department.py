"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - GIAO DIỆN PHÒNG BAN ĐỀ NGHỊ
File: ui_department.py
Chứa:
- department_view(): Nộp hồ sơ mới và theo dõi tiến độ hồ sơ đã gửi.
Gọi submit_new_contract từ workflow_engine.py.
"""

import base64
from datetime import datetime
import streamlit as st

from db_utils import (
    get_contracts,
    get_workflows
)
from workflow_engine import submit_new_contract

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

                success, c_code, msg = submit_new_contract(
                    contract_title=contract_title,
                    partner_name=partner_name,
                    contract_type=selected_contract_type,
                    contract_value=contract_value,
                    current_username=current_username,
                    current_department=current_department,
                    workflow_id=matched_wf.get("id", "WF_DEFAULT"),
                    effective_date=str(eff_date),
                    expiration_date=str(exp_date),
                    notes=contract_notes,
                    attachments=attachments_list
                )
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

