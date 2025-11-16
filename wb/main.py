from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from bs4 import BeautifulSoup
import time
import json
import re
import random


def driver_options():
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    # Явно указываем Chrome и русскую локаль
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--lang=ru-RU')
    options.add_argument('--accept-lang=ru-RU,ru;q=0.9')

    # Дополнительные опции для обхода антибот
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2
        },
        "profile.managed_default_content_settings": {
            "images": 1
        },
        "intl.accept_languages": "ru-RU,ru"
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)

    # Устанавливаем геолокацию на Москву через CDP
    print("📍 Установка геолокации: Москва...")
    try:
        # Координаты Москвы: 55.7558° N, 37.6173° E
        driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
            "latitude": 55.7558,
            "longitude": 37.6173,
            "accuracy": 100
        })
        print("✅ Геолокация установлена: Москва (55.7558, 37.6173)")
    except Exception as e:
        print(f"⚠️ Не удалось установить геолокацию через CDP: {e}")

    # Устанавливаем часовой пояс для Москвы (Europe/Moscow, UTC+3)
    try:
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
            "timezoneId": "Europe/Moscow"
        })
        print("✅ Часовой пояс установлен: Europe/Moscow (UTC+3)")
    except Exception as e:
        print(f"⚠️ Не удалось установить часовой пояс: {e}")

    # Улучшенный обход детекции автоматизации
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
            Object.defineProperty(navigator, 'geolocation', {
                get: () => ({
                    getCurrentPosition: (success, error) => {
                        success({
                            coords: {
                                latitude: 55.7558,
                                longitude: 37.6173,
                                accuracy: 100
                            },
                            timestamp: Date.now()
                        });
                    }
                })
            });
            window.chrome = {runtime: {}};
        '''
    })

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    stealth(
        driver,
        languages=["ru-RU", "ru"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True
    )

    return driver


def driver_scroll(driver, deep_scroll=30):
    """Плавная прокрутка страницы с имитацией человеческого поведения"""
    try:
        for i in range(deep_scroll):
            try:
                scroll_amount = random.randint(300, 700)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
                time.sleep(random.uniform(0.1, 0.3))
            except Exception as e:
                print(f"⚠️ Ошибка при прокрутке (шаг {i}): {e}")
                break

        # Прокрутка вверх для имитации просмотра
        try:
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ Ошибка при прокрутке вверх: {e}")

        # Прокрутка к элементу с ценой
        try:
            driver.execute_script("""
                var priceElement = document.querySelector('.price-block__content, .price-block__final-price');
                if (priceElement) {
                    priceElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            """)
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Ошибка при прокрутке к цене: {e}")
    except Exception as e:
        print(f"⚠️ Критическая ошибка при прокрутке: {e}")


def extract_json_ld(soup):
    """Извлекает структурированные данные JSON-LD"""
    scripts = soup.find_all('script', {'type': 'application/ld+json'})
    for script in scripts:
        try:
            data = json.loads(script.string)
            if data.get('@type') == 'Product':
                return data
        except:
            continue
    return None


def wait_for_page_load(driver, timeout=15):
    """Ожидание полной загрузки страницы и JavaScript"""
    print("   Проверка загрузки DOM...")
    try:
        wait = WebDriverWait(driver, timeout)

        # Ждем загрузки DOM (с таймаутом)
        try:
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            print("   ✅ DOM загружен")
        except Exception as e:
            print(f"   ⚠️ DOM загрузка: {e}")
        time.sleep(1)

        # Ждем загрузки основных элементов Wildberries (с таймаутом)
        print("   Проверка наличия элементов...")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
                                                       '.product-page__title, h1, .price-block__content, .product-page__header, [class*="price"]')))
            print("   ✅ Основные элементы найдены")
        except Exception as e:
            print(f"   ⚠️ Элементы не найдены: {e}")
            # Продолжаем работу даже если элементы не найдены

        time.sleep(1)

        # Простая проверка наличия элементов на странице
        print("   Финальная проверка...")
        try:
            elements_found = driver.execute_script("""
                return document.querySelector('h1, .product-page__title, [class*="price"]') !== null;
            """)
            if elements_found:
                print("   ✅ Элементы на странице найдены")
            else:
                print("   ⚠️ Элементы не найдены, но продолжаем")
        except Exception as e:
            print(f"   ⚠️ Ошибка проверки: {e}")

    except Exception as e:
        print(f"   ⚠️ Предупреждение при ожидании загрузки: {e}")
        time.sleep(2)  # Даем время на загрузку даже при ошибке

    print("   ✅ Ожидание загрузки завершено")


def parse_product(driver, url):
    """Парсит страницу товара на Wildberries с учетом динамического контента"""
    print("🌐 Загрузка страницы...")

    # Устанавливаем cookies для региона Москвы перед загрузкой страницы
    try:
        # Сначала загружаем главную страницу для установки cookies
        print("🌐 Загрузка главной страницы для настройки региона...")
        driver.get("https://www.wildberries.ru/")
        time.sleep(3)

        # Устанавливаем регион Москвы через JavaScript (Wildberries использует это для определения региона)
        driver.execute_script("""
            // Устанавливаем регион в localStorage
            if (typeof(Storage) !== "undefined") {
                localStorage.setItem('location', 'Москва');
                localStorage.setItem('region', 'Москва');
                localStorage.setItem('city', 'Москва');
                localStorage.setItem('regionId', '1'); // ID Москвы
            }

            // Устанавливаем в sessionStorage
            if (typeof(sessionStorage) !== "undefined") {
                sessionStorage.setItem('location', 'Москва');
                sessionStorage.setItem('region', 'Москва');
            }
        """)

        # Устанавливаем cookies для региона Москвы
        # Wildberries использует различные cookie для определения региона
        cookies_to_set = [
            {"name": "location", "value": "Москва", "domain": ".wildberries.ru", "path": "/"},
            {"name": "region", "value": "Москва", "domain": ".wildberries.ru", "path": "/"},
            {"name": "city", "value": "Москва", "domain": ".wildberries.ru", "path": "/"},
            {"name": "regionId", "value": "1", "domain": ".wildberries.ru", "path": "/"},
            {"name": "wbx", "value": "1", "domain": ".wildberries.ru", "path": "/"},  # Cookie для региона
        ]

        for cookie in cookies_to_set:
            try:
                driver.add_cookie(cookie)
            except:
                pass

        print("✅ Cookies и localStorage для региона Москвы установлены")

        # Обновляем страницу для применения настроек
        driver.refresh()
        time.sleep(2)

    except Exception as e:
        print(f"⚠️ Не удалось установить cookies: {e}")

    # Теперь загружаем страницу товара
    print(f"🛒 Загрузка страницы товара: {url}")
    try:
        driver.get(url)
    except Exception as e:
        print(f"❌ Ошибка при загрузке страницы: {e}")
        raise

    # Имитация человеческого поведения - случайная задержка
    time.sleep(random.uniform(3, 6))

    # Проверяем, что сессия еще активна
    try:
        _ = driver.current_url
    except Exception as e:
        print(f"❌ Сессия браузера потеряна: {e}")
        raise

    # Ожидание полной загрузки страницы
    print("⏳ Ожидание загрузки динамического контента...")
    try:
        wait_for_page_load(driver, timeout=15)
    except Exception as e:
        print(f"⚠️ Предупреждение при ожидании загрузки: {e}")
        time.sleep(2)  # Даем дополнительное время

    # Проверяем сессию перед прокруткой
    try:
        _ = driver.current_url
    except Exception as e:
        print(f"❌ Сессия браузера потеряна перед прокруткой: {e}")
        raise

    # Прокручиваем страницу для загрузки всех элементов
    print("📜 Прокрутка страницы...")
    try:
        driver_scroll(driver, 30)  # Уменьшил количество прокруток
    except Exception as e:
        print(f"⚠️ Ошибка при прокрутке: {e}")
        # Продолжаем работу даже если прокрутка не удалась

    # Дополнительное ожидание после прокрутки
    time.sleep(2)  # Уменьшил время ожидания

    # Убеждаемся, что регион установлен правильно после загрузки страницы
    try:
        driver.execute_script("""
            // Проверяем и устанавливаем регион еще раз после загрузки страницы
            if (typeof(Storage) !== "undefined") {
                localStorage.setItem('location', 'Москва');
                localStorage.setItem('region', 'Москва');
                localStorage.setItem('city', 'Москва');
            }
        """)
    except:
        pass

    # Ждем еще немного для применения настроек региона
    time.sleep(2)

    # Пытаемся получить цену через JavaScript напрямую
    print("🔍 Извлечение данных через JavaScript...")
    js_price = None
    try:
        js_price = driver.execute_script("""
            var priceWidget = document.querySelector('.price-block__final-price, .price-block__content, [class*="price"]');
            if (priceWidget) {
                var priceText = priceWidget.innerText || priceWidget.textContent;
                return priceText;
            }
            return null;
        """)
        if js_price:
            print(f"   💰 Цена найдена через JS: {js_price}")
        else:
            print("   ⚠️ Цена не найдена через JS, будет использован BeautifulSoup")
    except Exception as e:
        print(f"   ⚠️ Не удалось получить цену через JS: {e}")

    # Обновляем страницу для получения актуального HTML
    print("📄 Парсинг HTML страницы...")
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        print("   ✅ HTML распарсен")
    except Exception as e:
        print(f"   ❌ Ошибка парсинга HTML: {e}")
        raise

    product_data = {
        'url': url,
        'title': None,
        'price': None,
        'old_price': None,
        'rating': None,
        'reviews_count': None,
        'questions_count': None,
        'images': [],
        'description': None,
        'full_description': None,
        'characteristics': {},
        'availability': None,
        'brand': None,
        'seller': None,
        'seller_name': None,
        'sku': None,
        'category': None,
        'discount_percent': None,
        'delivery_info': None,
        'warranty': None,
        'country': None,
        'product_id': None,
        'region': 'Москва'
    }

    # 1. Название товара
    title_selectors = [
        ('h1', {}),
        ('h1', {'class': lambda x: x and 'product-page__title' in str(x)}),
        ('.product-page__title', {}),
        ('span', {'class': lambda x: x and 'product-page__title' in str(x)}),
        ('.product-page__header', {})
    ]
    for selector, attrs in title_selectors:
        title = soup.find(selector, attrs)
        if title:
            product_data['title'] = title.get_text(strip=True)
            print(f"      ✅ Название найдено: {product_data['title'][:50]}...")
            break

    if not product_data['title']:
        print("      ⚠️ Название не найдено")

    # 2. Цена (актуальная) - улучшенный поиск с учетом динамической загрузки
    print("   2️⃣ Поиск цены...")
    # Сначала пытаемся получить цену через Selenium напрямую
    try:
        wait = WebDriverWait(driver, 10)
        # Ищем цену Wildberries
        price_selectors = [
            '.price-block__final-price',
            '.price-block__content',
            '.price-block__old-price',
            '[class*="price"][class*="final"]',
            '[class*="price-block"]'
        ]

        price_found = False
        for selector in price_selectors:
            try:
                price_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in price_elements:
                    price_text = elem.text
                    if price_text and ('₽' in price_text or any(c.isdigit() for c in price_text)):
                        price_match = re.search(r'([\d\s]+)',
                                                price_text.replace('\xa0', ' ').replace('₽', '').replace('\u2009', ' '))
                        if price_match:
                            potential_price = price_match.group(1).replace(' ', '').replace('\xa0', '').replace(
                                '\u2009', '')
                            # Проверяем, что это разумная цена (не слишком маленькая или большая)
                            if potential_price and len(potential_price) >= 3:
                                product_data['price'] = potential_price
                                print(f"✅ Цена найдена через Selenium: {product_data['price']} ₽")
                                price_found = True
                                break
                if price_found:
                    break
            except:
                continue

        if not price_found:
            # Пробуем найти любую цену
            price_elements = driver.find_elements(By.CSS_SELECTOR, '.price-block__final-price, .price-block__content')
            if price_elements:
                price_text = price_elements[0].text
                price_match = re.search(r'([\d\s]+)',
                                        price_text.replace('\xa0', ' ').replace('₽', '').replace('\u2009', ' '))
                if price_match:
                    product_data['price'] = price_match.group(1).replace(' ', '').replace('\xa0', '').replace('\u2009',
                                                                                                              '')
                    print(f"✅ Цена найдена через Selenium (fallback): {product_data['price']} ₽")
    except Exception as e:
        print(f"⚠️ Не удалось получить цену через Selenium: {e}")

    # Если не нашли через Selenium, используем JS результат
    if not product_data['price'] and js_price:
        price_match = re.search(r'([\d\s]{3,})', js_price.replace('\xa0', ' ').replace('₽', '').replace('\u2009', ' '))
        if price_match:
            potential_price = price_match.group(1).replace(' ', '').replace('\xa0', '').replace('\u2009', '')
            if potential_price and len(potential_price) >= 3:
                product_data['price'] = potential_price
                print(f"✅ Цена найдена через JS: {product_data['price']} ₽")

    # Если все еще не нашли, используем BeautifulSoup
    if not product_data['price']:
        price_selectors = [
            ('.price-block__final-price', {}),
            ('.price-block__content', {}),
            ('span', {'class': lambda x: x and 'price' in str(x).lower() and 'final' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'price-block' in str(x).lower()})
        ]
        for selector, attrs in price_selectors:
            price_elem = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'([\d\s]+)',
                                        price_text.replace('\xa0', ' ').replace('₽', '').replace('\u2009', ' '))
                if price_match:
                    product_data['price'] = price_match.group(1).replace(' ', '').replace('\xa0', '').replace('\u2009',
                                                                                                              '')
                    print(f"✅ Цена найдена через BeautifulSoup: {product_data['price']} ₽")
                    break

    # 3. Старая цена - пропущена для Wildberries (не ищем зачеркнутую цену)

    # 4. Рейтинг и отзывы - улучшенный поиск
    rating_selectors = [
        ('.product-page__rating', {}),
        ('.rating', {}),
        ('div', {'class': lambda x: x and 'rating' in str(x).lower()}),
        ('span', {'class': lambda x: x and 'rating' in str(x).lower()})
    ]
    for selector, attrs in rating_selectors:
        rating_elem = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            rating_match = re.search(r'(\d+[.,]?\d*)', rating_text)
            if rating_match:
                product_data['rating'] = rating_match.group(1).replace(',', '.')
                # Пытаемся найти количество отзывов в том же элементе
                reviews_match = re.search(r'(\d+[\s\d]*)\s*отзыв', rating_text, re.IGNORECASE)
                if reviews_match:
                    product_data['reviews_count'] = reviews_match.group(1).replace(' ', '').replace('\xa0', '')
                break

    # Поиск отзывов отдельно
    if not product_data['reviews_count']:
        reviews_selectors = [
            ('a', {'href': lambda x: x and 'reviews' in str(x).lower()}),
            ('.product-page__rating', {})
        ]
        for selector, attrs in reviews_selectors:
            reviews = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
            if reviews:
                reviews_text = reviews.get_text(strip=True)
                reviews_match = re.search(r'(\d+[\s\d]*)\s*отзыв', reviews_text, re.IGNORECASE)
                if reviews_match:
                    product_data['reviews_count'] = reviews_match.group(1).replace(' ', '').replace('\xa0', '')
                    break

        # Поиск по тексту отдельно
        if not product_data['reviews_count']:
            reviews_span = soup.find('span', string=lambda text: text and 'отзыв' in str(text).lower())
            if reviews_span:
                reviews_text = reviews_span.get_text(strip=True)
                reviews_match = re.search(r'(\d+[\s\d]*)\s*отзыв', reviews_text, re.IGNORECASE)
                if reviews_match:
                    product_data['reviews_count'] = reviews_match.group(1).replace(' ', '').replace('\xa0', '')

    # 5. Изображения товара - улучшенный поиск
    # Ищем все изображения с доменом wildberries.ru
    all_images = soup.find_all('img')
    seen_images = set()
    for img in all_images:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
        if src:
            # Нормализуем URL
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://www.wildberries.ru' + src
            # Ищем изображения товара
            if 'wildberries.ru' in src or 'wbstatic.net' in src or 'basket' in src.lower():
                # Убираем параметры размера для получения оригинального изображения
                clean_src = re.sub(r'/size\d+/', '/size1000/', src)
                clean_src = re.sub(r'_\d+x\d+', '_1000x1000', clean_src)
                if clean_src not in seen_images and 'logo' not in clean_src.lower() and 'icon' not in clean_src.lower():
                    seen_images.add(clean_src)
                    product_data['images'].append(clean_src)
                    if len(product_data['images']) >= 20:  # Ограничиваем до 20 изображений
                        break

    # 6. Описание товара - улучшенный поиск
    desc_selectors = [
        ('.product-page__description', {}),
        ('.product-page__text', {}),
        ('div', {'class': lambda x: x and 'description' in str(x).lower()}),
        ('div', {'id': 'description'})
    ]
    for selector, attrs in desc_selectors:
        desc = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
        if desc:
            full_desc = desc.get_text(separator='\n', strip=True)
            if full_desc and len(full_desc) > 50:
                product_data['description'] = full_desc[:500]
                product_data['full_description'] = full_desc
                break

    # 7. Характеристики - улучшенный поиск
    # Ищем в разных структурах
    chars_patterns = [
        ('.product-page__details', {}),
        ('.product-params', {}),
        ('table', {'class': lambda x: x and 'params' in str(x).lower()}),
        ('dl', {'class': lambda x: x and 'params' in str(x).lower()})
    ]

    for selector, attrs in chars_patterns:
        chars_section = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
        if chars_section:
            # Структура dl/dt/dd
            dts = chars_section.find_all('dt')
            dds = chars_section.find_all('dd')
            if dts and dds:
                for dt, dd in zip(dts, dds):
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    if key and value:
                        product_data['characteristics'][key] = value
            else:
                # Структура tr/td
                rows = chars_section.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            product_data['characteristics'][key] = value
            if product_data['characteristics']:
                break

    # 8. Наличие товара
    availability_patterns = [
        ('.product-page__availability', {}),
        ('div', {'class': lambda x: x and ('availability' in str(x).lower() or 'stock' in str(x).lower())})
    ]
    for selector, attrs in availability_patterns:
        availability_elem = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
        if availability_elem:
            product_data['availability'] = availability_elem.get_text(strip=True)
            break

    # Поиск наличия по тексту
    if not product_data['availability']:
        availability_div = soup.find('div', string=lambda text: text and (
                'в наличии' in str(text).lower() or
                'нет в наличии' in str(text).lower() or
                'доступен' in str(text).lower()
        ))
        if availability_div:
            product_data['availability'] = availability_div.get_text(strip=True)

    # 9. Бренд
    brand_patterns = [
        ('.product-page__brand', {}),
        ('a', {'href': lambda x: x and 'brand' in str(x).lower()}),
        ('span', {'class': lambda x: x and 'brand' in str(x).lower()}),
        ('div', {'class': lambda x: x and 'brand' in str(x).lower()})
    ]
    for selector, attrs in brand_patterns:
        brand_elem = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
        if brand_elem:
            brand_text = brand_elem.get_text(strip=True)
            if brand_text and len(brand_text) < 100:  # Бренд обычно короткий
                product_data['brand'] = brand_text
                break

    # 10. Продавец (Wildberries обычно продает сам)
    seller_patterns = [
        ('.product-page__seller', {}),
        ('div', {'class': lambda x: x and 'seller' in str(x).lower()}),
        ('span', {'class': lambda x: x and 'seller' in str(x).lower()})
    ]
    for selector, attrs in seller_patterns:
        seller_elem = soup.select_one(selector) if isinstance(selector, str) else soup.find(selector, attrs)
        if seller_elem:
            seller_text = seller_elem.get_text(strip=True)
            if seller_text:
                product_data['seller'] = seller_text
                product_data['seller_name'] = seller_text
                break

    # 11. Артикул/SKU
    # В Wildberries артикул обычно в URL или в специальном блоке
    sku_elem = soup.select_one('.product-page__article')
    if sku_elem:
        sku_text = sku_elem.get_text(strip=True)
        sku_match = re.search(r'артикул[:\s]+([^\s]+)', sku_text, re.IGNORECASE)
        if sku_match:
            product_data['sku'] = sku_match.group(1)

    if not product_data['sku']:
        sku_span = soup.find('span', string=lambda text: text and 'артикул' in str(text).lower())
        if sku_span:
            parent = sku_span.find_parent()
            if parent:
                sku_text = parent.get_text(strip=True)
                sku_match = re.search(r'артикул[:\s]+([^\s]+)', sku_text, re.IGNORECASE)
                if sku_match:
                    product_data['sku'] = sku_match.group(1)

    if not product_data['sku']:
        sku_div = soup.find('div', string=lambda text: text and 'артикул' in str(text).lower())
        if sku_div:
            parent = sku_div.find_parent()
            if parent:
                sku_text = parent.get_text(strip=True)
                sku_match = re.search(r'артикул[:\s]+([^\s]+)', sku_text, re.IGNORECASE)
                if sku_match:
                    product_data['sku'] = sku_match.group(1)

    # Если не нашли, пытаемся извлечь из URL
    if not product_data['sku']:
        url_match = re.search(r'/catalog/(\d+)/', url)
        if url_match:
            product_data['sku'] = url_match.group(1)

    # 12. Категория
    category_elem = soup.find('nav', {'class': lambda x: x and 'breadcrumb' in str(x).lower()})
    if category_elem:
        categories = []
        links = category_elem.find_all('a')
        for link in links:
            cat_text = link.get_text(strip=True)
            if cat_text and cat_text.lower() not in ['главная', 'home', 'wildberries']:
                categories.append(cat_text)
        if categories:
            product_data['category'] = ' > '.join(categories)

    # 13. Информация о доставке
    delivery_elem = soup.find('div', string=lambda text: text and (
                'доставка' in str(text).lower() or 'доставим' in str(text).lower()))
    if delivery_elem:
        parent = delivery_elem.find_parent()
        if parent:
            product_data['delivery_info'] = parent.get_text(strip=True)[:200]

    # 14. Гарантия
    warranty_elem = soup.find('div', string=lambda text: text and 'гарантия' in str(text).lower())
    if warranty_elem:
        parent = warranty_elem.find_parent()
        if parent:
            product_data['warranty'] = parent.get_text(strip=True)[:200]

    # 15. Страна производства
    country_elem = soup.find('div', string=lambda text: text and 'страна' in str(text).lower())
    if country_elem:
        parent = country_elem.find_parent()
        if parent:
            country_text = parent.get_text(strip=True)
            country_match = re.search(r'страна[:\s]+([^\n]+)', country_text, re.IGNORECASE)
            if country_match:
                product_data['country'] = country_match.group(1).strip()

    # 16. ID товара из URL
    id_match = re.search(r'/catalog/(\d+)/', url)
    if id_match:
        product_data['product_id'] = id_match.group(1)

    # 17. Попытка извлечь данные из JSON-LD
    json_ld_data = extract_json_ld(soup)
    if json_ld_data:
        if not product_data['title']:
            product_data['title'] = json_ld_data.get('name')
        if not product_data['price']:
            offers = json_ld_data.get('offers', {})
            if isinstance(offers, dict):
                product_data['price'] = offers.get('price')
        if not product_data['rating']:
            rating_obj = json_ld_data.get('aggregateRating', {})
            if isinstance(rating_obj, dict):
                product_data['rating'] = rating_obj.get('ratingValue')
        if not product_data['brand']:
            product_data['brand'] = json_ld_data.get('brand', {}).get('name') if isinstance(json_ld_data.get('brand'),
                                                                                            dict) else json_ld_data.get(
                'brand')
        if not product_data['description']:
            product_data['description'] = json_ld_data.get('description')
            product_data['full_description'] = json_ld_data.get('description')

    return product_data


def print_product_data(data):
    """Красиво выводит данные о товаре"""
    print("\n" + "=" * 60)
    print("ИНФОРМАЦИЯ О ТОВАРЕ (WILDBERRIES)")
    print("=" * 60)

    print(f"\n📦 Название: {data.get('title', 'Не указано')}")

    price_str = f"{data.get('price', 'Не указана')} ₽"
    if data.get('old_price'):
        price_str += f" (было {data['old_price']} ₽"
        if data.get('discount_percent'):
            price_str += f", скидка {data['discount_percent']}%"
        price_str += ")"
    print(f"💰 Цена: {price_str}")

    rating_str = data.get('rating', 'Не указан')
    if data.get('reviews_count'):
        rating_str += f" ({data['reviews_count']} отзывов)"
    if data.get('questions_count'):
        rating_str += f", {data['questions_count']} вопросов"
    print(f"⭐ Рейтинг: {rating_str}")

    print(f"📍 Наличие: {data.get('availability', 'Не указано')}")

    if data.get('brand'):
        print(f"🏷️  Бренд: {data['brand']}")

    if data.get('seller') or data.get('seller_name'):
        print(f"🏪 Продавец: {data.get('seller') or data.get('seller_name')}")

    if data.get('sku'):
        print(f"🔢 Артикул: {data['sku']}")

    if data.get('product_id'):
        print(f"🆔 ID товара: {data['product_id']}")

    if data.get('category'):
        print(f"📂 Категория: {data['category']}")

    if data.get('country'):
        print(f"🌍 Страна: {data['country']}")

    if data.get('images'):
        print(f"\n🖼️  Изображений: {len(data['images'])}")
        print(f"   Первое: {data['images'][0][:80]}...")

    if data.get('description'):
        print(f"\n📝 Описание: {data['description'][:200]}...")
        if data.get('full_description') and len(data['full_description']) > 200:
            print(f"   (Полное описание: {len(data['full_description'])} символов)")

    if data.get('characteristics'):
        print(f"\n📋 Характеристики ({len(data['characteristics'])} шт.):")
        for key, value in list(data['characteristics'].items())[:10]:
            print(f"   • {key}: {value}")
        if len(data['characteristics']) > 10:
            print(f"   ... и еще {len(data['characteristics']) - 10}")

    if data.get('delivery_info'):
        print(f"\n🚚 Доставка: {data['delivery_info'][:150]}...")

    if data.get('warranty'):
        print(f"\n🛡️  Гарантия: {data['warranty'][:150]}...")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    driver = driver_options()

    try:
        url = "https://www.wildberries.ru/catalog/403523144/detail.aspx"

        print("🔍 Парсинг страницы товара Wildberries...")
        product_data = parse_product(driver, url)

        # Выводим результат
        print_product_data(product_data)

        # Сохраняем в JSON
        with open('product_data.json', 'w', encoding='utf-8') as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2)
        print("✅ Данные сохранены в product_data.json")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        driver.quit()
        print("\n✅ Браузер закрыт")

