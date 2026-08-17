# TopHeroes Collector

ตัวดึงข้อมูลจากหน้า Facebook สาธารณะของ Top Heroes แบบ **ไม่ล็อกอินและไม่ใช้ Facebook API** เก็บ pinned post 1 รายการกับโพสต์ปกติล่าสุด 2 รายการเป็น JSON และมี static dashboard สำหรับ deploy บน GitHub Pages โปรแกรมจะคลิก **See more** ภายในโพสต์เพื่ออ่านข้อความเต็ม แต่จะบันทึกเฉพาะข้อความโพสต์ ไม่บันทึก Like, reaction, จำนวน Like, Comment, ผู้กด Like หรือข้อความคอมเมนต์ และจะไม่กด Like/ทำปฏิกิริยาใด ๆ

## ทดสอบบนเครื่อง

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python cli.py fetch --headed
python cli.py validate
python3 api_server.py --port 8000
```

เปิด `http://127.0.0.1:8000` เพื่อดู dashboard และเรียก API ได้ที่ `http://127.0.0.1:8000/api/posts.json` หรือ `http://127.0.0.1:8000/api/posts` ส่วน health check อยู่ที่ `http://127.0.0.1:8000/api/health` ทุก endpoint เป็น GET/OPTIONS แบบ read-only และเปิด CORS สำหรับโปรแกรมภายนอก

ตัวอย่างดึง JSON:

```bash
curl http://127.0.0.1:8000/api/posts.json
```

หรือจาก JavaScript:

```js
const response = await fetch('http://127.0.0.1:8000/api/posts.json');
const data = await response.json();
```

คำสั่ง `--headed` มีไว้ตรวจด้วยตาเท่านั้น โปรแกรมจะไม่ล็อกอินและไม่เก็บ session state การคลิกมีเฉพาะ See more ของโพสต์ และไม่มีคำสั่งกด Like หรือส่ง reaction

## การทำงานออนไลน์

GitHub Actions รัน workflow จาก `.github/workflows/collect.yml` วันละ 4 รอบที่เวลา 02:00, 08:00, 14:00 และ 20:00 UTC ซึ่งตรงกับ 09:00, 15:00, 21:00 และ 03:00 เวลาไทย และเปิด Facebook ใหม่ทุกครั้งเพื่อดึงข้อมูล public จากนั้น commit `data/posts.json` และ snapshot ที่เปลี่ยนกลับ repository หน้า GitHub Pages ใช้ไฟล์ static `site/data/posts.json` และ `site/api/posts.json`; โปรแกรมภายนอกสามารถเรียก `/api/posts.json` ได้โดยตรงโดยไม่ต้องเปิด Python server

เปิด GitHub Pages โดยเลือก source เป็น GitHub Actions เมื่อ workflow commit JSON ใหม่ workflow `pages.yml` จะ deploy โฟลเดอร์ `site/` ไปยัง GitHub Pages อัตโนมัติ หน้าเว็บไม่ได้ดึง Facebook โดยตรง

## ข้อจำกัด

Facebook อาจเปลี่ยน DOM, ไม่แสดง pinned marker, แสดง login wall, CAPTCHA หรือจำกัด automation ระบบจะไม่ bypass ข้อจำกัดและจะเก็บสถานะ partial/blocked/not_found พร้อม warning แทนการเดาข้อมูล หากรอบใดล้มเหลว workflow จะไม่เขียนข้อมูลว่างทับ JSON รอบก่อนหน้า

อย่าเพิ่มรหัสผ่าน cookie token หรือไฟล์ browser profile ลง repository หาก Facebook เปลี่ยน DOM จนขยาย See more ไม่ได้ ระบบจะบันทึกข้อความที่มองเห็นและสถานะ `partial` โดยไม่เดาข้อความส่วนที่หายไป
