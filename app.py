import os
import json
import base64
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from fpdf import FPDF
import google.generativeai as genai
import streamlit as st

# ==============================================================================
# HÀM BƯỚC 4: LEGAL_STAFF_VIEW() - PHÁP CHẾ RÀ SOÁT & TÍCH HỢP AI GEMINI
# ==============================================================================
def legal_staff_view():
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "")
    current_fullname = current_user.get("full_name", "Chuyên viên Pháp chế")

    st.title("⚖️ Bàn Làm Việc Pháp Chế: Rà Soát & Thẩm Định Hợp Đồng")
    tab_reviewing, tab_history = st.tabs(["🔍 Đang rà soát", "📜 Lịch sử rà soát"])
    all_contracts = get_contracts()

    # TAB 1: ĐANG RÀ SOÁT (status == 'Đang rà soát' VÀ assigned_to == current_username)
    with tab_reviewing:
        active_contracts = [
            c for c in all_contracts
            if c.get("status") == "Đang rà soát" and c.get("assigned_to") == current_username
        ]

        if not active_contracts:
            st.info(f"Không có hồ sơ nào ở trạng thái 'Đang rà soát' được phân công cho @{current_username}.")
        else:
            labels = [f"{c['id']} — {c['title']} ({c.get('partner_name')})" for c in active_contracts]
            sel_idx = st.selectbox("Chọn hồ sơ thẩm định:", range(len(active_contracts)), format_func=lambda i: labels[i])
            contract = active_contracts[sel_idx]
            st.markdown("---")

            col_left, col_right = st.columns([1, 1])

            # CỘT TRÁI: RENDER PDF TRỰC TIẾP QUA THẺ <iframe> BASE64
            with col_left:
                st.markdown("#### 📄 Xem Trực Tiếp Tài Liệu Hồ Sơ (PDF)")
                attachments = contract.get("attachments", [])
                if attachments:
                    att_labels = [f"{i+1}. [{a.get('checklist_item')}]: {a.get('file_name')}" for i, a in enumerate(attachments)]
                    att_idx = st.selectbox("Chọn file PDF:", range(len(attachments)), format_func=lambda i: att_labels[i])
                    chosen_att = attachments[att_idx]
                    pdf_b64 = chosen_att.get("file_base64", "").strip()
                    if pdf_b64:
                        # Chuẩn hóa base64 & data URI
                        raw_b64 = pdf_b64.split("base64,")[-1].strip().replace("\n", "").replace("\r", "").replace(" ", "")
                        pdf_data_uri = f"data:application/pdf;base64,{raw_b64}"
                        try:
                            pdf_bytes = base64.b64decode(raw_b64)
                        except Exception:
                            pdf_bytes = None

                        # Render đa tầng <object> + <embed> + <iframe>
                        st.markdown(f'''
                        <div style="border-radius: 12px; overflow: hidden; border: 1.5px solid #CBD5E1; box-shadow: 0 4px 10px rgba(0,0,0,0.06); background-color: #FFFFFF; margin-bottom: 10px;">
                            <div style="background-color: #F8FAFC; padding: 10px 14px; border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 0.82rem; font-weight: 700; color: #1E293B;">📎 {chosen_att.get('file_name')}</span>
                                <a href="{pdf_data_uri}" target="_blank" download="{chosen_att.get('file_name')}" style="font-size: 0.78rem; font-weight: 600; color: #2563EB; text-decoration: none; background: #EFF6FF; padding: 4px 10px; border-radius: 6px; border: 1px solid #BFDBFE;">↗️ Mở / Tải tệp</a>
                            </div>
                            <object data="{pdf_data_uri}#toolbar=1" type="application/pdf" width="100%" height="680px" style="border: none; display: block;">
                                <embed src="{pdf_data_uri}#toolbar=1" type="application/pdf" width="100%" height="680px" />
                                <iframe src="{pdf_data_uri}" width="100%" height="680px" style="border: none;"></iframe>
                            </object>
                        </div>
                        ''', unsafe_allow_html=True)

                        if pdf_bytes:
                            st.download_button(
                                label=f"📥 Tải xuống tệp PDF '{chosen_att.get('file_name')}'",
                                data=pdf_bytes,
                                file_name=chosen_att.get("file_name", "document.pdf"),
                                mime="application/pdf",
                                key=f"dl_pdf_{contract['id']}_{att_idx}",
                                use_container_width=True
                            )
                else:
                    st.info("Hồ sơ này không có tệp PDF đính kèm.")

            # CỘT PHẢI: CHECKLIST & AI GEMINI & NÚT 'TRÌNH GIÁM ĐỐC DUYỆT'
            with col_right:
                st.markdown("#### ⚖️ Thẩm Định Checklist & Đánh Giá Pháp Lý")
                matched_wf = next((w for w in get_workflows() if w.get("id") == contract.get("workflow_id")), None)
                checklist = matched_wf.get("checklist", ["Dự thảo Hợp đồng", "Tài liệu khác"]) if matched_wf else ["Dự thảo Hợp đồng", "Tài liệu khác"]
                checklist_results = {}

                for idx, item in enumerate(checklist, 1):
                    st.markdown(f"**Mục {idx}: {item}**")
                    radio_val = st.radio(f"Đánh giá '{item}':", ["Đạt", "Không đạt", "Có góp ý"], horizontal=True, key=f"r_{contract['id']}_{idx}")
                    comment = ""
                    if radio_val == "Có góp ý":
                        comment = st.text_area(f"Góp ý cho '{item}':", key=f"c_{contract['id']}_{idx}", height=80)
                    checklist_results[item] = {"status": radio_val, "comment": comment.strip()}

                st.markdown("---")
                # TÍCH HỢP AI GEMINI
                with st.expander("🤖 Trợ lý AI Gemini - Rà soát Rủi ro & Điều khoản", expanded=False):
                    api_key = st.text_input("Gemini API Key:", type="password", key=f"k_{contract['id']}")
                    clause = st.text_area("Nội dung điều khoản cần rà soát rủi ro:", key=f"t_{contract['id']}")
                    if st.button("🔍 Phân tích Rủi ro bằng AI Gemini", key=f"b_{contract['id']}"):
                        if api_key and clause:
                            try:
                                genai.configure(api_key=api_key.strip())
                                model = genai.GenerativeModel("gemini-1.5-flash")
                                res = model.generate_content(f"Bạn là chuyên gia pháp chế. Hãy đánh giá rủi ro điều khoản sau: {clause}")
                                st.markdown(res.text)
                            except Exception as e:
                                st.error(f"Lỗi Gemini: {e}")

                st.markdown("---")
                gen_assess = st.selectbox("Đánh giá tổng quát: *", ["Đủ điều kiện pháp lý - Đề xuất ký", "Cần điều chỉnh và bổ sung", "Không đủ điều kiện pháp lý"])
                summary = st.text_area("Ý kiến kết luận của Pháp chế: *")

                if st.button("📤 Trình Giám đốc duyệt", type="primary", use_container_width=True):
                    if summary.strip():
                        contract["status"] = "Chờ Giám đốc duyệt"
                        contract["legal_review"] = {
                            "reviewer": current_username,
                            "reviewer_name": current_fullname,
                            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "general_assessment": gen_assess,
                            "summary_notes": summary.strip(),
                            "checklist_results": checklist_results
                        }
                        save_contracts(all_contracts)
                        st.success("Đã hoàn tất rà soát và chuyển sang trạng thái: 'Chờ Giám đốc duyệt'!")
                        st.rerun()

    # TAB 2: LỊCH SỬ RÀ SOÁT (CHỈ XEM, KHÔNG CHO SỬA)
    with tab_history:
        st.subheader("📜 Lịch Sử Thẩm Định Của Chuyên Viên")
        history = [c for c in all_contracts if c.get("assigned_to") == current_username and c.get("status") != "Đang rà soát"]
        if not history:
            st.info("Chưa có hồ sơ nào trong lịch sử thẩm định của bạn.")
        else:
            for hc in history:
                lr = hc.get("legal_review", {})
                with st.expander(f"📁 {hc['id']}: {hc['title']} — Trạng thái: [{hc['status']}]"):
                    st.write(f"**Đối tác:** {hc['partner_name']} | **Giá trị:** {hc['value_vnd']:,.0f} đ")
                    st.write(f"**Kết quả tổng quát (Chỉ đọc):** {lr.get('general_assessment')}")
                    st.info(f"Ý kiến kết luận: {lr.get('summary_notes')}")
                    st.markdown("**Chi tiết checklist (Chỉ xem):**")
                    for k, v in lr.get("checklist_results", {}).items():
                        st.markdown(f"- **{k}:** {v.get('status')} {'(' + v.get('comment') + ')' if v.get('comment') else ''}")

