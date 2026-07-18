import shutil
import subprocess
import sys
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent
    frontend_dir = root_dir / "frontend"
    static_dir = root_dir / "src" / "static"

    print("====================================================")
    print(" BẮT ĐẦU DỰNG GIAO DIỆN REACT FRONTEND (PRODUCTION) ")
    print("====================================================")

    # 1. Kiểm tra thư mục frontend
    if not frontend_dir.exists():
        print(f"Lỗi: Không tìm thấy thư mục frontend tại {frontend_dir}")
        sys.exit(1)

    # 2. Chạy npm install và npm run build
    try:
        print("\n[1/3] Đang tải các thư viện node packages (npm install)...")
        subprocess.run("npm install", shell=True, cwd=str(frontend_dir), check=True)
        
        print("\n[2/3] Đang đóng gói ứng dụng React (npm run build)...")
        subprocess.run("npm run build", shell=True, cwd=str(frontend_dir), check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi trong quá trình build React: {e}")
        sys.exit(1)

    # 3. Sao chép kết quả build vào src/static
    dist_dir = frontend_dir / "dist"
    if not dist_dir.exists():
        print(f"\n❌ Lỗi: Không tìm thấy thư mục đầu ra biên dịch 'dist' tại {dist_dir}")
        sys.exit(1)

    try:
        print("\n[3/3] Đang đồng bộ tài nguyên tĩnh vào FastAPI backend...")
        if static_dir.exists():
            shutil.rmtree(static_dir)
        shutil.copytree(dist_dir, static_dir)
        print("\n✅ HOÀN THÀNH: React Frontend đã được đưa vào FastAPI!")
        print("Bây giờ bạn chỉ cần khởi chạy uvicorn và mở http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Lỗi khi đồng bộ file tĩnh: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
