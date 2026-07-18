import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def calculate_metrics(predictions: Dict[str, Any], ground_truth: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Tính toán độ chính xác cho từng biến số liệu.
    Trả về:
        - accuracy (float): Tỷ lệ chính xác (0.0 -> 1.0)
        - details (list): Chi tiết kết quả so sánh từng trường dữ liệu.
    """
    correct_count = 0
    total_count = 0
    details = []
    
    # Duyệt qua các trường trong Ground Truth
    for key, gt_val in ground_truth.items():
        pred_val = predictions.get(key, None)
        total_count += 1
        is_correct = False
        
        if gt_val is None:
            is_correct = (pred_val is None)
        elif isinstance(gt_val, (int, float)):
            try:
                # Đối với số, cho phép sai số nhỏ do làm tròn
                is_correct = abs(float(pred_val) - float(gt_val)) < 1e-5
            except (ValueError, TypeError):
                is_correct = False
        else:
            # Đối với chuỗi, chuẩn hóa khoảng trắng và so khớp chính xác
            is_correct = str(pred_val).strip().lower() == str(gt_val).strip().lower()
            
        if is_correct:
            correct_count += 1
            
        details.append({
            "field": key,
            "ground_truth": gt_val,
            "prediction": pred_val,
            "status": "CORRECT" if is_correct else "INCORRECT"
        })
        
    accuracy = correct_count / total_count if total_count > 0 else 1.0
    return accuracy, details


def setup_mock_eval_data(gt_dir: Path, pred_dir: Path):
    """
    Tạo dữ liệu đối sánh giả lập để chạy demo kiểm thử ngay lập tức.
    """
    gt_dir.mkdir(parents=True, exist_ok=True)
    pred_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Báo cáo tuần 1
    gt_1 = {
        "tong_ho_so_tiep_nhan": 150,
        "ho_so_da_giai_quyet": 140,
        "ho_so_dung_han": 138,
        "tong_so_don_kntc": 12,
        "don_khieu_nai": 4,
        "don_to_cao": 2,
        "don_kien_nghi_phan_anh": 6
    }
    pred_1 = {
        "tong_ho_so_tiep_nhan": 150,
        "ho_so_da_giai_quyet": 140,
        "ho_so_dung_han": 138,
        "tong_so_don_kntc": 12,
        "don_khieu_nai": 4,
        "don_to_cao": 2,
        "don_kien_nghi_phan_anh": 6  # Khớp hoàn hảo
    }
    
    # 2. Báo cáo tuần 2 (Có sai lệch)
    gt_2 = {
        "tong_ho_so_tiep_nhan": 200,
        "ho_so_da_giai_quyet": 190,
        "ho_so_dung_han": 185,
        "tong_so_don_kntc": 8,
        "don_khieu_nai": 3,
        "don_to_cao": 5
    }
    pred_2 = {
        "tong_ho_so_tiep_nhan": 200,
        "ho_so_da_giai_quyet": 190,
        "ho_so_dung_han": 180,  # Sai lệch: GT là 185
        "tong_so_don_kntc": 8,
        "don_khieu_nai": 3,
        "don_to_cao": 4  # Sai lệch: GT là 5
    }
    
    with open(gt_dir / "report_01_gt.json", "w", encoding="utf-8") as f:
        json.dump(gt_1, f, ensure_ascii=False, indent=2)
    with open(pred_dir / "report_01_pred.json", "w", encoding="utf-8") as f:
        json.dump(pred_1, f, ensure_ascii=False, indent=2)
        
    with open(gt_dir / "report_02_gt.json", "w", encoding="utf-8") as f:
        json.dump(gt_2, f, ensure_ascii=False, indent=2)
    with open(pred_dir / "report_02_pred.json", "w", encoding="utf-8") as f:
        json.dump(pred_2, f, ensure_ascii=False, indent=2)


def main():
    print("==================================================")
    print("📊 BỘ ĐÁNH GIÁ ĐỘ CHÍNH XÁC SỐ LIỆU (EVALUATION)")
    print("==================================================")
    
    base_eval_dir = Path("e:/Project/VAIC_Project/data/evaluation")
    gt_dir = base_eval_dir / "ground_truth"
    pred_dir = base_eval_dir / "predictions"
    
    # Tự động sinh dữ liệu stubs nếu chưa có
    if not gt_dir.exists() or not list(gt_dir.glob("*.json")):
        print("[Info] Không tìm thấy dữ liệu đối sánh. Đang khởi tạo dữ liệu giả lập...")
        setup_mock_eval_data(gt_dir, pred_dir)
        
    gt_files = list(gt_dir.glob("*.json"))
    
    total_acc = 0.0
    report_count = 0
    
    print(f"\nTìm thấy {len(gt_files)} tệp tin đối sánh:")
    print("-" * 75)
    print(f"{'Tên Báo Cáo':<25} | {'Số Chỉ Tiêu':<15} | {'Đúng/Tổng':<12} | {'Độ Chính Xác':<15}")
    print("-" * 75)
    
    all_details = []
    
    for gt_file in gt_files:
        pred_file = pred_dir / gt_file.name.replace("_gt.json", "_pred.json")
        if not pred_file.exists():
            print(f"[Cảnh báo] Thiếu file kết quả dự đoán của AI: {pred_file.name}")
            continue
            
        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
        with open(pred_file, "r", encoding="utf-8") as f:
            pred_data = json.load(f)
            
        acc, details = calculate_metrics(pred_data, gt_data)
        total_acc += acc
        report_count += 1
        
        correct_fields = sum(1 for d in details if d["status"] == "CORRECT")
        total_fields = len(details)
        
        print(f"{gt_file.stem:<25} | {total_fields:<15} | {correct_fields}/{total_fields:<10} | {acc*100:>11.2f}%")
        all_details.append((gt_file.name, details))
        
    avg_acc = (total_acc / report_count) * 100 if report_count > 0 else 0.0
    print("-" * 75)
    print(f"{'ĐỘ CHÍNH XÁC TRUNG BÌNH TOÀN BỘ HỆ THỐNG':<56} | {avg_acc:>11.2f}%")
    print("==================================================")
    
    # In chi tiết các chỉ tiêu bị sai lệch
    has_incorrect = False
    for filename, details in all_details:
        incorrect_fields = [d for d in details if d["status"] == "INCORRECT"]
        if incorrect_fields:
            if not has_incorrect:
                print("\n❌ CHI TIẾT CÁC CHỈ TIÊU TRÍCH XUẤT SAI LỆCH:")
                print("-" * 80)
                print(f"{'Tên File':<20} | {'Trường Chỉ Tiêu':<25} | {'Ground Truth':<15} | {'AI Trích Xuất':<15}")
                print("-" * 80)
                has_incorrect = True
            for field in incorrect_fields:
                print(f"{filename:<20} | {field['field']:<25} | {str(field['ground_truth']):<15} | {str(field['prediction']):<15}")
                
    if has_incorrect:
        print("-" * 80)
    else:
        print("\n🎉 Tuyệt vời! Tất cả chỉ số trích xuất khớp hoàn toàn với Ground Truth.")


if __name__ == "__main__":
    from typing import Tuple
    main()
