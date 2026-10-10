"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - GIAO DIỆN GIÁM ĐỐC PHÁP CHẾ & GIÁM SÁT ADMIN
File: ui_director.py
Chứa:
- director_view(readonly, active_tab):
    Tab 1: Dashboard Thống kê & Biểu đồ
    Tab 2: Phân công hồ sơ (gọi assign_contract từ workflow_engine)
    Tab 3: Điều chuyển chuyên viên (gọi transfer_contract từ workflow_engine)
    Tab 4: Phê duyệt & Ban hành (gọi approve_contract từ workflow_engine)
Hỗ trợ cả chế độ readonly=True cho Admin ('God Mode').
"""

import base64
import pandas as pd
import streamlit as st

from db_utils import (
    get_contracts,
    get_users,
    get_config
)
from workflow_engine import (
    assign_contract,
    transfer_contract,
    approve_contract,
    generate_review_pdf
)

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
                    success, msg = assign_contract(
                        contract_id=target_contract.get("id"),
                        assignee_username=chosen_candidate.get("username"),
                        director_username=current_username,
                        director_instruction=director_instruction
                    )
                    if success:
                        st.success(
                            f"🎉 Đã giao hồ sơ **'{target_contract.get('id')}: {target_contract.get('title')}'** "
                            f"cho chuyên viên **{chosen_candidate.get('full_name')}** (`@{chosen_candidate.get('username')}`) thành công!\n\n"
                            f"Trạng thái hồ sơ đã chuyển thành: **'Đang rà soát'**."
                        )
                        st.rerun()
                    else:
                        st.error(msg)

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
                        success, msg = transfer_contract(
                            contract_id=transfer_contract.get("id"),
                            new_assignee_username=new_assignee,
                            new_assignee_name=chosen_new_candidate.get("full_name"),
                            transferred_by=current_username,
                            transfer_reason=transfer_reason
                        )
                        if success:
                            st.success(
                                f"🎉 Đã điều chuyển hồ sơ **'{transfer_contract.get('id')}'** từ chuyên viên "
                                f"**{current_assignee_name}** (`@{old_assignee}`) sang **{chosen_new_candidate.get('full_name')}** (`@{new_assignee}`) thành công!"
                            )
                            st.rerun()
                        else:
                            st.error(msg)

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
                    success, msg, pdf_result_bytes, pdf_filename, email_ok, email_msg = approve_contract(
                        contract_id=appr_contract.get("id"),
                        action_type=action_key,
                        director_username=current_username,
                        director_fullname=current_fullname,
                        director_notes=dir_opinion.strip()
                    )

                    if success:
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

                        st.rerun()
                    else:
                        st.error(msg)

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

