import asyncio
import sqlite3
import httpx
import flet as ft
from datetime import datetime

# ==========================================
# ۱. لایه دیتابیس محلی (مدیریت ۱۰۰+ اکانت)
# ==========================================
class FleetDB:
    def __init__(self, db_name="fleet_commercial.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_name TEXT,
                username TEXT UNIQUE,
                password TEXT,
                plate TEXT,
                session_token TEXT,
                last_status TEXT DEFAULT 'آماده'
            )
        """)
        self.conn.commit()

    def add_account(self, driver_name, username, password, plate):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO accounts (driver_name, username, password, plate) VALUES (?, ?, ?, ?)",
                (driver_name, username, password, plate)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_accounts(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, driver_name, username, password, plate, session_token, last_status FROM accounts")
        return cursor.fetchall()

    def update_status(self, acc_id, status, token=None):
        cursor = self.conn.cursor()
        if token:
            cursor.execute("UPDATE accounts SET last_status = ?, session_token = ? WHERE id = ?", (status, token, acc_id))
        else:
            cursor.execute("UPDATE accounts SET last_status = ? WHERE id = ?", (status, acc_id))
        self.conn.commit()


# ==========================================
# ۲. موتور اتوماسیون و شبکه (سرور موبایل / اصلی)
# ==========================================
class AutomationEngine:
    def __init__(self, use_mobile_endpoint=True, proxy_url=None):
        # آدرس پایه سرور موبایل سامانه
        self.base_url = "https://mobile-api.utcms.ir/api/v1" if use_mobile_endpoint else "https://barname.utcms.ir"
        self.proxy = proxy_url
        # محدودکننده سرعت همزمان برای جلوگیری از فشار روی سرور و مسدود شدن IP
        self.semaphore = asyncio.Semaphore(5)

    def get_headers(self, is_mobile=True, token=None):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.9.2" if is_mobile else "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def process_single_account(self, account, db: FleetDB, update_ui_callback):
        acc_id, name, user, pwd, plate, token, _ = account
        
        async with self.semaphore:
            await update_ui_callback(acc_id, "در حال اتصال...")
            
            async with httpx.AsyncClient(proxies=self.proxy, verify=False, timeout=20.0) as client:
                try:
                    # بررسی و دریافت توکن در صورت عدم وجود
                    if not token:
                        await update_ui_callback(acc_id, "در حال لاگین...")
                        # در این بخش درخواست پست به API لاگین سامانه انجام می‌شود
                        await asyncio.sleep(1.5)  
                        token = f"sample_jwt_token_{acc_id}"
                    
                    # ارسال درخواست صدور باربرگ
                    await update_ui_callback(acc_id, "در حال صدور باربرگ...")
                    await asyncio.sleep(2.0)  
                    
                    now_str = datetime.now().strftime("%H:%M:%S")
                    final_status = f"صادر شد ({now_str})"
                    db.update_status(acc_id, final_status, token)
                    await update_ui_callback(acc_id, final_status)

                except Exception as e:
                    err_msg = f"خطا: {str(e)[:20]}"
                    db.update_status(acc_id, err_msg)
                    await update_ui_callback(acc_id, err_msg)


# ==========================================
# ۳. رابط کاربری تجاری (Flet UI)
# ==========================================
async def main(page: ft.Page):
    page.title = "سامانه تجاری مدیریت هوشمند باربرگ"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 950
    page.window_height = 700

    db = FleetDB()
    status_Controls = {}

    # صفحه احراز هویت (لایسنس تجاری مشتری)
    license_user = ft.TextField(label="نام کاربری اشتراک", width=280)
    license_pass = ft.TextField(label="رمز عبور اشتراک", password=True, can_reveal_password=True, width=280)
    login_error = ft.Text("", color=ft.colors.RED_400)

    def verify_commercial_license(e):
        if license_user.value == "admin" and license_pass.value == "1234":
            page.clean()
            build_main_dashboard()
        else:
            login_error.value = "نام کاربری یا رمز عبور اشتراک معتبر نیست!"
            page.update()

    def build_main_dashboard():
        use_mobile_server = ft.Switch(label="استفاده از سرور موبایل سامانه", value=True)
        proxy_input = ft.TextField(label="پروکسی / چرخش IP (اختیاری)", hint_text="http://ip:port", width=300, height=45)
        
        f_name = ft.TextField(label="نام راننده", width=150)
        f_user = ft.TextField(label="نام کاربری سامانه", width=150)
        f_pass = ft.TextField(label="رمز عبور", width=150)
        f_plate = ft.TextField(label="پلاک خودرو", width=150)

        accounts_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ردیف")),
                ft.DataColumn(ft.Text("نام راننده")),
                ft.DataColumn(ft.Text("نام کاربری")),
                ft.DataColumn(ft.Text("پلاک")),
                ft.DataColumn(ft.Text("وضعیت لحظه‌ای")),
            ],
            rows=[]
        )

        def refresh_table():
            accounts_table.rows.clear()
            status_Controls.clear()
            for acc in db.get_all_accounts():
                acc_id, name, user, _, plate, _, status = acc
                status_text = ft.Text(status, color=ft.colors.AMBER if "حال" in status else ft.colors.GREEN_400)
                status_Controls[acc_id] = status_text
                accounts_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(acc_id))),
                        ft.DataCell(ft.Text(name)),
                        ft.DataCell(ft.Text(user)),
                        ft.DataCell(ft.Text(plate)),
                        ft.DataCell(status_text),
                    ])
                )
            page.update()

        def add_new_driver(e):
            if f_user.value and f_pass.value:
                db.add_account(f_name.value, f_user.value, f_pass.value, f_plate.value)
                f_name.value = f_user.value = f_pass.value = f_plate.value = ""
                refresh_table()

        async def update_row_status(acc_id, new_status):
            if acc_id in status_Controls:
                status_Controls[acc_id].value = new_status
                if "صادر شد" in new_status:
                    status_Controls[acc_id].color = ft.colors.GREEN_400
                elif "خطا" in new_status:
                    status_Controls[acc_id].color = ft.colors.RED_400
                else:
                    status_Controls[acc_id].color = ft.colors.CYAN_300
                page.update()

        async def start_batch_automation(e):
            accounts = db.get_all_accounts()
            if not accounts:
                return
            engine = AutomationEngine(
                use_mobile_endpoint=use_mobile_server.value,
                proxy_url=proxy_input.value if proxy_input.value else None
            )
            tasks = [engine.process_single_account(acc, db, update_row_status) for acc in accounts]
            await asyncio.gather(*tasks)

        refresh_table()

        page.add(
            ft.AppBar(title=ft.Text("پنل مدیریت و اتوماسیون ناوگان (نسخه تجاری)"), bgcolor=ft.colors.SURFACE_VARIANT),
            ft.Row([use_mobile_server, proxy_input], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Text("افزودن حساب جدید به لیست اتوماسیون:", weight=ft.FontWeight.BOLD),
            ft.Row([f_name, f_user, f_pass, f_plate, ft.ElevatedButton("افزودن حساب", icon=ft.icons.ADD, on_click=add_new_driver)]),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton(
                    "شروع صدور خودکار گروهی (همه حساب‌ها)", 
                    icon=ft.icons.PLAY_ARROW, 
                    bgcolor=ft.colors.GREEN_700, 
                    color=ft.colors.WHITE,
                    on_click=start_batch_automation
                ),
            ]),
            ft.Container(content=ft.Column([accounts_table], scroll=ft.ScrollMode.AUTO), expand=True)
        )

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.SECURITY, size=60, color=ft.colors.BLUE_400),
                ft.Text("ورود به نسخه تجاری باربرگ", size=22, weight=ft.FontWeight.BOLD),
                license_user,
                license_pass,
                login_error,

              ft.ElevatedButton("ورود به برنامه", width=280, on_click=verify_commercial_license),
                ft.Text("تست ورود: نام کاربری admin / رمز 1234", size=12, color=ft.colors.GREY_500)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            expand=True
        )
    )

ft.app(target=main)
