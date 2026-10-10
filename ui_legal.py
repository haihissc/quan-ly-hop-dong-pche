"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - GIAO DIỆN CHUYÊN VIÊN PHÁP CHẾ
File: ui_legal.py
Chứa:
- legal_staff_view(): Bàn làm việc thẩm định checklist, xem PDF song song, tích hợp AI Gemini.
Gọi save_legal_review từ workflow_engine.py khi trình duyệt lên Giám đốc.
"""

import base64
import pandas as pd
import google.generativeai as genai
import streamlit as st

from db_utils import (
    get_contracts,
    get_users,
    get_config
)
from workflow_engine import save_legal_review

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
                        success, msg = save_legal_review(
                            contract_id=selected_contract.get("id"),
                            reviewer_username=current_username,
                            reviewer_fullname=current_fullname,
                            general_assessment=general_assessment,
                            summary_notes=summary_notes,
                            checklist_results=checklist_results
                        )
                        if success:
                            st.success(
                                f"🎉 Đã hoàn tất rà soát hồ sơ '{selected_contract.get('id')}: {selected_contract.get('title')}' "
                                f"và chuyển sang trạng thái: **'Chờ Giám đốc duyệt'** thành công!"
                            )
                            st.rerun()
                        else:
                            st.error(msg)

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

