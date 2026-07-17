# README.md

# Evaluation Pipeline

## Giới thiệu

Evaluation Pipeline được sử dụng để đánh giá chất lượng của **Agentic AI** trong việc **tự động tổng hợp, chuẩn hóa số liệu và sinh báo cáo quản trị cho UBND phường**.

Dự án **không sử dụng Fine-tuning**. Mục tiêu của Evaluation là đo lường chất lượng đầu ra và cải thiện **Data Pipeline**, **Knowledge Base (RAG)**, **Prompt**, **Memory** và **Rule Engine**.

---

# Evaluation Dataset

## Ground Truth

Ground Truth là các **báo cáo đã được lãnh đạo phê duyệt hoặc phát hành chính thức**, được sử dụng làm đáp án chuẩn để đánh giá AI.

### Nguồn dữ liệu

- Báo cáo tuần
- Báo cáo tháng
- Báo cáo quý
- Báo cáo năm
- Báo cáo chuyên đề

> Các báo cáo cần được ẩn danh (nếu có dữ liệu nhạy cảm) trước khi sử dụng.

---

## Bộ Test

Bộ test bao gồm nhiều tình huống tổng hợp báo cáo khác nhau nhằm đánh giá khả năng của AI.

Ví dụ:

- Thiếu dữ liệu từ một phòng ban
- Dữ liệu giữa các đơn vị không thống nhất
- Báo cáo có nhiều định dạng (Word, Excel, PDF)
- Số liệu cần hợp nhất từ nhiều nguồn
- Báo cáo có nhiều bảng biểu

---

# Evaluation Pipeline

```text
            Bộ dữ liệu đánh giá
     (Ground Truth + Bộ Test)
                 │
                 ▼
          AI sinh báo cáo
                 │
                 ▼
      So sánh với Ground Truth
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
 Data Accuracy
 Consistency Score
 Hallucination Rate
                 │
                 ▼
      Cán bộ nghiệp vụ đánh giá
                 │
                 ▼
         Human Edit Rate
                 │
                 ▼
      Đo thời gian xử lý (Latency)
                 │
                 ▼
      Dashboard đánh giá hệ thống
                 │
                 ▼
 Cải thiện Data Pipeline, RAG,
 Prompt và Rule Engine
```

---

# Evaluation Metrics

## 1. Data Accuracy

### Mục tiêu

Đánh giá mức độ chính xác của số liệu do AI sinh ra.

### Cách đánh giá

So sánh từng chỉ tiêu trong báo cáo AI với Ground Truth.

Ví dụ:

- Dân số (Tổng dân số, Tạm trú, Tạm vắng)
- Hồ sơ khiếu nại - tố cáo (Đơn tiếp nhận, Trạng thái giải quyết)
- KPI hoàn thành (Tỷ lệ giải quyết hồ sơ thủ tục hành chính đúng hạn)

---

## 2. Hallucination Rate

### Mục tiêu

Đánh giá tỷ lệ thông tin AI tự tạo ra nhưng không có trong dữ liệu nguồn hoặc tài liệu tham chiếu.

Ví dụ:

- Sinh thêm số liệu không tồn tại.
- Viết nhận định không có căn cứ.
- Thêm chỉ tiêu không xuất hiện trong dữ liệu.

---

## 3. Consistency Score

### Mục tiêu

Đánh giá tính nhất quán của báo cáo.

Bao gồm:

- Tổng bằng tổng các thành phần.
- Các bảng không mâu thuẫn nhau.
- Nội dung diễn giải phù hợp với số liệu.
- Thống nhất tên đơn vị, thời gian và chỉ tiêu.

---

## 4. Latency

### Mục tiêu

Đánh giá tốc độ sinh báo cáo.

Đo thời gian từ khi hệ thống nhận đủ dữ liệu đầu vào đến khi tạo xong báo cáo hoàn chỉnh.

---

## 5. Human Edit Rate

### Mục tiêu

Đánh giá mức độ AI cần sự can thiệp của con người.

Được đo bằng tỷ lệ nội dung hoặc số liệu phải chỉnh sửa trước khi báo cáo được phê duyệt.

Ví dụ:

- Sửa số liệu.
- Sửa diễn giải.
- Sửa định dạng.
- Sửa bố cục.

---

# Đầu ra của Evaluation

Sau mỗi lần đánh giá, hệ thống tạo Dashboard tổng hợp gồm:

- Data Accuracy
- Hallucination Rate
- Consistency Score
- Latency
- Human Edit Rate

Kết quả được sử dụng để:

- Cải thiện Data Pipeline.
- Cập nhật Knowledge Base (RAG).
- Điều chỉnh Prompt.
- Cập nhật Rule Engine.
- Theo dõi chất lượng hệ thống theo thời gian.

---

# Lưu ý

- Evaluation **không được sử dụng để Fine-tuning mô hình LLM**.
- Ground Truth là các báo cáo đã được phê duyệt chính thức.
- Việc đánh giá được thực hiện định kỳ để đảm bảo AI luôn đáp ứng yêu cầu về độ chính xác, tính nhất quán và đúng quy trình báo cáo của cơ quan nhà nước.