"""
HỆ THỐNG QUẢN TRỊ HỢP ĐỒNG - WORKFLOW ENGINE (CORE LOGIC)
File: workflow_engine.py
Mục đích: Tách toàn bộ logic xử lý quy trình và trạng thái hồ sơ hợp đồng.
Bao gồm:
- submit_new_contract: Xử lý khi phòng ban nộp hồ sơ mới.
- assign_contract: Giám đốc phân công chuyên viên thụ lý.
- transfer_contract: Điều chuyển hồ sơ sang chuyên viên khác.
- save_legal_review: Pháp chế lưu kết quả rà soát checklist và chuyển trình duyệt.
- approve_contract: Giám đốc phê duyệt phát hành hoặc yêu cầu làm lại, xuất PDF và gửi email.
- ContractReviewPDF, generate_review_pdf, send_approval_email.
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF

from db_utils import (
    get_contracts, save_contracts,
    get_config, get_users
)

# ==============================================================================
# 1. CÔNG CỤ TẠO FILE PDF & GỬI EMAIL THÔNG BÁO TỰ ĐỘNG
# ==============================================================================
class ContractReviewPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 64, 175)
        self.rect(0, 0, 210, 8, "F")
        self.ln(4)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(226, 232, 240)
        self.line(10, 281, 200, 281)
        font_to_use = getattr(self, "custom_font_family", "Helvetica")
        try:
            self.set_font(font_to_use, "", 8)
        except Exception:
            self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f"Trang {self.page_no()} | He thong Quan tri Hop dong - Asia Holdings", 0, 0, "C")

def get_unicode_font_paths():
    """Tìm font TTF hỗ trợ Unicode tiếng Việt trên hệ thống"""
    font_candidates = [
        "/Arial.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]
    bold_candidates = [
        "/Arial-Bold.ttf",
        "Arial-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf"
    ]
    regular = next((p for p in font_candidates if os.path.exists(p)), None)
    bold = next((p for p in bold_candidates if os.path.exists(p)), None)
    if not bold and regular:
        bold = regular
    return regular, bold

def generate_review_pdf(contract: dict, action_type: str, director_notes: str, director_name: str) -> bytes:
    """
    Dùng fpdf tạo file PDF 'Phiếu góp ý Hợp đồng'.
    Bắt buộc cấu hình font Unicode (như Arial.ttf) để tiếng Việt trên PDF không bị lỗi.
    Bao gồm:
    - Tên, Loại hợp đồng, Đối tác, Phòng ban, Giá trị
    - Đánh giá các mục Checklist
    - Kết luận và Quyết định phê duyệt
    """
    pdf = ContractReviewPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    font_path, font_bold_path = get_unicode_font_paths()
    font_family = "Helvetica"
    if font_path:
        try:
            pdf.add_font("ArialUnicode", "", font_path, uni=True)
            if font_bold_path:
                pdf.add_font("ArialUnicode", "B", font_bold_path, uni=True)
            else:
                pdf.add_font("ArialUnicode", "B", font_path, uni=True)
            font_family = "ArialUnicode"
        except Exception:
            font_family = "Helvetica"

    pdf.custom_font_family = font_family

    # 1. TIÊU ĐỀ DOANH NGHIỆP
    pdf.set_font(font_family, "B", 11)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, "TẬP ĐOÀN CÔNG NGHỆ VÀ THƯƠNG MẠI Á CHÂU - ASIA HOLDINGS", 0, 1, "C")
    pdf.set_font(font_family, "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "HỘI ĐỒNG THẨM ĐỊNH & PHÊ DUYỆT PHÁP LÝ HỢP ĐỒNG", 0, 1, "C")

    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(70, 24, 140, 24)
    pdf.ln(7)

    # Tiêu đề chính
    pdf.set_font(font_family, "B", 15)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 8, "PHIẾU GÓP Ý & THẨM ĐỊNH HỢP ĐỒNG", 0, 1, "C")

    pdf.set_font(font_family, "", 8.5)
    pdf.set_text_color(71, 85, 105)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 5, f"Mã hồ sơ: {contract.get('id', 'N/A')} | Thời gian xuất phiếu: {now_str}", 0, 1, "C")
    pdf.ln(3)

    # 2. PHẦN I: THÔNG TIN HỒ SƠ HỢP ĐỒNG
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  I. THÔNG TIN HỒ SƠ HỢP ĐỒNG", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    info_rows = [
        ("Mã hợp đồng:", str(contract.get("id", "")), "Loại hợp đồng:", str(contract.get("contract_type", "Hợp đồng kinh tế"))),
        ("Tên hợp đồng:", str(contract.get("title", "")), "Phòng ban đề xuất:", str(contract.get("department", ""))),
        ("Đối tác (Bên B):", str(contract.get("partner_name", "")), "Giá trị (VNĐ):", f"{contract.get('value_vnd', 0):,.0f} VNĐ"),
        ("Người đề xuất:", str(contract.get("created_by", "")), "Thời hạn hiệu lực:", f"{contract.get('effective_date', '')} đến {contract.get('expiration_date', '')}")
    ]

    for label1, val1, label2, val2 in info_rows:
        pdf.set_font(font_family, "B", 8.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(32, 5.5, label1, 0, 0, "L")
        pdf.set_font(font_family, "", 8.5)
        pdf.cell(63, 5.5, val1[:40], 0, 0, "L")

        pdf.set_font(font_family, "B", 8.5)
        pdf.cell(35, 5.5, label2, 0, 0, "L")
        pdf.set_font(font_family, "", 8.5)
        pdf.cell(60, 5.5, val2[:40], 0, 1, "L")

    pdf.ln(2.5)

    # 3. PHẦN II: KẾT QUẢ THẨM ĐỊNH CỦA BAN PHÁP CHẾ
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  II. KẾT QUẢ THẨM ĐỊNH CỦA BAN PHÁP CHẾ", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    lr = contract.get("legal_review", {})
    reviewer_name = lr.get("reviewer_name", contract.get("assigned_to", "Chuyên viên Pháp chế"))
    reviewed_at = lr.get("reviewed_at", "Đã thẩm định")
    assessment = lr.get("general_assessment", "Đủ điều kiện pháp lý - Đề xuất ký")
    notes = lr.get("summary_notes", "Không có ghi chú thêm.")

    pdf.set_font(font_family, "B", 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(38, 5.5, "Chuyên viên thẩm định:", 0, 0, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.cell(57, 5.5, f"{reviewer_name} (@{contract.get('assigned_to', '')})", 0, 0, "L")

    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(35, 5.5, "Thời gian thẩm định:", 0, 0, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.cell(60, 5.5, str(reviewed_at), 0, 1, "L")

    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(38, 5.5, "Đánh giá tổng quát:", 0, 0, "L")
    pdf.set_font(font_family, "B", 9)
    if "Đủ điều kiện" in assessment:
        pdf.set_text_color(22, 101, 52)
    elif "Không đủ" in assessment:
        pdf.set_text_color(185, 28, 28)
    else:
        pdf.set_text_color(180, 83, 9)
    pdf.cell(0, 5.5, f"[ {assessment} ]", 0, 1, "L")

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(0, 5, "Ý kiến kết luận của Pháp chế:", 0, 1, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.multi_cell(0, 4.8, f'"{notes}"')
    pdf.ln(2.5)

    # 4. PHẦN III: BẢNG ĐÁNH GIÁ CHI TIẾT TỪNG MỤC CHECKLIST
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  III. BẢNG ĐÁNH GIÁ CHI TIẾT CÁC MỤC CHECKLIST", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    pdf.set_fill_color(30, 64, 175)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_family, "B", 8)
    pdf.cell(10, 6, "STT", 1, 0, "C", fill=True)
    pdf.cell(65, 6, "Hạng mục kiểm tra", 1, 0, "L", fill=True)
    pdf.cell(28, 6, "Kết quả", 1, 0, "C", fill=True)
    pdf.cell(87, 6, "Nội dung ý kiến góp ý / Ghi chú", 1, 1, "L", fill=True)

    chk_results = lr.get("checklist_results", {})
    if not chk_results:
        chk_results = {
            "Dự thảo Hợp đồng chi tiết": {"status": "Đạt", "comment": "Điều khoản rõ ràng, tuân thủ pháp luật."},
            "Hồ sơ năng lực & Pháp lý đối tác": {"status": "Đạt", "comment": "Đầy đủ ĐKKD và tài liệu đính kèm."}
        }

    row_idx = 1
    pdf.set_text_color(30, 41, 59)
    for item_name, item_res in chk_results.items():
        st_val = item_res.get("status", "Đạt")
        cm_val = item_res.get("comment", "Không có góp ý thêm.")

        pdf.set_font(font_family, "", 8)
        pdf.cell(10, 5.5, str(row_idx), 1, 0, "C")
        pdf.cell(65, 5.5, item_name[:36], 1, 0, "L")

        pdf.set_font(font_family, "B", 8)
        if st_val == "Đạt":
            pdf.set_text_color(22, 101, 52)
        elif st_val == "Không đạt":
            pdf.set_text_color(185, 28, 28)
        else:
            pdf.set_text_color(180, 83, 9)
        pdf.cell(28, 5.5, st_val, 1, 0, "C")

        pdf.set_text_color(30, 41, 59)
        pdf.set_font(font_family, "", 7.8)
        pdf.cell(87, 5.5, cm_val[:55], 1, 1, "L")
        row_idx += 1

    pdf.ln(2.5)

    # 5. PHẦN IV: QUYẾT ĐỊNH & PHÊ DUYỆT CỦA GIÁM ĐỐC
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font(font_family, "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6.5, "  IV. QUYẾT ĐỊNH & PHÊ DUYỆT CỦA BAN GIÁM ĐỐC", 0, 1, "L", fill=True)
    pdf.ln(1.5)

    decision_text = "KÝ DUYỆT PHÁT HÀNH (HOÀN TẤT)" if action_type == "approve" else "YÊU CẦU LÀM LẠI / ĐIỀU CHỈNH"
    pdf.set_font(font_family, "B", 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(42, 5.5, "Quyết định của Giám đốc:", 0, 0, "L")

    if action_type == "approve":
        pdf.set_text_color(22, 101, 52)
    else:
        pdf.set_text_color(185, 28, 28)
    pdf.cell(0, 5.5, f"[ {decision_text} ]", 0, 1, "L")

    pdf.set_text_color(30, 41, 59)
    pdf.set_font(font_family, "B", 8.5)
    pdf.cell(0, 5, "Ý kiến chỉ đạo của Giám đốc:", 0, 1, "L")
    pdf.set_font(font_family, "", 8.5)
    pdf.multi_cell(0, 4.8, f'"{director_notes}"')
    pdf.ln(4)

    # CHỮ KÝ ĐIỆN TỬ
    pdf.set_font(font_family, "B", 9)
    pdf.cell(95, 5, "CHUYÊN VIÊN THẨM ĐỊNH", 0, 0, "C")
    pdf.cell(95, 5, "GIÁM ĐỐC PHÁP CHẾ PHÊ DUYỆT", 0, 1, "C")

    pdf.set_font(font_family, "I", 7.8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(95, 4, "(Ký, ghi rõ họ tên)", 0, 0, "C")
    pdf.cell(95, 4, "(Ký duyệt điện tử)", 0, 1, "C")
    pdf.ln(10)

    pdf.set_font(font_family, "B", 9)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(95, 5, str(reviewer_name), 0, 0, "C")
    pdf.cell(95, 5, str(director_name), 0, 1, "C")

    try:
        out = pdf.output(dest="S")
        if isinstance(out, str):
            return out.encode("latin1")
        return bytes(out)
    except Exception:
        return str(pdf.output()).encode("latin1")

def send_approval_email(contract: dict, pdf_bytes: bytes, pdf_filename: str, action_type: str, director_notes: str) -> tuple[bool, str]:
    """
    Dùng smtplib đọc cấu hình từ config.json và email phòng ban từ users.json
    để gửi email tự động đính kèm file PDF (có try-except báo lỗi nếu sai cấu hình mail).
    """
    config_data = get_config()
    smtp_settings = config_data.get("smtp_settings", {})

    server_host = smtp_settings.get("server", "smtp.gmail.com")
    server_port = int(smtp_settings.get("port", 587))
    sender_email = smtp_settings.get("sender_email", "notification@asiaholdings.vn")
    app_password = smtp_settings.get("app_password", "")
    use_tls = smtp_settings.get("use_tls", True)

    users_list = get_users()

    created_by_user = next((u for u in users_list if u.get("username") == contract.get("created_by")), None)
    assigned_user = next((u for u in users_list if u.get("username") == contract.get("assigned_to")), None)

    to_emails = []
    if created_by_user and created_by_user.get("email"):
        to_emails.append(created_by_user.get("email"))
    if assigned_user and assigned_user.get("email"):
        to_emails.append(assigned_user.get("email"))

    if not to_emails:
        to_emails = [f"{contract.get('created_by', 'kinhdoanh01')}@congty.com.vn"]

    to_emails = list(set(to_emails))

    action_label = "Ký duyệt phát hành (Hoàn tất)" if action_type == "approve" else "Yêu cầu làm lại"
    subject = f"[Asia Holdings] Thông báo {action_label}: Hợp đồng {contract.get('id')} - {contract.get('title')}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    body_content = f"""
