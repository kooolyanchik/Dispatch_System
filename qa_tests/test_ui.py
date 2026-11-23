import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://127.0.0.1:8000"


class TestDispatcherUI:
    def test_page_loads_successfully(self, browser):
        """Страница входа загружается"""
        browser.get(BASE_URL)
        assert "Dispatch System" in browser.title or "Вход" in browser.page_source

    def test_login_fields_present(self, browser):
        """Поля логина и пароля присутствуют"""
        browser.get(BASE_URL)
        username_field = browser.find_element(By.ID, "loginUsername")
        password_field = browser.find_element(By.ID, "loginPassword")
        assert username_field.is_displayed()
        assert password_field.is_displayed()

    def test_login_button_exists(self, browser):
        """Кнопка входа присутствует"""
        browser.get(BASE_URL)
        login_btn = browser.find_element(By.CLASS_NAME, "btn-submit")
        assert login_btn.is_displayed()
        assert "Войти" in login_btn.text

    def test_dashboard_loads_after_login(self, browser):
        """После входа открывается дашборд"""
        browser.get(BASE_URL)

        username_field = browser.find_element(By.ID, "loginUsername")
        password_field = browser.find_element(By.ID, "loginPassword")
        login_btn = browser.find_element(By.CLASS_NAME, "btn-submit")

        username_field.send_keys("admin")
        password_field.send_keys("admin123")
        login_btn.click()

        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tabs"))
        )

        assert "Заявки" in browser.page_source

    def test_tabs_present(self, browser):
        """Вкладки присутствуют на дашборде"""
        browser.get(BASE_URL)

        browser.find_element(By.ID, "loginUsername").send_keys("admin")
        browser.find_element(By.ID, "loginPassword").send_keys("admin123")
        browser.find_element(By.CLASS_NAME, "btn-submit").click()

        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tabs"))
        )

        tabs = browser.find_elements(By.CLASS_NAME, "tab")
        assert len(tabs) >= 2

    def test_admin_tab_visible_for_admin(self, browser):
        """Вкладка 'Пользователи' видна админу"""
        browser.get(BASE_URL)

        browser.find_element(By.ID, "loginUsername").send_keys("admin")
        browser.find_element(By.ID, "loginPassword").send_keys("admin123")
        browser.find_element(By.CLASS_NAME, "btn-submit").click()

        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.ID, "adminTab"))
        )

        admin_tab = browser.find_element(By.ID, "adminTab")
        assert admin_tab.is_displayed()

    def test_create_request_form_exists(self, browser):
        """Форма создания заявки присутствует"""
        browser.get(BASE_URL)

        browser.find_element(By.ID, "loginUsername").send_keys("admin")
        browser.find_element(By.ID, "loginPassword").send_keys("admin123")
        browser.find_element(By.CLASS_NAME, "btn-submit").click()

        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.ID, "reqTitle"))
        )

        title_field = browser.find_element(By.ID, "reqTitle")
        desc_field = browser.find_element(By.ID, "reqDesc")
        assert title_field.is_displayed()
        assert desc_field.is_displayed()

    def test_requests_table_exists(self, browser):
        """Таблица заявок присутствует"""
        browser.get(BASE_URL)

        browser.find_element(By.ID, "loginUsername").send_keys("admin")
        browser.find_element(By.ID, "loginPassword").send_keys("admin123")
        browser.find_element(By.CLASS_NAME, "btn-submit").click()

        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.ID, "tableBody"))
        )

        table = browser.find_element(By.ID, "tableBody")
        assert table.is_displayed()

    def test_logout_button_exists(self, browser):
        """Кнопка выхода присутствует"""
        browser.get(BASE_URL)

        browser.find_element(By.ID, "loginUsername").send_keys("admin")
        browser.find_element(By.ID, "loginPassword").send_keys("admin123")
        browser.find_element(By.CLASS_NAME, "btn-submit").click()

        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-logout"))
        )

        logout_btn = browser.find_element(By.CLASS_NAME, "btn-logout")
        assert logout_btn.is_displayed()
        assert "Выйти" in logout_btn.text

    def test_register_mode_switch(self, browser):
        """Переключение в режим регистрации"""
        browser.get(BASE_URL)

        # Нажимаем на вкладку "Регистрация"
        register_btn = browser.find_element(By.ID, "modeRegister")
        register_btn.click()

        # Проверяем, что форма регистрации видна
        reg_form = browser.find_element(By.ID, "registerForm")
        assert reg_form.is_displayed()

        # Проверяем наличие полей регистрации
        reg_username = browser.find_element(By.ID, "regUsername")
        reg_password = browser.find_element(By.ID, "regPassword")
        assert reg_username.is_displayed()
        assert reg_password.is_displayed()

    def test_consent_checkboxes_present(self, browser):
        """Тест UI-12: Чекбоксы согласия присутствуют в форме регистрации"""
        browser.get(BASE_URL)

        # Переключаемся в режим регистрации
        browser.find_element(By.ID, "modeRegister").click()

        consent_privacy = browser.find_element(By.ID, "consentPrivacy")
        consent_terms = browser.find_element(By.ID, "consentTerms")

        assert consent_privacy.is_displayed()
        assert consent_terms.is_displayed()
        assert not consent_privacy.is_selected()
        assert not consent_terms.is_selected()

    def test_consent_links_work(self, browser):
        """Ссылки на документы открываются"""
        browser.get(BASE_URL)
        browser.find_element(By.ID, "modeRegister").click()

        # Проверяем ссылку на Политику конфиденциальности
        privacy_link = browser.find_element(By.CSS_SELECTOR, 'a[href="/privacy"]')
        assert privacy_link.is_displayed()
        assert "Политикой конфиденциальности" in privacy_link.text

        # Проверяем ссылку на Пользовательское соглашение
        terms_link = browser.find_element(By.CSS_SELECTOR, 'a[href="/terms"]')
        assert terms_link.is_displayed()
        assert "Пользовательским соглашением" in terms_link.text

    def test_register_without_consent_fails(self, browser):
        """Регистрация без согласия невозможна"""
        browser.get(BASE_URL)
        browser.find_element(By.ID, "modeRegister").click()

        # Заполняем поля, но НЕ ставим галочки
        browser.find_element(By.ID, "regUsername").send_keys("testuser_noconsent")
        browser.find_element(By.ID, "regPassword").send_keys("testpass123")
        browser.find_element(By.ID, "regPasswordConfirm").send_keys("testpass123")

        # Нажимаем кнопку регистрации
        browser.find_element(By.ID, "registerBtn").click()

        # Ждём появления ошибки
        import time
        time.sleep(1.5)

        error_msg = browser.find_element(By.ID, "errorMsg")
        # Проверяем, что сообщение видимо И содержит текст про согласие
        assert error_msg.is_displayed(), "Сообщение об ошибке не отображается"
        error_text = error_msg.text.lower()
        assert "соглаш" in error_text or "соглас" in error_text, \
            f"Текст ошибки не содержит упоминания согласия: '{error_text}'"

    def test_privacy_page_loads(self, browser):
        """Страница Политики конфиденциальности загружается"""
        browser.get(f"{BASE_URL}/privacy")
        assert "Политика конфиденциальности" in browser.page_source

    def test_terms_page_loads(self, browser):
        """Страница Пользовательского соглашения загружается"""
        browser.get(f"{BASE_URL}/terms")
        assert "Пользовательское соглашение" in browser.page_source