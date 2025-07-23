# 使用一個包含 Python 3.10 的官方基礎映像
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 更新作業系統套件列表，並安裝 ffmpeg 和 libopus
# -y 選項會自動對所有提示回答 "yes"
RUN apt-get update && apt-get install -y ffmpeg libopus-dev

# 複製 requirements.txt 檔案到工作目錄
COPY requirements.txt .

# 安裝 requirements.txt 中定義的 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製你專案中的所有其他檔案 (例如 bot.py) 到工作目錄
COPY . .

# 當容器啟動時，執行的指令
CMD ["python", "bot.py"]