Kính gửi Phòng ban đề xuất ({contract.get('department')}) và Phòng Pháp chế,

Hệ thống Quản trị Hợp đồng Asia Holdings thông báo kết quả phê duyệt hồ sơ từ Ban Giám đốc:

1. THÔNG TIN HỒ SƠ:
   - Mã hợp đồng: {contract.get('id')}
   - Tên hợp đồng: {contract.get('title')}
   - Đối tác: {contract.get('partner_name')}
   - Giá trị: {contract.get('value_vnd', 0):,.0f} VNĐ
   - Phòng ban đề xuất: {contract.get('department')} (Người tạo: @{contract.get('created_by')})

2. KẾT QUẢ PHÊ DUYỆT:
   - Quyết định: {action_label}
   - Ý kiến chỉ đạo của Giám đốc: "{director_notes}"
   - Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Đính kèm email này là tập tin PDF 'Phiếu góp ý Hợp đồng' bản chính thức (có chữ ký phê duyệt).

Trân trọng,
Ban Giám đốc Pháp chế - Asia Holdings
    """.strip()

    msg.attach(MIMEText(body_content, "plain", "utf-8"))

    if pdf_bytes:
        try:
            part = MIMEApplication(pdf_bytes, _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
            msg.attach(part)
        except Exception:
            pass

    try:
        if not app_password:
            return (
                False,
                f"Đã tạo email gửi tới [{', '.join(to_emails)}] nhưng chưa gửi thực tế do 'app_password' trong config.json đang để trống. "
                f"(Vui lòng điền Mật khẩu ứng dụng SMTP tại config.json để gửi thật qua {server_host})."
            )

        if use_tls:
            with smtplib.SMTP(server_host, server_port, timeout=10) as server:
                server.starttls()
                server.login(sender_email, app_password)
                server.sendmail(sender_email, to_emails, msg.as_string())
        else:
            with smtplib.SMTP(server_host, server_port, timeout=10) as server:
                server.login(sender_email, app_password)
                server.sendmail(sender_email, to_emails, msg.as_string())

        return (True, f"Đã gửi email thông báo tự động đính kèm file PDF tới: {', '.join(to_emails)}")
    except Exception as smtp_error:
        return (False, f"Lỗi gửi email qua {server_host}:{server_port} ({str(smtp_error)}). Đã lưu phiếu góp ý PDF thành công!")



# ==============================================================================
# 2. CÁC HÀM XỬ LÝ QUY TRÌNH HỢP ĐỒNG (WORKFLOW ENGINE CORE)
# ==============================================================================

def submit_new_contract(
    contract_title: str,
    partner_name: str,
    contract_type: str,
    contract_value: float,
    current_username: str,
    current_department: str,
    workflow_id: str,
    effective_date: str,
    expiration_date: str,
    notes: str,
    attachments: list
) -> tuple[bool, str, str]:
    """
    Xử lý khi phòng ban nộp hồ sơ mới.
    Tự động sinh mã hợp đồng, khởi tạo trạng thái 'Chờ Giám đốc phân công',
    và lưu vào contracts.json.
    Trả về: (thành_công: bool, mã_hợp_đồng: str, thông_báo: str)
    """
    try:
        all_contracts = get_contracts()
        year_str = str(datetime.now().year)
        contract_code = f"HD-{year_str}-{str(len(all_contracts) + 1).zfill(3)}"
        
        new_contract_record = {
            "id": contract_code,
            "title": contract_title.strip(),
            "partner_name": partner_name.strip(),
            "contract_type": contract_type,
            "value_vnd": int(contract_value),
            "created_by": current_username,
            "department": current_department,
            "workflow_id": workflow_id or "WF_DEFAULT",
            "current_step": 1,
            "status": "Chờ Giám đốc phân công",
            "effective_date": str(effective_date),
            "expiration_date": str(expiration_date),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "notes": (notes or "").strip(),
            "attachments": attachments or []
        }
        
        all_contracts.append(new_contract_record)
        if save_contracts(all_contracts):
            return True, contract_code, f"Nộp hồ sơ '{contract_code}: {contract_title}' thành công! Trạng thái: 'Chờ Giám đốc phân công'."
        return False, "", "Lỗi khi ghi dữ liệu hợp đồng vào contracts.json!"
    except Exception as e:
        return False, "", f"Lỗi hệ thống khi nộp hồ sơ: {str(e)}"


def assign_contract(
    contract_id: str,
    assignee_username: str,
    director_username: str,
    director_instruction: str = ""
) -> tuple[bool, str]:
    """
    Giám đốc phân công chuyên viên pháp chế thụ lý hồ sơ.
    Cập nhật trạng thái thành 'Đang rà soát', gán assigned_to và chỉ đạo.
    """
    try:
        all_contracts = get_contracts()
        target = next((c for c in all_contracts if c.get("id") == contract_id), None)
        if not target:
            return False, f"Không tìm thấy hồ sơ có mã '{contract_id}'!"
        
        target["status"] = "Đang rà soát"
        target["assigned_to"] = assignee_username
        target["assigned_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target["assigned_by"] = director_username
        target["director_instruction"] = (director_instruction or "").strip()
        
        if save_contracts(all_contracts):
            return True, f"Đã giao hồ sơ '{contract_id}' cho chuyên viên @{assignee_username} thành công!"
        return False, "Lỗi khi lưu contracts.json!"
    except Exception as e:
        return False, f"Lỗi hệ thống khi phân công: {str(e)}"


def transfer_contract(
    contract_id: str,
    new_assignee_username: str,
    new_assignee_name: str,
    transferred_by: str,
    transfer_reason: str = ""
) -> tuple[bool, str]:
    """
    Điều chuyển hồ sơ đang rà soát sang chuyên viên khác.
    Lưu lại lịch sử điều chuyển trong contract['reassignment_history'].
    """
    try:
        all_contracts = get_contracts()
        target = next((c for c in all_contracts if c.get("id") == contract_id), None)
        if not target:
            return False, f"Không tìm thấy hồ sơ có mã '{contract_id}'!"
        
        old_assignee = target.get("assigned_to", "Chưa gán")
        users_list = get_users()
        old_assignee_obj = next((u for u in users_list if u.get("username") == old_assignee), None)
        old_name = old_assignee_obj.get("full_name", old_assignee) if old_assignee_obj else old_assignee
        
        if "reassignment_history" not in target:
            target["reassignment_history"] = []
        
        target["reassignment_history"].append({
            "from_user": old_assignee,
            "from_user_name": old_name,
            "to_user": new_assignee_username,
            "to_user_name": new_assignee_name,
            "transferred_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "transferred_by": transferred_by,
            "reason": (transfer_reason or "").strip()
        })
        
        target["assigned_to"] = new_assignee_username
        
        if save_contracts(all_contracts):
            return True, f"Đã điều chuyển hồ sơ '{contract_id}' từ @{old_assignee} sang @{new_assignee_username} thành công!"
        return False, "Lỗi khi lưu contracts.json!"
    except Exception as e:
        return False, f"Lỗi hệ thống khi điều chuyển: {str(e)}"


def save_legal_review(
    contract_id: str,
    reviewer_username: str,
    reviewer_fullname: str,
    general_assessment: str,
    summary_notes: str,
    checklist_results: dict
) -> tuple[bool, str]:
    """
    Pháp chế lưu kết quả rà soát checklist và chuyển trình Giám đốc duyệt.
    Đổi trạng thái sang 'Chờ Giám đốc duyệt'.
    """
    try:
        all_contracts = get_contracts()
        target = next((c for c in all_contracts if c.get("id") == contract_id), None)
        if not target:
            return False, f"Không tìm thấy hồ sơ có mã '{contract_id}'!"
        
        target["status"] = "Chờ Giám đốc duyệt"
        target["legal_review"] = {
            "reviewer": reviewer_username,
            "reviewer_name": reviewer_fullname,
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "general_assessment": general_assessment,
            "summary_notes": (summary_notes or "").strip(),
            "checklist_results": checklist_results or {}
        }
        
        if save_contracts(all_contracts):
            return True, f"Đã hoàn tất rà soát hồ sơ '{contract_id}' và chuyển sang 'Chờ Giám đốc duyệt'!"
        return False, "Lỗi khi lưu contracts.json!"
    except Exception as e:
        return False, f"Lỗi hệ thống khi lưu kết quả rà soát: {str(e)}"


def approve_contract(
    contract_id: str,
    action_type: str,
    director_username: str,
    director_fullname: str,
    director_notes: str
) -> tuple[bool, str, bytes, str, bool, str]:
    """
    Giám đốc phê duyệt hợp đồng:
    - action_type == 'approve': Ký duyệt phát hành -> Status = 'Hoàn tất'
    - action_type == 'reject': Yêu cầu làm lại -> Status = 'Đang rà soát'
    Tự động:
    1. Tạo file PDF Phiếu góp ý hợp đồng (Unicode).
    2. Gửi email thông báo tự động đính kèm file PDF.
    3. Cập nhật contracts.json.
    Trả về: (thành_công: bool, thông_báo: str, pdf_bytes: bytes, pdf_filename: str, email_ok: bool, email_msg: str)
    """
    try:
        all_contracts = get_contracts()
        target = next((c for c in all_contracts if c.get("id") == contract_id), None)
        if not target:
            return False, f"Không tìm thấy hồ sơ '{contract_id}'!", b"", "", False, ""
        
        new_status = "Hoàn tất" if action_type == "approve" else "Đang rà soát"
        pdf_filename = f"Phieu_gop_y_{target.get('id')}.pdf"
        
        # 1. Tạo PDF
        pdf_bytes = generate_review_pdf(
            contract=target,
            action_type=action_type,
            director_notes=(director_notes or "").strip(),
            director_name=director_fullname
        )
        
        # 2. Gửi email
        email_ok, email_msg = send_approval_email(
            contract=target,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
            action_type=action_type,
            director_notes=(director_notes or "").strip()
        )
        
        # 3. Cập nhật hợp đồng
        target["status"] = new_status
        target["director_approval"] = {
            "approved_by": director_username,
            "approved_by_name": director_fullname,
            "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Ký duyệt phát hành" if action_type == "approve" else "Yêu cầu làm lại",
            "notes": (director_notes or "").strip(),
            "review_sheet_pdf": pdf_filename
        }
        
        if save_contracts(all_contracts):
            msg = f"Đã ký duyệt phát hành hồ sơ '{contract_id}' thành công!" if action_type == "approve" else f"Đã chuyển hồ sơ '{contract_id}' về 'Đang rà soát' để làm lại!"
            return True, msg, pdf_bytes, pdf_filename, email_ok, email_msg
        return False, "Lỗi khi lưu contracts.json!", pdf_bytes, pdf_filename, email_ok, email_msg
    except Exception as e:
        return False, f"Lỗi hệ thống khi phê duyệt: {str(e)}", b"", "", False, ""
