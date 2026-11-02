import flet as ft

def main(page: ft.Page):
    page.title = "BaarnamaCommercial - نسخه تجاری باربرگ"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20

    license_user = ft.TextField(label="نام کاربری", width=280)
    license_pass = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True, width=280)
    login_error = ft.Text("", color=ft.Colors.RED)

    def verify_commercial_license(e):
        if license_user.value == "admin" and license_pass.value == "1234":
            login_error.value = ""
            page.clean()
            page.add(
                ft.AppBar(title=ft.Text("پنل مدیریت و اتوماسیون ناوگان (نسخه تجاری)"), bgcolor=ft.Colors.SURFACE_VARIANT),
                ft.Divider(),
                ft.Text("خوش آمدید! اتوماسیون باربرگ آماده به کار است.", weight=ft.FontWeight.BOLD),
            )
            page.update()
        else:
            login_error.value = "نام کاربری یا رمز عبور اشتباه است!"
            page.update()

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.SECURITY, size=60, color=ft.Colors.BLUE_400),
                ft.Text("ورود به نسخه تجاری باربرگ", size=22, weight=ft.FontWeight.BOLD),
                license_user,
                license_pass,
                login_error,
                ft.ElevatedButton("ورود به برنامه", width=280, on_click=verify_commercial_license),
                ft.Text("تست ورود: نام کاربری admin / رمز 1234", size=12, color=ft.Colors.GREY_500)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            expand=True
        )
    )

ft.app(target=main)