# ==============================================================================
# HÀM BƯỚC 5: DIRECTOR_VIEW() (PHẦN 1) - QUẢN TRỊ GIÁM ĐỐC PHÁP CHẾ
# ==============================================================================
def director_view():
    current_user = st.session_state.get("user", {})
    st.title("👑 Bàn Làm Việc Giám Đốc Pháp Chế")
    tab_stats, tab_assign, tab_transfer = st.tabs(["📊 Dashboard Thống kê", "📋 Phân công hồ sơ", "🔄 Điều chuyển nhân sự"])
    all_contracts = get_contracts()
    all_users = get_users()

    # TAB 1: DASHBOARD THỐNG KÊ (PANDAS, ST.METRIC, 2 BIỂU ĐỒ)
    with tab_stats:
        if all_contracts:
            df = pd.DataFrame(all_contracts)
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("Tổng hồ sơ", len(df))
            with m2: st.metric("Chờ phân công", len(df[df["status"] == "Chờ Giám đốc phân công"]))
            with m3: st.metric("Đang rà soát", len(df[df["status"] == "Đang rà soát"]))
            with m4: st.metric("Đã xong / Chờ duyệt", len(df[df["status"].isin(["Chờ Giám đốc duyệt", "Đã duyệt", "Đã hoàn tất"])]))

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### 📈 1. Phân bổ theo Trạng thái hồ sơ")
                st.bar_chart(df["status"].value_counts(), color="#2563EB")
            with c2:
                st.markdown("##### ⚖️ 2. Thống kê theo Mức độ rủi ro (Kết quả đánh giá)")
                risks = []
                for c in all_contracts:
                    assess = c.get("legal_review", {}).get("general_assessment", "") if c.get("legal_review") else ""
                    if not assess: risks.append("Chưa đánh giá")
                    elif "Đủ điều kiện" in assess: risks.append("Thấp (Đủ ĐK ký)")
                    elif "điều chỉnh" in assess: risks.append("Trung bình (Cần sửa)")
                    else: risks.append("Cao (Không đạt)")
                st.bar_chart(pd.Series(risks).value_counts(), color="#DC2626")

    # TAB 2: PHÂN CÔNG HỒ SƠ (XEM TỆP TIẾNG VIỆT, CHỌN CHUYÊN VIÊN, GIAO VIỆC)
    with tab_assign:
        pending = [c for c in all_contracts if c.get("status") == "Chờ Giám đốc phân công"]
        if not pending:
            st.info("Hiện không có hồ sơ nào ở trạng thái 'Chờ Giám đốc phân công'.")
        else:
            labels = [f"{c['id']} — {c['title']} ({c.get('partner_name')})" for c in pending]
            idx = st.selectbox("Chọn hồ sơ phân công:", range(len(pending)), format_func=lambda i: labels[i])
            c_target = pending[idx]

            col_l, col_r = st.columns([1.1, 0.9])
            with col_l:
                st.markdown(f"**Hợp đồng:** {c_target['title']} | **Giá trị:** {c_target.get('value_vnd', 0):,.0f} đ")
                st.markdown(f"**Đối tác:** {c_target.get('partner_name')} | **Phòng ban:** {c_target.get('department')}")
                attachments = c_target.get("attachments", [])
                if attachments:
                    att_labels = [f"{i+1}. [{a.get('checklist_item')}]: {a.get('file_name')}" for i, a in enumerate(attachments)]
                    att_idx = st.selectbox("Xem tệp đính kèm tiếng Việt:", range(len(attachments)), format_func=lambda i: att_labels[i])
                    chosen_f = attachments[att_idx]
                    b64 = chosen_f.get("file_base64", "").split("base64,")[-1].strip()
                    if b64:
                        st.markdown(f'<object data="data:application/pdf;base64,{b64}#toolbar=1" type="application/pdf" width="100%" height="420px"><iframe src="data:application/pdf;base64,{b64}" width="100%" height="420px"></iframe></object>', unsafe_allow_html=True)
            with col_r:
                legal_users = [u for u in all_users if u.get("department") == "Phòng Pháp chế" or "Pháp chế" in u.get("role", "")]
                if not legal_users: legal_users = all_users
                u_labels = [f"{u['full_name']} (@{u['username']})" for u in legal_users]
                cand_idx = st.selectbox("Chọn chuyên viên pháp chế đảm nhiệm:", range(len(legal_users)), format_func=lambda i: u_labels[i])
                instruction = st.text_area("Chỉ đạo của Giám đốc:", placeholder="Lưu ý rà soát...")
                if st.button("🚀 Giao việc & Đổi trạng thái 'Đang rà soát'", type="primary"):
                    c_target["status"] = "Đang rà soát"
                    c_target["assigned_to"] = legal_users[cand_idx]["username"]
                    save_contracts(all_contracts)
                    st.success("Đã giao việc thành công!")
                    st.rerun()

    # TAB 3: ĐIỀU CHUYỂN
    with tab_transfer:
        in_rev = [c for c in all_contracts if c.get("status") == "Đang rà soát"]
        if not in_rev:
            st.info("Hiện không có hồ sơ nào ở trạng thái 'Đang rà soát'.")
        else:
            rev_labels = [f"{c['id']} — {c['title']} (Đang giao: @{c.get('assigned_to')})" for c in in_rev]
            r_idx = st.selectbox("Chọn hồ sơ cần điều chuyển:", range(len(in_rev)), format_func=lambda i: rev_labels[i])
            c_trans = in_rev[r_idx]
            legal_users = [u for u in all_users if u.get("department") == "Phòng Pháp chế" or "Pháp chế" in u.get("role", "")]
            if not legal_users: legal_users = all_users
            u_labels = [f"{u['full_name']} (@{u['username']})" for u in legal_users]
            new_cand_idx = st.selectbox("Chuyển sang chuyên viên mới:", range(len(legal_users)), format_func=lambda i: u_labels[i])
            reason = st.text_area("Lý do điều chuyển: *", placeholder="Lý do công tác, chuyên môn...")
            if st.button("🔄 Xác nhận Điều chuyển Hồ sơ", type="primary"):
                if reason.strip():
                    c_trans["assigned_to"] = legal_users[new_cand_idx]["username"]
                    save_contracts(all_contracts)
                    st.success("Đã điều chuyển hồ sơ thành công!")
                    st.rerun()

    # TAB 4: PHÊ DUYỆT & BAN HÀNH (BƯỚC 6 - CHI TIẾT, KHÔNG DÙNG PLACEHOLDER)
    with tab_approve:
        st.subheader("✍️ Phê Duyệt & Ban Hành Hợp Đồng")
        pending_appr = [c for c in all_contracts if c.get("status") == "Chờ Giám đốc duyệt"]

        if not pending_appr:
            st.info("Hiện không có hồ sơ nào ở trạng thái 'Chờ Giám đốc duyệt'.")
        else:
            appr_labels = [f"{c['id']} — {c['title']} ({c.get('partner_name')} | {c.get('value_vnd', 0):,.0f} VNĐ)" for c in pending_appr]
            appr_idx = st.selectbox("Chọn hồ sơ cần thẩm tra và phê duyệt:", range(len(pending_appr)), format_func=lambda i: appr_labels[i])
            c_appr = pending_appr[appr_idx]

            st.markdown("---")
            col_pdf, col_rev = st.columns([1.05, 0.95])

            # CỘT TRÁI: HIỂN THỊ TRÌNH XEM PDF (ĐỐI CHIẾU NỘI DUNG HỢP ĐỒNG)
            with col_pdf:
                st.markdown("#### 📄 Trình Xem Văn Bản Hợp Đồng (Đối Chiếu PDF)")
                st.markdown(f"**Mã HĐ:** [{c_appr['id']}] | **Tên:** **{c_appr['title']}** | **Đối tác:** {c_appr.get('partner_name')}")
                attachments = c_appr.get("attachments", [])
                if attachments:
                    att_labels = [f"{i+1}. [{a.get('checklist_item')}]: {a.get('file_name')}" for i, a in enumerate(attachments)]
                    a_idx = st.selectbox("Chọn tài liệu đối chiếu:", range(len(attachments)), format_func=lambda i: att_labels[i])
                    chosen_att = attachments[a_idx]
                    b64 = chosen_att.get("file_base64", "").split("base64,")[-1].strip()

                    v_mode = st.radio("Chế độ xem văn bản:", ["📖 Trình đọc văn bản A4 sắc nét", "📑 Tệp gốc PDF (iFrame)"], horizontal=True, key=f"v_mode_{c_appr['id']}")
                    if v_mode == "📖 Trình đọc văn bản A4 sắc nét":
                        st.markdown(f'''
                        <div style="border-radius: 12px; border: 1.5px solid #CBD5E1; background: #FFFFFF; padding: 20px; font-family: serif; max-height: 480px; overflow-y: auto;">
                            <div style="text-align: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px;">
                                <div style="font-weight: 800; font-size: 0.82rem;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
                                <div style="font-size: 0.75rem; color: #475569;">Độc lập - Tự do - Hạnh phúc</div>
                            </div>
                            <h4 style="text-align: center; margin-top: 10px; color: #0F172A; text-transform: uppercase;">{c_appr['title']}</h4>
                            <div style="font-size: 0.78rem; font-family: sans-serif; background: #F8FAFC; padding: 8px; border-radius: 6px;">
                                <b>Bên A:</b> ASIA HOLDINGS - {c_appr.get('department')}<br/>
                                <b>Bên B:</b> {c_appr.get('partner_name')}<br/>
                                <b>Giá trị:</b> {c_appr.get('value_vnd', 0):,.0f} VNĐ
                            </div>
                            <div style="font-size: 0.78rem; font-family: sans-serif; margin-top: 10px; line-height: 1.5;">
                                <p><b>Điều 1:</b> Cung ứng hạng mục theo đúng hồ sơ [{chosen_att.get('checklist_item')}].</p>
                                <p><b>Điều 2:</b> Thanh toán đúng hạn theo thỏa thuận và bảo hành 24 tháng.</p>
                                <p><b>Ý kiến Pháp chế:</b> "{l_rev.get('summary_notes', 'Đủ điều kiện ký kết') if 'l_rev' in locals() else 'Đủ điều kiện ký kết'}".</p>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                    elif b64:
                        pdf_uri = f"data:application/pdf;base64,{b64}"
                        st.markdown(f'<object data="{pdf_uri}#toolbar=1" type="application/pdf" width="100%" height="480px"><embed src="{pdf_uri}#toolbar=1" type="application/pdf" width="100%" height="480px" /><iframe src="{pdf_uri}" width="100%" height="480px"></iframe></object>', unsafe_allow_html=True)

                    try:
                        f_bytes = base64.b64decode(b64)
                        st.download_button(f"📥 Tải tệp '{chosen_att.get('file_name')}' về máy", data=f_bytes, file_name=chosen_att.get("file_name", "hop_dong.pdf"), mime="application/pdf", key=f"dl_att_{c_appr['id']}_{a_idx}", use_container_width=True)
                    except Exception:
                        pass
                else:
                    st.warning("Hồ sơ không có tệp đính kèm.")

            # CỘT PHẢI: LỊCH SỬ Ý KIẾN GÓP Ý PHÁP CHẾ & 2 NÚT THAO TÁC
            with col_rev:
                st.markdown("#### ⚖️ Lịch Sử Thẩm Định & Ý Kiến Của Pháp Chế")
                l_rev = c_appr.get("legal_review", {})
                if l_rev:
                    st.markdown(f"**Chuyên viên:** {l_rev.get('reviewer_name')} (@{c_appr.get('assigned_to')}) | **Thời gian:** {l_rev.get('reviewed_at')}")
                    st.markdown(f"**Đánh giá tổng quát:** **{l_rev.get('general_assessment')}**")
                    st.info(f"💡 **Ý kiến kết luận:** "{l_rev.get('summary_notes')}"")

                    st.markdown("##### 📋 Chi tiết đánh giá Checklist:")
                    for it_name, it_res in l_rev.get("checklist_results", {}).items():
                        st.markdown(f"- **{it_name}**: [{it_res.get('status')}] — *{it_res.get('comment')}*")

                st.markdown("---")
                dir_notes = st.text_area("Ý kiến phê duyệt của Giám đốc:", value="Đồng ý thông qua nội dung dự thảo hợp đồng theo thẩm định của Ban Pháp chế. Cho phép phát hành.", height=80)
                col_b1, col_b2 = st.columns(2)
                btn_approve = col_b1.button("✅ Ký duyệt phát hành", type="primary", use_container_width=True)
                btn_reject = col_b2.button("↩️ Yêu cầu làm lại", type="secondary", use_container_width=True)

                if btn_approve or btn_reject:
                    action_type = "approve" if btn_approve else "reject"
                    c_appr["status"] = "Hoàn tất" if action_type == "approve" else "Đang rà soát"
                    pdf_filename = f"Phieu_gop_y_{c_appr['id']}.pdf"

                    # 1. DÙNG FPDF TẠO FILE PDF 'PHIẾU GÓP Ý HỢP ĐỒNG' (UNICODE FONT)
                    pdf_bytes = generate_review_pdf(c_appr, action_type, dir_notes, current_fullname)

                    # 2. DÙNG SMTPLIB GỬI EMAIL TỰ ĐỘNG ĐÍNH KÈM FILE PDF
                    email_ok, email_msg = send_approval_email(c_appr, pdf_bytes, pdf_filename, action_type, dir_notes)

                    c_appr["director_approval"] = {
                        "approved_by": current_username,
                        "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "action": "Ký duyệt phát hành" if action_type == "approve" else "Yêu cầu làm lại",
                        "notes": dir_notes
                    }
                    save_contracts(all_contracts)
                    st.success(f"Đã xử lý hồ sơ thành công! Trạng thái: {c_appr['status']}")
                    if email_ok: st.success(email_msg)
                    else: st.info(email_msg)

                # 3. HIỆN NÚT ST.DOWNLOAD_BUTTON TẢI FILE PDF TRÊN GIAO DIỆN
                review_pdf_data = generate_review_pdf(c_appr, "approve", dir_notes, current_fullname)
                st.download_button(
                    label=f"📥 Tải 'Phiếu góp ý Hợp đồng' ({c_appr['id']}.pdf)",
                    data=review_pdf_data,
                    file_name=f"Phieu_gop_y_{c_appr['id']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
