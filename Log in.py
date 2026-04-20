import flet as ft

def login_page(page: ft.Page):
    page.bgcolor = "#FFFDE7"
    page.title = "Budget Bee - Login"

    email_field = ft.TextField(
        label="Email",
        hint_text="you@email.com",
        border_color="#B3E5FC",
        focused_border_color="#64B5F6",
        bgcolor="#F8FDFF",
        width=320,
    )

    password_field = ft.TextField(
        label="Password",
        hint_text="Enter your password",
        password=True,
        can_reveal_password=True,
        border_color="#B3E5FC",
        focused_border_color="#64B5F6",
        bgcolor="#F8FDFF",
        width=320,
    )

    error_text = ft.Text("", color="#E53935", size=12)

    def handle_login(e):
        if not email_field.value or not password_field.value:
            error_text.value = "Please fill in all fields."
        else:
            error_text.value = ""
            # TODO: connect to Ji Hong's auth logic here
        page.update()

    login_btn = ft.ElevatedButton(
        text="Log In",
        bgcolor="#64B5F6",
        color="white",
        width=320,
        on_click=handle_login,
    )

    register_link = ft.TextButton(
        text="Don't have an account? Register",
        on_click=lambda e: page.go("/register"),
    )

    page.add(
        ft.Column(
            [
                ft.Text("🐝 Budget Bee", size=28, weight=ft.FontWeight.BOLD, color="#F9A825"),
                ft.Text("Track smarter, save better", size=13, color="#78909C"),
                ft.Divider(height=20, color="transparent"),
                email_field,
                password_field,
                error_text,
                login_btn,
                register_link,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )
    )

def main(page: ft.Page):
    login_page(page)

ft.app(target=main, view=ft.AppView.WEB_BROWSER)