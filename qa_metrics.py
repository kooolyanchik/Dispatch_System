import requests
import time
import statistics

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/requests"


def measure_performance():
    print("Запуск аудита качества (QA Metrics)...")

    print("Получение токена авторизации (admin / admin123)...")
    login_data = {"username": "admin", "password": "admin123"}

    try:
        login_response = requests.post(f"{BASE_URL}/login", data=login_data)
        login_response.raise_for_status()
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Токен получен успешно.\n")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка авторизации: {e}")
        print("Убедитесь, что сервер запущен в другом окне терминала!")
        return

    response_times = []
    errors = 0
    total_requests = 10

    print(f"Замер времени отклика ({total_requests} запросов)...")

    for i in range(total_requests):
        start_time = time.time()
        try:
            response = requests.get(API_URL, headers=headers)
            response.raise_for_status()

            elapsed_ms = (time.time() - start_time) * 1000
            response_times.append(elapsed_ms)

        except requests.exceptions.RequestException:
            errors += 1

    if not response_times:
        print("")
        print("Отчет по качеству")
        print(f"Все {total_requests} запросов завершились с ошибкой.")
        print("Проверьте, запущен ли сервер (uvicorn) и доступен ли он по адресу 127.0.0.1:8000")
        return

    avg_time = statistics.mean(response_times)
    max_time = max(response_times)

    print("Отчет по качеству веб-интерфейса и API")
    print(f"Успешных запросов: {total_requests - errors}/{total_requests}")
    print(f"Ошибок: {errors}")
    print(f"Среднее время отклика: {avg_time:.2f} мс")
    print(f"Максимальное время отклика: {max_time:.2f} мс")

    if avg_time < 200 and errors == 0:
        print("Статус качества: ОТЛИЧНО (Соответствует SLA)")
    elif avg_time < 500:
        print("Статус качества: УДОВЛЕТВОРИТЕЛЬНО")
    else:
        print("Статус качества: ТРЕБУЕТСЯ ОПТИМИЗАЦИЯ")


if __name__ == "__main__":
    measure_performance()