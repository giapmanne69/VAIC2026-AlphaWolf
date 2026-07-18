import os
from pathlib import Path
import openpyxl
from docx import Document
import pdfplumber
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None


class DocParser:
    def __init__(self, tesseract_cmd_path: str = None):
        # Cấu hình đường dẫn Tesseract binary trên Windows nếu có
        if tesseract_cmd_path and pytesseract:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
        elif pytesseract and os.name == "nt":
            # Thử tìm các đường dẫn mặc định của Tesseract trên Windows
            default_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Users\DELL\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
            ]
            for p in default_paths:
                if Path(p).exists():
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def parse(self, file_path: str) -> str:
        """
        Tự động phân loại định dạng và gọi hàm parser tương ứng.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
            
        ext = path.suffix.lower()
        if ext == ".docx":
            return self.parse_docx(path)
        elif ext in [".xlsx", ".xls"]:
            return self.parse_xlsx(path)
        elif ext == ".pdf":
            return self.parse_pdf(path)
        elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            return self.parse_image(path)
        else:
            raise ValueError(f"Định dạng tệp không được hỗ trợ: {ext}")

    def parse_docx(self, path: Path) -> str:
        """
        Đọc tệp Word (.docx), trích xuất văn bản từ đoạn văn và bảng biểu.
        """
        doc = Document(path)
        content = []
        
        # 1. Đọc qua tất cả các phần tử trong document để giữ nguyên thứ tự
        for element in doc.element.body:
            if element.tag.endswith('p'):  # Paragraph
                p_text = element.text if hasattr(element, 'text') else ""
                # Tìm đoạn tương ứng trong doc.paragraphs
                for p in doc.paragraphs:
                    if p._element == element:
                        p_text = p.text
                        break
                if p_text.strip():
                    content.append(p_text.strip())
            elif element.tag.endswith('tbl'):  # Table
                # Tìm bảng tương ứng trong doc.tables
                table = None
                for t in doc.tables:
                    if t._element == element:
                        table = t
                        break
                if table:
                    table_content = []
                    for row in table.rows:
                        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        table_content.append(" | ".join(row_cells))
                    content.append("\n[BẢNG BIỂU]:\n" + "\n".join(table_content) + "\n")
                    
        return "\n".join(content)

    def parse_xlsx(self, path: Path) -> str:
        """
        Đọc bảng tính Excel (.xlsx), chuyển đổi các bảng số liệu thành dạng văn bản phân tách bằng dấu gạch đứng.
        """
        wb = openpyxl.load_workbook(path, data_only=True)
        content = []
        
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            content.append(f"\n--- Trang tính: {sheet_name} ---")
            
            # Quét các dòng có chứa dữ liệu
            for r in range(1, sheet.max_row + 1):
                row_vals = []
                has_data = False
                for c in range(1, sheet.max_column + 1):
                    val = sheet.cell(row=r, column=c).value
                    if val is not None:
                        has_data = True
                        row_vals.append(str(val).strip())
                    else:
                        row_vals.append("")
                # Chỉ lấy dòng có chứa ít nhất 1 ô dữ liệu để tránh file quá loãng
                if has_data:
                    content.append(" | ".join(row_vals))
                    
        return "\n".join(content)

    def parse_pdf(self, path: Path) -> str:
        """
        Đọc tệp PDF dạng văn bản bằng pdfplumber.
        Nếu trang PDF rỗng (nhiều khả năng là file PDF Scan dạng ảnh), sẽ thử OCR trang đó.
        """
        content = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    content.append(f"\n--- Trang PDF {i+1} ---")
                    content.append(text.strip())
                else:
                    # Rỗng chữ -> Có thể là PDF Scan, thử OCR nếu có thư viện
                    content.append(f"\n--- Trang PDF Scan {i+1} ---")
                    try:
                        # Convert trang PDF sang Image để OCR
                        # (Yêu cầu cài đặt pdf2image và poppler, nếu không có ta cảnh báo)
                        content.append("[Cảnh báo: Phát hiện trang quét PDF Scan dạng ảnh, cần chạy OCR]")
                    except Exception as e:
                        content.append(f"[Lỗi OCR trang PDF: {str(e)}]")
                        
        return "\n".join(content)

    def parse_image(self, path: Path) -> str:
        """
        OCR hình ảnh sử dụng Tesseract.
        """
        if not pytesseract:
            return "[Lỗi: Thư viện pytesseract chưa được cài đặt để xử lý OCR ảnh]"
            
        try:
            image = Image.open(path)
            # Chạy OCR với ngôn ngữ tiếng Việt (vie) và tiếng Anh (eng)
            text = pytesseract.image_to_string(image, lang="vie+eng")
            return text.strip()
        except Exception as e:
            return f"[Lỗi OCR ảnh {path.name}: {str(e)}. Hãy đảm bảo đã cài đặt Tesseract binary trên Windows và cấu hình đúng đường dẫn]"
