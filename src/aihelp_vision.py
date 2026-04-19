import os
import base64
from io import BytesIO
from pathlib import Path
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
import queue
import threading
import re
import time

import keyboard
import pyautogui
from openai import OpenAI

# ================= 配置区域 =================

# 替换为您的支持 Vision (视觉) 的 API Key
# 推荐使用:
# 1. OpenAI (gpt-4o-mini, gpt-4o) - 最稳
# 2. DashScope (qwen-vl-max) - 中文最强
# 3. Google Gemini (gemini-1.5-flash) - 免费且快
API_KEY = "sk-cfa012bef6554f65a635f21e2cbe9cd1"  # 请填写您的 API Key
AI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 请填写对应的 Base URL
AI_MODEL = "qwen-vl-plus"  # 请填写对应的模型名称

OBSIDIAN_DIR = Path(os.getenv("OBSIDIAN_DIR", r"D:\obsidian\obsidiandata\englishnote"))

HOTKEY_CAPTURE = "F8"
HOTKEY_SELECT_REGION = "F7"

# ===========================================

REGION = None
task_queue = queue.Queue()
processing_count = 0
max_concurrent_tasks = 2

if not API_KEY or API_KEY.startswith("sk-..."):
    raise RuntimeError("请在代码中配置真实的支持 Vision 的 API Key！")

client = OpenAI(
    api_key=API_KEY,
    base_url=AI_BASE_URL,
)

def encode_image(image):
    """将 PIL Image 转换为 Base64 字符串"""
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def select_region():
    """手动框选截图区域"""
    result = {"region": None}
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.25)
    root.configure(bg="black")
    
    canvas = tk.Canvas(root, cursor="cross", bg="gray", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x, start_y = 0, 0
    rect_id = None

    def on_press(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id: canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_drag(event):
        if rect_id: canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_release(event):
        x1, y1, x2, y2 = start_x, start_y, event.x, event.y
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        if width > 10 and height > 10:
            result["region"] = (left, top, width, height)
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()
    return result["region"]

def set_region_hotkey():
    global REGION
    print("[INFO] 请框选区域...")
    region = select_region()
    if region:
        REGION = region
        print(f"[OK] 区域已设置: {REGION}")
        add_task_to_queue()

def capture_hotkey():
    global REGION
    if not REGION:
        print("[INFO] 请先框选区域...")
        region = select_region()
        if not region: return
        REGION = region
    add_task_to_queue()

def add_task_to_queue():
    global processing_count
    if processing_count >= max_concurrent_tasks:
        print(f"[INFO] 任务队列已满，请稍候...")
        return
    
    # 立即截图（在主线程截图，避免 UI 变化）
    screenshot = pyautogui.screenshot(region=REGION)
    task_queue.put(screenshot)
    print(f"[INFO] 截图已添加，队列长度: {task_queue.qsize()}")
    
    if not hasattr(add_task_to_queue, 'worker_started'):
        threading.Thread(target=worker_loop, daemon=True).start()
        add_task_to_queue.worker_started = True

def worker_loop():
    global processing_count
    while True:
        try:
            image = task_queue.get(timeout=1)
            processing_count += 1
            print(f"[INFO] 开始处理图片...")
            try:
                process_image(image)
            except Exception as e:
                print(f"[ERROR] 处理失败: {e}")
            finally:
                processing_count -= 1
                task_queue.task_done()
        except queue.Empty:
            continue

def process_image(image):
    base64_image = encode_image(image)
    
    # 构造 Vision API 请求
    # 提示词要求输出 JSON 或特定 Markdown 格式
    prompt = """
    请识别这张图片中的英语题目。
    
    请输出 Markdown 格式解析，包含以下部分：
    1. # 重点单词
       (仅输出这道题最核心的一个单词)
    2. # 题目
       (识别出的完整题目文本)
    3. # 英语题目解析
       (尽量简洁)
    4.# 相关单词
    
    请严格按照上述标题输出，不要标注markdown
    """

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        content = response.choices[0].message.content
        save_note(content)
        
    except Exception as e:
        print(f"[ERROR] API 调用失败: {e}")

def save_note(content):
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    
    # 解析重点单词作为文件名
    keyword = "english_note"
    match = re.search(r"# 重点单词\s*\n+([^\n]+)", content)
    if match:
        keyword = match.group(1).strip().split()[0] # 取第一行第一个词
        keyword = re.sub(r'[^\w\s-]', '', keyword).strip()

    file_path = OBSIDIAN_DIR / f"{keyword}.md"
    
    # 处理重名
    counter = 1
    original_kw = keyword
    while file_path.exists():
        file_path = OBSIDIAN_DIR / f"{original_kw}_{counter}.md"
        counter += 1
        
    file_path.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] 笔记已保存: {file_path.name}")

def main():
    keyboard.add_hotkey(HOTKEY_SELECT_REGION, set_region_hotkey)
    keyboard.add_hotkey(HOTKEY_CAPTURE, capture_hotkey)
    print(f"Ready! 按 {HOTKEY_SELECT_REGION} 框选，按 {HOTKEY_CAPTURE} 识别。")
    keyboard.wait()

if __name__ == "__main__":
    main()