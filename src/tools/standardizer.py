import csv
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from config import settings


def normalize_vietnamese(s: str) -> str:
    """
    Chuẩn hóa chuỗi tiếng Việt: chuyển chữ thường, loại bỏ dấu tiếng Việt, loại bỏ tiền tố thừa.
    """
    s = s.lower().strip()
    # Loại bỏ dấu tiếng Việt (diacritics)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = s.replace('đ', 'd')
    # Loại bỏ tiền tố hành chính để so khớp tên riêng tốt hơn
    prefixes = [
        "phuong ", "xa ", "thi tran ", "quan ", "huyen ", "thanh pho ", "tinh ",
        "p. ", "p ", "phong ", "ban ", "pb ", "bp "
    ]
    changed = True
    while changed:
        changed = False
        for p in prefixes:
            if s.startswith(p):
                s = s[len(p):]
                changed = True
    return s.strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Tính khoảng cách Levenshtein giữa hai chuỗi.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def get_similarity_score(s1: str, s2: str) -> float:
    """
    Tính điểm tương đồng kết hợp giữa Jaccard Word Overlap và Edit Distance.
    """
    norm1 = normalize_vietnamese(s1)
    norm2 = normalize_vietnamese(s2)
    
    if not norm1 or not norm2:
        return 0.0
        
    # 1. Word Jaccard Similarity
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    jaccard = len(words1.intersection(words2)) / len(words1.union(words2)) if words1 or words2 else 0.0
    
    # 2. Levenshtein Similarity
    dist = levenshtein_distance(norm1, norm2)
    max_len = max(len(norm1), len(norm2))
    lev_sim = 1.0 - (dist / max_len) if max_len > 0 else 1.0
    
    # Kết hợp 60% Jaccard (khớp từ tốt hơn viết tắt) và 40% Levenshtein (khớp sai chính tả tốt hơn)
    return 0.6 * jaccard + 0.4 * lev_sim


class Standardizer:
    def __init__(self):
        self.wards: List[Dict[str, str]] = []
        self.departments: List[Dict[str, str]] = []
        self.load_directories()

    def load_directories(self):
        """
        Đọc các tệp tin CSV danh mục chuẩn từ settings.
        """
        # 1. Đọc wards.csv
        wards_path = Path(settings.WARDS_CSV_PATH)
        if wards_path.exists():
            with open(wards_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.wards = [row for row in reader]

        # 2. Đọc phong_ban.csv
        dept_path = Path(settings.DEPARTMENTS_CSV_PATH)
        if dept_path.exists():
            with open(dept_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.departments = [row for row in reader]

    def match_ward(self, raw_ward_name: str, threshold: float = 0.5) -> Tuple[Optional[str], float]:
        """
        So khớp fuzzy tìm phường/xã chuẩn trong wards.csv.
        Trả về: (MaPhuongXa, score) hoặc (None, 0.0)
        """
        if not self.wards:
            return None, 0.0

        best_match = None
        best_score = 0.0

        for ward in self.wards:
            # So khớp với trường 'TenPhuongXa'
            score = get_similarity_score(raw_ward_name, ward["TenPhuongXa"])
            if score > best_score:
                best_score = score
                best_match = ward["MaPhuongXa"]

        if best_score >= threshold:
            return best_match, best_score
        return None, best_score

    def match_department(self, raw_dept_name: str, threshold: float = 0.5) -> Tuple[Optional[str], float]:
        """
        So khớp fuzzy tìm phòng ban chuẩn trong phong_ban.csv.
        Trả về: (department_id, score) hoặc (None, 0.0)
        """
        if not self.departments:
            return None, 0.0

        best_match = None
        best_score = 0.0

        for dept in self.departments:
            score = get_similarity_score(raw_dept_name, dept["department_name"])
            if score > best_score:
                best_score = score
                best_match = dept["department_id"]

        if best_score >= threshold:
            return best_match, best_score
        return None, best_score
