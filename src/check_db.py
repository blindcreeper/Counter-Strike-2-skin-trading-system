import sqlite3
conn = sqlite3.connect("market_trends.db")
cursor = conn.cursor()
try:
    cursor.execute("SELECT count(*) FROM market_history")
    count = cursor.fetchone()[0]
    print(f"📊 数据库检测结果：目前已存入 {count} 个饰品的记忆。")
except Exception as e:
    print(f"❌ 读取失败：{e}")
conn.close()
