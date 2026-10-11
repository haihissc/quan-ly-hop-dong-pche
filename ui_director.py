"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - GIAO DIỆN ĐIỀU HÀNH GIÁM ĐỐC PHÁP CHẾ & GIÁM SÁT ADMIN
File: ui_director.py
Kiến trúc:
- Bàn làm việc Giám đốc Pháp chế và Chế độ Giám sát Read-Only dành cho Admin ('God Mode').
- 4 Tab Nghiệp vụ hoàn chỉnh:
    1. Dashboard / Tổng quan:
       * Clickable Metric Drill-down: Thẻ chỉ số kèm nút chuyển trang ngay lập tức.
       * Bộ lọc động trạng thái để lọc nhanh danh sách bên dưới.
       * 2 biểu đồ phân tích trực quan: Trạng thái & Mức độ rủi ro.
       * Bảng dữ liệu tương tác đầy đủ.
    2. Phân công hồ sơ:
       * Chi tiết thông tin hồ sơ & Trình đọc văn bản A4 / PDF nhúng chuẩn.
       * Giao diện Action Bar ở Chân trang (Bottom Footer Section) phân công cho chuyên viên pháp chế.
    3. Điều chuyển nhân sự:
       * Chọn hồ sơ đang rà soát, xem lịch sử phân công/điều chuyển.
       * Giao diện Action Bar ở Chân trang điều chuyển sang nhân sự mới kèm lý do.
    4. Phê duyệt & Ban hành:
       * Bố cục 2 cột: Cột trái Trình đối chiếu văn bản (A4 / PDF gốc), Cột phải Toàn bộ ý kiến checklist của Pháp chế.
       * Action Bar & Hướng dẫn ở Chân trang (Bottom Footer): Ý kiến Giám đốc, Ký duyệt phát hành, Yêu cầu làm lại.
       * Xuất Phiếu góp ý PDF tiếng Việt Unicode và nút Tải về tự động.
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
    Giao diện Quản trị Điều hành của Giám đốc Pháp chế & Giám sát Read-Only dành cho Admin.
    Kết nối chuẩn xác với workflow_engine.py và db_utils.py.
    """
    current_user = st.session_state.get("user", {})
    current_username = current_user.get("username", "")
    current_fullname = current_user.get("full_name", "Giám đốc Pháp chế")

    # CSS tùy chỉnh riêng cho màn hình Giám đốc (Thẻ chỉ số, Action Footer)
    st.markdown(
        """
        <style>
        /* Card thống kê tương tác */
        .dir-metric-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            transition: all 0.2s ease-in-out;
            height: 100%;
        }
        .dir-metric-card:hover {
            border-color: #3B82F6;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
        }
        .dir-metric-title {
            font-size: 0.82rem;
            color: #64748B;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .dir-metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            color: #0F172A;
            margin: 6px 0;
            line-height: 1.1;
        }
        .dir-metric-badge {
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 20px;
        }
        
        /* Action Footer Bar ở chân trang */
        .dir-footer-action-bar {
            background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
            border: 1.5px solid #CBD5E1;
            border-radius: 14px;
            padding: 20px 24px;
            margin-top: 24px;
            margin-bottom: 16px;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
        }
        .dir-footer-header {
            font-size: 1.05rem;
            font-weight: 800;
            color: #0F172A;
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .dir-footer-desc {
            font-size: 0.82rem;
            color: #475569;
            margin-bottom: 14px;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Tiêu đề giao diện
    if readonly:
        st.title("🛡️ Giám Sát Hệ Thống Hợp Đồng (Read-Only Mode)")
        st.markdown(
            """
            <div style="background: #FEF3C7; border: 1.5px solid #F59E0B; border-radius: 10px; padding: 12px 18px; margin-bottom: 16px;">
                <div style="font-size: 0.95rem; font-weight: 800; color: #92400E; display: flex; align-items: center; gap: 6px;">
                    <span>👑 CHẾ ĐỘ GIÁM SÁT DÀNH CHO ADMIN (READ-ONLY / GOD MODE)</span>
                </div>
                <div style="font-size: 0.84rem; color: #78350F; margin-top: 4px; line-height: 1.5;">
                    Bạn đang giám sát toàn bộ hoạt động của hệ thống với quyền Quản trị viên (Admin). Bạn có quyền tra cứu Dashboard thống kê, đọc tệp PDF hồ sơ đính kèm và kiểm tra phiếu thẩm định của Pháp chế.<br/>
                    <b>Tất cả nút hành động (Phân công, Điều chuyển, Ký duyệt, Yêu cầu làm lại) đã được khóa an toàn để bảo đảm tính độc lập chuyên môn của Phòng Pháp chế.</b>
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

    # Đồng bộ hóa Tab dựa vào session_state hoặc active_tab
    if "director_active_tab_override" in st.session_state and st.session_state["director_active_tab_override"]:
        effective_tab = st.session_state.pop("director_active_tab_override")
    else:
        effective_tab = active_tab or "dashboard"

    tab_titles_admin = [
        "📊 Dashboard Thống kê",
        "📋 Giám sát Phân công",
        "🔄 Giám sát Điều chuyển",
        "✍️ Giám sát Phê duyệt & Hồ sơ"
    ]
    tab_titles_director = [
        "📊 Dashboard / Tổng quan",
        "📋 Phân công hồ sơ",
        "🔄 Điều chuyển nhân sự",
        "✍️ Phê duyệt & Ban hành"
    ]

    titles_to_use = tab_titles_admin if readonly else tab_titles_director

    if effective_tab == "assign":
        ordered_tabs = [titles_to_use[1], titles_to_use[0], titles_to_use[2], titles_to_use[3]]
        tab_assign, tab_stats, tab_transfer, tab_approve = st.tabs(ordered_tabs)
    elif effective_tab == "approve":
        ordered_tabs = [titles_to_use[3], titles_to_use[0], titles_to_use[1], titles_to_use[2]]
        tab_approve, tab_stats, tab_assign, tab_transfer = st.tabs(ordered_tabs)
    elif effective_tab == "transfer":
        ordered_tabs = [titles_to_use[2], titles_to_use[0], titles_to_use[1], titles_to_use[3]]
        tab_transfer, tab_stats, tab_assign, tab_approve = st.tabs(ordered_tabs)
    else:
        tab_stats, tab_assign, tab_transfer, tab_approve = st.tabs(titles_to_use)

    all_contracts = get_contracts()
    all_users = get_users()
    sys_config = get_config()
    company_name = sys_config.get("company_name", "TỔNG CÔNG TY CÔNG NGHIỆP SÀI GÒN - TNHH MỘT THÀNH VIÊN")

    # ==========================================================================
    # TAB 1: DASHBOARD TỔNG QUAN (CLICKABLE METRICS, INTERACTIVE DRILL-DOWN)
    # ==========================================================================
    with tab_stats:
        st.subheader("📊 Báo Cáo & Thống Kê Tổng Quan Hợp Đồng")
        
        if not all_contracts:
            st.info("Hiện chưa có hợp đồng nào được lưu trữ trong hệ thống.")
        else:
            df_contracts = pd.DataFrame(all_contracts)

            total_contracts = len(df_contracts)
            pending_assign = len(df_contracts[df_contracts["status"] == "Chờ Giám đốc phân công"])
            in_review = len(df_contracts[df_contracts["status"] == "Đang rà soát"])
            pending_approval = len(df_contracts[df_contracts["status"] == "Chờ Giám đốc duyệt"])
            completed = len(df_contracts[df_contracts["status"].isin(["Đã hoàn tất", "Hoàn tất", "Đã duyệt", "Đã ký kết"])])

            st.markdown(
                "<div style='font-size: 0.85rem; color: #64748B; margin-bottom: 8px;'>"
                "💡 <i>Nhấp vào các nút thao tác bên dưới mỗi thẻ chỉ số để chuyển ngay đến màn hình xử lý hồ sơ tương ứng.</i>"
                "</div>",
                unsafe_allow_html=True
            )

            # 4 THẺ CHỈ SỐ CLICKABLE DRILL-DOWN TƯƠNG TÁC
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)

            with col_m1:
                st.markdown(
                    f"""
                    <div class="dir-metric-card" style="border-top: 4px solid #2563EB;">
                        <div class="dir-metric-title">📁 Tổng số hồ sơ</div>
                        <div class="dir-metric-value">{total_contracts}</div>
                        <span class="dir-metric-badge" style="background: #EFF6FF; color: #1D4ED8;">Toàn bộ hệ thống</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button("📋 Xem tất cả hồ sơ", key="btn_drill_all", use_container_width=True):
                    st.session_state["dir_dashboard_status_filter"] = "Tất cả"
                    st.rerun()

            with col_m2:
                badge_bg = "#FEE2E2" if pending_assign > 0 else "#F1F5F9"
                badge_color = "#DC2626" if pending_assign > 0 else "#64748B"
                badge_txt = f"⚠️ {pending_assign} cần giao" if pending_assign > 0 else "Đã giao hết"
                st.markdown(
                    f"""
                    <div class="dir-metric-card" style="border-top: 4px solid #DC2626;">
                        <div class="dir-metric-title">⚡ Chờ phân công</div>
                        <div class="dir-metric-value" style="color: {'#DC2626' if pending_assign > 0 else '#0F172A'};">{pending_assign}</div>
                        <span class="dir-metric-badge" style="background: {badge_bg}; color: {badge_color};">{badge_txt}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                btn_assign_label = "🚀 Chuyển đến Phân công" if not readonly else "👁️ Giám sát Phân công"
                if st.button(btn_assign_label, key="btn_drill_assign", type="primary" if pending_assign > 0 else "secondary", use_container_width=True):
                    st.session_state["director_active_tab_override"] = "assign"
                    st.rerun()

            with col_m3:
                st.markdown(
                    f"""
                    <div class="dir-metric-card" style="border-top: 4px solid #F59E0B;">
                        <div class="dir-metric-title">⏳ Đang rà soát</div>
                        <div class="dir-metric-value" style="color: #D97706;">{in_review}</div>
                        <span class="dir-metric-badge" style="background: #FEF3C7; color: #B45309;">Chuyên viên thẩm định</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                btn_trans_label = "🔄 Điều chuyển nhân sự" if not readonly else "👁️ Giám sát Điều chuyển"
                if st.button(btn_trans_label, key="btn_drill_transfer", use_container_width=True):
                    st.session_state["director_active_tab_override"] = "transfer"
                    st.rerun()

            with col_m4:
                badge_appr_bg = "#FEF3C7" if pending_approval > 0 else "#DCFCE7"
                badge_appr_cl = "#92400E" if pending_approval > 0 else "#166534"
                badge_appr_tx = f"✍️ {pending_approval} chờ ký" if pending_approval > 0 else f"✅ {completed} hoàn tất"
                st.markdown(
                    f"""
                    <div class="dir-metric-card" style="border-top: 4px solid #10B981;">
                        <div class="dir-metric-title">✍️ Chờ Giám đốc duyệt</div>
                        <div class="dir-metric-value" style="color: {'#B45309' if pending_approval > 0 else '#059669'};">{pending_approval}</div>
                        <span class="dir-metric-badge" style="background: {badge_appr_bg}; color: {badge_appr_cl};">{badge_appr_tx}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                btn_appr_label = "✍️ Chuyển đến Ký duyệt" if not readonly else "👁️ Giám sát Phê duyệt"
                if st.button(btn_appr_label, key="btn_drill_approve", type="primary" if pending_approval > 0 else "secondary", use_container_width=True):
                    st.session_state["director_active_tab_override"] = "approve"
                    st.rerun()

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # 2 BIỂU ĐỒ BÁO CÁO PHÂN TÍCH
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
                st.markdown("##### ⚖️ 2. Thống kê theo Mức độ rủi ro (Kết quả thẩm định)")
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

            # BẢNG TƯƠNG TÁC DANH SÁCH HỒ SƠ VỚI BỘ LỌC ĐỘNG
            st.markdown("---")
            st.markdown("##### 📋 Danh Sách Hồ Sơ Tương Tác & Tra Cứu Nhanh")
            
            filter_col1, filter_col2 = st.columns([1, 2])
            with filter_col1:
                status_options = ["Tất cả", "Chờ Giám đốc phân công", "Đang rà soát", "Chờ Giám đốc duyệt", "Hoàn tất"]
                curr_filter = st.session_state.get("dir_dashboard_status_filter", "Tất cả")
                idx_default = status_options.index(curr_filter) if curr_filter in status_options else 0
                chosen_status = st.selectbox("Lọc nhanh theo trạng thái:", status_options, index=idx_default, key="sb_dash_filter")
            
            with filter_col2:
                search_kw = st.text_input("Tìm kiếm theo Mã HĐ, Tên hợp đồng, Đối tác, Phòng ban:", placeholder="Nhập từ khóa tìm kiếm...", key="input_dash_search")

            # Áp dụng bộ lọc
            filtered_df = df_contracts.copy()
            if chosen_status != "Tất cả":
                if chosen_status == "Hoàn tất":
                    filtered_df = filtered_df[filtered_df["status"].isin(["Hoàn tất", "Đã hoàn tất", "Đã duyệt", "Đã ký kết"])]
                else:
                    filtered_df = filtered_df[filtered_df["status"] == chosen_status]
            
            if search_kw.strip():
                kw = search_kw.strip().lower()
                filtered_df = filtered_df[
                    filtered_df["id"].str.lower().str.contains(kw, na=False) |
                    filtered_df["title"].str.lower().str.contains(kw, na=False) |
                    filtered_df["partner_name"].str.lower().str.contains(kw, na=False) |
                    filtered_df["department"].str.lower().str.contains(kw, na=False)
                ]

            view_cols = ["id", "title", "partner_name", "department", "value_vnd", "status", "assigned_to", "created_at"]
            avail_cols = [col for col in view_cols if col in filtered_df.columns]
            
            st.dataframe(
                filtered_df[avail_cols],
                column_config={
                    "id": st.column_config.TextColumn("Mã HĐ", width="medium"),
                    "title": st.column_config.TextColumn("Tên hợp đồng", width="large"),
                    "partner_name": st.column_config.TextColumn("Đối tác"),
                    "department": st.column_config.TextColumn("Phòng ban đề xuất"),
                    "value_vnd": st.column_config.NumberColumn("Giá trị (VNĐ)", format="%d VNĐ"),
                    "status": st.column_config.TextColumn("Trạng thái"),
                    "assigned_to": st.column_config.TextColumn("Chuyên viên"),
                    "created_at": st.column_config.TextColumn("Ngày tạo"),
                },
                hide_index=True,
                use_container_width=True
            )

    # ==========================================================================
    # TAB 2: PHÂN CÔNG HỒ SƠ (FOOTER ACTION BAR DƯỚI CÙNG)
    # ==========================================================================
    with tab_assign:
        st.subheader("📋 Phân Công Hồ Sơ Cho Chuyên Viên Pháp Chế")
        st.markdown("Xem chi tiết hồ sơ đề xuất, thẩm tra nội dung văn bản đính kèm, sau đó quyết định giao việc tại khu vực chân trang.")

        pending_list = [c for c in all_contracts if c.get("status") == "Chờ Giám đốc phân công"]

        if not pending_list:
            st.info("🎉 Hiện không có hồ sơ nào ở trạng thái **'Chờ Giám đốc phân công'**. Toàn bộ đã được phân công hoặc hoàn tất.")
        else:
            pending_labels = [
                f"{c.get('id')} — {c.get('title')} ({c.get('partner_name')} | {c.get('department')} | {c.get('value_vnd', 0):,.0f} VNĐ)"
                for c in pending_list
            ]
            sel_pending_idx = st.selectbox(
                "Chọn hồ sơ cần thẩm tra và phân công:",
                range(len(pending_list)),
                format_func=lambda i: pending_labels[i],
                key="sel_assign_contract"
            )
            target_contract = pending_list[sel_pending_idx]

            st.markdown("---")

            # 1. KHỐI THÔNG TIN CHI TIẾT HỒ SƠ
            st.markdown("#### 📄 1. Thông Tin Chi Tiết Hồ Sơ")
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.markdown(f"- **Mã hồ sơ:** `{target_contract.get('id')}`")
                st.markdown(f"- **Tên hợp đồng:** **{target_contract.get('title')}**")
                st.markdown(f"- **Phân loại:** {target_contract.get('contract_type', 'Hợp đồng thương mại')}")
            with col_info2:
                st.markdown(f"- **Đối tác (Bên B):** **{target_contract.get('partner_name')}**")
                st.markdown(f"- **Phòng ban đề xuất:** {target_contract.get('department')}")
                st.markdown(f"- **Người tạo hồ sơ:** `@{target_contract.get('created_by')}`")
            with col_info3:
                st.markdown(f"- **Giá trị hợp đồng:** <b style='color: #047857;'>{target_contract.get('value_vnd', 0):,.0f} VNĐ</b>", unsafe_allow_html=True)
                st.markdown(f"- **Thời hạn:** `{target_contract.get('effective_date')}` đến `{target_contract.get('expiration_date')}`")
                st.markdown(f"- **Trạng thái:** <span style='background: #FEE2E2; color: #DC2626; padding: 2px 8px; border-radius: 4px; font-weight: 700;'>{target_contract.get('status')}</span>", unsafe_allow_html=True)

            if target_contract.get("notes"):
                st.info(f"💡 **Ghi chú/Đề xuất từ phòng ban:** {target_contract.get('notes')}")

            # 2. KHỐI TRÌNH ĐỌC VĂN BẢN HỒ SƠ (ĐỐI CHIẾU PDF)
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 📎 2. Văn Bản & Tài Liệu Đính Kèm Cần Rà Soát")
            attachments = target_contract.get("attachments", [])
            
            if not attachments:
                st.warning("Hồ sơ này chưa có tệp đính kèm nào.")
            else:
                att_labels = [
                    f"{i+1}. [{att.get('checklist_item', 'Tài liệu')}]: {att.get('file_name', 'document.pdf')}"
                    for i, att in enumerate(attachments)
                ]
                att_idx = st.selectbox(
                    "Chọn tệp tài liệu trong hồ sơ để đọc:",
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
                    missing_pad = len(raw_b64) % 4
                    if missing_pad:
                        raw_b64 += "=" * (4 - missing_pad)
                    pdf_data_uri = f"data:application/pdf;base64,{raw_b64}"

                    try:
                        pdf_bytes = base64.b64decode(raw_b64)
                    except Exception:
                        pdf_bytes = None

                    f_name = chosen_att.get("file_name", "document.pdf")
                    f_kb = chosen_att.get("file_size", len(pdf_bytes) if pdf_bytes else 0) / 1024

                    col_vmode, col_vdl = st.columns([2, 1])
                    with col_vmode:
                        view_mode_assign = st.radio(
                            "Chế độ hiển thị văn bản:",
                            ["📖 Trình đọc văn bản A4 sắc nét", "📑 Tệp gốc PDF (iFrame / Object)"],
                            horizontal=True,
                            key=f"mode_assign_pdf_{target_contract.get('id')}_{att_idx}"
                        )
                    with col_vdl:
                        if pdf_bytes:
                            st.download_button(
                                label=f"📥 Tải tệp '{f_name}' về máy",
                                data=pdf_bytes,
                                file_name=f_name,
                                mime="application/pdf",
                                key=f"btn_dl_dir_{target_contract.get('id')}_{att_idx}",
                                use_container_width=True
                            )

                    if view_mode_assign == "📖 Trình đọc văn bản A4 sắc nét":
                        chk_item = chosen_att.get("checklist_item", "Dự thảo hợp đồng")
                        st.markdown(
                            f"""
                            <div style="border-radius: 12px; border: 1.5px solid #CBD5E1; box-shadow: 0 4px 10px rgba(0,0,0,0.06); background-color: #F8FAFC; overflow: hidden; margin-top: 8px; margin-bottom: 8px;">
                                <div style="background-color: #1E293B; color: #FFFFFF; padding: 8px 14px; font-size: 0.82rem; font-weight: 600; display: flex; justify-content: space-between; align-items: center;">
                                    <span>📖 Văn bản hồ sơ: <b>{f_name}</b></span>
                                    <span style="color: #6EE7B7; font-size: 0.75rem; font-family: monospace;">Khổ chuẩn A4 • Sắc nét</span>
                                </div>
                                <div style="padding: 24px; background: #FFFFFF; max-height: 480px; min-height: 480px; overflow-y: auto; font-family: serif; color: #1E293B; border-top: 1px solid #E2E8F0; line-height: 1.6;">
                                    <div style="text-align: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 12px; margin-bottom: 12px;">
                                        <div style="font-weight: 800; font-size: 0.85rem; text-transform: uppercase; color: #0F172A;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
                                        <div style="font-weight: 700; font-size: 0.78rem; color: #334155;">Độc lập - Tự do - Hạnh phúc</div>
                                        <div style="font-size: 0.75rem; color: #64748B; margin-top: 2px;">***</div>
                                    </div>
                                    <div style="text-align: center; margin-bottom: 14px;">
                                        <h3 style="font-size: 1.05rem; font-weight: 800; text-transform: uppercase; color: #0F172A; margin: 0;">{target_contract.get('title')}</h3>
                                        <div style="font-size: 0.78rem; color: #64748B; font-family: sans-serif; margin-top: 4px;">
                                            Số hiệu: <b>{target_contract.get('id')}</b> | Phân loại: <b>{target_contract.get('contract_type')}</b>
                                        </div>
                                        <div style="font-size: 0.78rem; color: #2563EB; font-family: sans-serif; font-weight: 600; margin-top: 2px;">
                                            Hạng mục hồ sơ: [{chk_item}]
                                        </div>
                                    </div>
                                    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; font-size: 0.8rem; font-family: sans-serif; margin-bottom: 14px;">
                                        <div><b>Bên đề xuất (Bên A):</b> {company_name} - {target_contract.get('department')}</div>
                                        <div style="margin-top: 3px;"><b>Đối tác (Bên B):</b> <span style="color: #1E3A8A; font-weight: 700;">{target_contract.get('partner_name')}</span></div>
                                        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed #CBD5E1; display: flex; justify-content: space-between; flex-wrap: wrap;">
                                            <span>Giá trị: <b style="color: #047857;">{target_contract.get('value_vnd', 0):,.0f} VNĐ</b></span>
                                            <span>Thời hạn: <b>{target_contract.get('effective_date')}</b> đến <b>{target_contract.get('expiration_date')}</b></span>
                                        </div>
                                    </div>
                                    <div style="font-size: 0.8rem; font-family: sans-serif; color: #334155;">
                                        <p><b>Nội dung thẩm tra hồ sơ:</b><br/>
                                        Hồ sơ trình ký phục vụ công tác rà soát, thẩm định trước khi ký kết chính thức. Toàn bộ tài liệu, quy cách đính kèm tuân thủ quy chế nội bộ của Tổng Công ty và pháp luật Việt Nam.</p>
                                        {f'<p><b>Ghi chú đề xuất của đơn vị:</b> <i>"{target_contract.get("notes")}"</i></p>' if target_contract.get("notes") else ''}
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
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
                else:
                    st.info("Tệp đính kèm không có dữ liệu chuỗi nội dung.")

            # 3. ACTION BAR & HƯỚNG DẪN Ở CHÂN TRANG (BOTTOM SECTION)
            st.markdown(
                """
                <div class="dir-footer-action-bar">
                    <div class="dir-footer-header">
                        <span>🎯 KHU VỰC CHỈ ĐẠO & PHÂN CÔNG THỤ LÝ (CHÂN TRANG)</span>
                    </div>
                    <div class="dir-footer-desc">
                        Giám đốc xem xét hồ sơ và tài liệu bên trên, sau đó lựa chọn Chuyên viên Pháp chế chịu trách nhiệm thụ lý rà soát. 
                        Sau khi bấm nút xác nhận, trạng thái hồ sơ sẽ tự động chuyển sang <b>'Đang rà soát'</b>.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Lọc danh sách nhân viên pháp chế
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

            col_cand, col_inst = st.columns([1, 1.2])
            with col_cand:
                sel_cand_idx = st.selectbox(
                    "Chọn chuyên viên pháp chế đảm nhiệm: *",
                    range(len(legal_candidates)),
                    format_func=lambda i: candidate_labels[i],
                    key="sel_assign_legal_staff"
                )
                chosen_candidate = legal_candidates[sel_cand_idx]

            with col_inst:
                director_instruction = st.text_area(
                    "Ý kiến chỉ đạo / Yêu cầu trọng tâm của Giám đốc (tùy chọn):",
                    placeholder="Ví dụ: Rà soát kỹ điều khoản phạt vi phạm hợp đồng và cam kết SLA; thời hạn hoàn thành trước ngày 25/04...",
                    height=80,
                    key="director_instruction_input"
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
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
                    "🚀 XÁC NHẬN GIAO VIỆC & CHUYỂN SANG TRẠNG THÁI 'ĐANG RÀ SOÁT'",
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
    # TAB 3: ĐIỀU CHUYỂN NHÂN SỰ (FOOTER ACTION BAR DƯỚI CÙNG)
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
            transfer_contract_obj = in_review_list[sel_trans_idx]
            current_assignee_username = transfer_contract_obj.get("assigned_to", "")
            
            current_assignee_user = next((u for u in all_users if u.get("username") == current_assignee_username), None)
            current_assignee_name = current_assignee_user.get("full_name", current_assignee_username) if current_assignee_user else current_assignee_username

            st.markdown("---")
            st.markdown("#### 📌 Thông Tin Hồ Sơ & Lịch Sử Thụ Lý")
            col_t1, col_t2 = st.columns([1, 1])

            with col_t1:
                st.markdown(f"- **Mã hợp đồng:** `{transfer_contract_obj.get('id')}`")
                st.markdown(f"- **Tên hợp đồng:** **{transfer_contract_obj.get('title')}**")
                st.markdown(f"- **Đối tác:** {transfer_contract_obj.get('partner_name')}")
                st.markdown(f"- **Giá trị:** {transfer_contract_obj.get('value_vnd', 0):,.0f} VNĐ")
                st.markdown(f"- **Phòng ban đề xuất:** {transfer_contract_obj.get('department')}")
                st.markdown(
                    f"- **Chuyên viên đang phụ trách hiện tại:** "
                    f"<span style='color: #DC2626; font-weight: 700;'>{current_assignee_name} (@{current_assignee_username})</span>",
                    unsafe_allow_html=True
                )

            with col_t2:
                reassignment_hist = transfer_contract_obj.get("reassignment_history", [])
                st.markdown("###### 📜 Lịch sử các lần điều chuyển:")
                if reassignment_hist:
                    for idx, rh in enumerate(reassignment_hist, 1):
                        st.markdown(
                            f"<div style='font-size: 0.8rem; background: #F8FAFC; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; border: 1px solid #E2E8F0;'>"
                            f"<b>Lần {idx}:</b> `{rh.get('transferred_at')}` — Từ <code>@{rh.get('from_user')}</code> sang <code>@{rh.get('to_user')}</code><br/>"
                            f"<i>Lý do:</i> {rh.get('reason')}</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("Chưa có lần điều chuyển nào trước đây.")

            # ACTION BAR & HƯỚNG DẪN Ở CHÂN TRANG ĐIỀU CHUYỂN
            st.markdown(
                """
                <div class="dir-footer-action-bar">
                    <div class="dir-footer-header">
                        <span>🔄 KHU VỰC ĐIỀU PHỐI NHÂN SỰ MỚI (CHÂN TRANG)</span>
                    </div>
                    <div class="dir-footer-desc">
                        Chọn chuyên viên pháp chế tiếp nhận mới và nêu rõ lý do điều chuyển. 
                        Hệ thống sẽ lưu vết lịch sử điều phối và gửi thông báo cho chuyên viên mới.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

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

            col_ncand, col_nreason = st.columns([1, 1.2])
            with col_ncand:
                sel_new_cand_idx = st.selectbox(
                    "Chọn chuyên viên tiếp nhận mới: *",
                    range(len(legal_candidates)),
                    format_func=lambda i: new_cand_labels[i],
                    key="sel_new_legal_candidate"
                )
                chosen_new_candidate = legal_candidates[sel_new_cand_idx]

            with col_nreason:
                transfer_reason = st.text_area(
                    "Lý do điều chuyển nhân sự: *",
                    placeholder="Ghi rõ lý do (ví dụ: Chuyên viên cũ đi công tác/quá tải nhiệm vụ, chuyển giao theo phân công chuyên môn lĩnh vực...)",
                    height=80,
                    key="transfer_reason_input"
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if readonly:
                st.button(
                    "🔒 Xác Nhận Điều Chuyển Hồ Sơ (Vô hiệu hóa trong chế độ Read-Only)",
                    disabled=True,
                    use_container_width=True,
                    key=f"btn_transfer_confirm_{transfer_contract_obj.get('id')}"
                )
                st.caption("🛡️ Quyền Read-Only: Tài khoản Admin chỉ giám sát, không thực hiện điều chuyển.")
                btn_do_transfer = False
            else:
                btn_do_transfer = st.button(
                    "🔄 XÁC NHẬN ĐIỀU CHUYỂN HỒ SƠ SANG CHUYÊN VIÊN MỚI",
                    type="primary",
                    use_container_width=True,
                    key=f"btn_transfer_confirm_{transfer_contract_obj.get('id')}"
                )

            if btn_do_transfer:
                if not transfer_reason.strip():
                    st.error("Vui lòng nhập lý do điều chuyển nhân sự!")
                elif chosen_new_candidate.get("username") == current_assignee_username:
                    st.warning("Chuyên viên được chọn trùng với chuyên viên đang phụ trách hiện tại! Vui lòng chọn nhân sự khác.")
                else:
                    success, msg = transfer_contract(
                        contract_id=transfer_contract_obj.get("id"),
                        new_assignee_username=chosen_new_candidate.get("username"),
                        new_assignee_name=chosen_new_candidate.get("full_name"),
                        transferred_by=current_username,
                        transfer_reason=transfer_reason
                    )
                    if success:
                        st.success(
                            f"🎉 Đã điều chuyển hồ sơ **'{transfer_contract_obj.get('id')}'** từ chuyên viên "
                            f"**{current_assignee_name}** (`@{current_assignee_username}`) sang **{chosen_new_candidate.get('full_name')}** (`@{chosen_new_candidate.get('username')}`) thành công!"
                        )
                        st.rerun()
                    else:
                        st.error(msg)

    # ==========================================================================
    # TAB 4: PHÊ DUYỆT & BAN HÀNH (BOTTOM FOOTER ACTION SECTION)
    # ==========================================================================
    with tab_approve:
        st.subheader("✍️ Phê Duyệt & Ban Hành Hợp Đồng")
        st.markdown(
            "Giám đốc Pháp chế đối chiếu nội dung văn bản hợp đồng (PDF) và toàn bộ lịch sử ý kiến thẩm định "
            "của chuyên viên pháp chế để ra quyết định **'Ký duyệt phát hành'** hoặc **'Yêu cầu làm lại'** tại khu vực Chân trang."
        )

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

            # MÀN HÌNH CHIA 2 CỘT HIỂN THỊ NỘI DUNG VÀ Ý KIẾN
            col_pdf_left, col_review_right = st.columns([1.05, 0.95])

            # ------------------------------------------------------------------
            # CỘT TRÁI: HIỂN THỊ TRÌNH XEM PDF ĐỐI CHIẾU
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
                        att_fname = chosen_appr_att.get("file_name", "hop_dong.pdf")
                        chk_item = chosen_appr_att.get("checklist_item", "Dự thảo hợp đồng")
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
                                        <div><b>Bên đề xuất (Bên A):</b> {company_name} - {appr_contract.get('department')}</div>
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

                    # Tải file PDF dự phòng
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
            # CỘT PHẢI: TOÀN BỘ LỊCH SỬ Ý KIẾN THẨM ĐỊNH CỦA PHÁP CHẾ
            # ------------------------------------------------------------------
            with col_review_right:
                st.markdown("#### ⚖️ Lịch Sử Thẩm Định Của Phòng Pháp Chế")

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
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
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
                                <div style="background: #FFFFFF; border-left: 3px solid #3B82F6; padding: 8px 12px; margin-top: 4px; border-radius: 4px; font-style: italic;">
                                    "{rev_notes}"
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # CHI TIẾT TỪNG MỤC CHECKLIST
                    st.markdown("##### 📋 Chi tiết đánh giá từng tiêu chí Checklist:")
                    chk_map = l_rev.get("checklist_results", {})
                    if chk_map:
                        for it_key, it_val in chk_map.items():
                            i_stat = it_val.get("status", "Đạt")
                            i_com = it_val.get("comment", "")
                            st_icon = "🟢 Đạt" if i_stat == "Đạt" else ("🔴 Không đạt" if i_stat == "Không đạt" else "🟡 Có góp ý")
                            st.markdown(
                                f"""
                                <div style="padding: 8px 12px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; margin-bottom: 6px; font-size: 0.83rem;">
                                    <div style="display: flex; justify-content: space-between;">
                                        <b>{it_key}</b>
                                        <span style="font-weight: 700;">{st_icon}</span>
                                    </div>
                                    {f'<div style="color: #64748B; font-size: 0.78rem; margin-top: 3px; font-style: italic;">↳ Góp ý: "{i_com}"</div>' if i_com else ''}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    else:
                        st.caption("Chưa có bảng checklist chi tiết.")

            # ------------------------------------------------------------------
            # BỐ CỤC ACTION BAR & HƯỚNG DẪN Ở CHÂN TRANG (BOTTOM FOOTER SECTION)
            # ------------------------------------------------------------------
            st.markdown(
                """
                <div class="dir-footer-action-bar">
                    <div class="dir-footer-header">
                        <span>🎯 KHU VỰC QUYẾT ĐỊNH PHÊ DUYỆT CỦA GIÁM ĐỐC (CHÂN TRANG)</span>
                    </div>
                    <div class="dir-footer-desc">
                        Sau khi đã kiểm tra toàn bộ văn bản đối chiếu (PDF) bên trái và kết quả thẩm định checklist bên phải, 
                        Giám đốc nhập ý kiến chỉ đạo cuối cùng và lựa chọn: <b>'Ký duyệt phát hành'</b> (hồ sơ Hoàn tất) hoặc <b>'Yêu cầu làm lại'</b> (trả về cho chuyên viên điều chỉnh).
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            dir_opinion = st.text_area(
                "Ý kiến phê duyệt / Chỉ đạo ban hành của Giám đốc:",
                value="Đồng ý thông qua nội dung dự thảo hợp đồng theo thẩm định của Phòng Pháp chế. Cho phép phát hành và tiến hành ký kết." if not readonly else "Chế độ Giám sát Hệ thống (Read-Only) - Chỉ tra cứu hồ sơ và phiếu thẩm định.",
                height=90,
                disabled=readonly,
                key=f"dir_opinion_input_{appr_contract.get('id')}"
            )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            col_btn_approve, col_btn_reject = st.columns(2)

            if readonly:
                with col_btn_approve:
                    st.button(
                        "🔒 Ký duyệt phát hành (Vô hiệu hóa trong chế độ Read-Only)",
                        disabled=True,
                        use_container_width=True,
                        key=f"btn_approve_action_{appr_contract.get('id')}"
                    )
                with col_btn_reject:
                    st.button(
                        "🔒 Yêu cầu làm lại (Vô hiệu hóa trong chế độ Read-Only)",
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
                        "✅ KÝ DUYỆT PHÁT HÀNH HỢP ĐỒNG",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_approve_action_{appr_contract.get('id')}"
                    )

                with col_btn_reject:
                    btn_reject_action = st.button(
                        "↩️ YÊU CẦU LÀM LẠI / TRẢ HỒ SƠ CHỈNH SỬA",
                        type="secondary",
                        use_container_width=True,
                        key=f"btn_reject_action_{appr_contract.get('id')}"
                    )

            # XỬ LÝ KHI GIÁM ĐỐC BẤM NÚT
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

            # NÚT XUẤT VÀ TẢI VỀ PHIẾU GÓP Ý PDF
            stored_pdf = st.session_state.get(f"last_gen_pdf_{appr_contract.get('id')}")
            stored_pdf_name = st.session_state.get(f"last_gen_pdf_name_{appr_contract.get('id')}", f"Phieu_gop_y_{appr_contract.get('id')}.pdf")

            if not stored_pdf:
                try:
                    stored_pdf = generate_review_pdf(
                        contract=appr_contract,
                        action_type="approve",
                        director_notes=dir_opinion.strip(),
                        director_name=current_fullname
                    )
                    stored_pdf_name = f"Phieu_gop_y_{appr_contract.get('id')}.pdf"
                except Exception as pdf_err:
                    stored_pdf = None
                    st.caption(f"⚠️ Bản xem trước PDF: {str(pdf_err)}")

            if stored_pdf:
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                st.download_button(
                    label=f"📥 Tải 'Phiếu góp ý Hợp đồng' ({stored_pdf_name})",
                    data=stored_pdf,
                    file_name=stored_pdf_name,
                    mime="application/pdf",
                    key=f"btn_download_review_pdf_{appr_contract.get('id')}",
                    use_container_width=True
                )
