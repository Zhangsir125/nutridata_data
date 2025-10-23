import os
import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_text(soup, selector, is_single=True):
    """提取选择器匹配的文本内容"""
    try:
        if is_single:
            elem = soup.select_one(selector)
            return elem.get_text(strip=True) if elem else "未获取到数据"
        else:
            elems = soup.select(selector)
            return [el.get_text(strip=True) for el in elems] if elems else []
    except Exception as e:
        print(f"解析 [{selector}] 失败：{e}")
        return "" if is_single else []


def download_image(image_url, save_dir, dish_id):
    """下载图片并以菜品ID命名"""
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{dish_id}.jpg" if str(dish_id).strip() else "none.jpg"
    save_path = os.path.join(save_dir, filename)

    try:
        with requests.Session() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            resp = session.get(image_url, headers=headers, timeout=15, stream=True)
            resp.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        return save_path
    except Exception as e:
        print(f"❌ 图片下载失败（ID:{dish_id}）：{e}")
        return ""


def save_to_json(data, filename):
    """保存数据到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📥 已保存到：{filename}")


def init_driver():
    """初始化Chrome浏览器配置（每个线程独立调用）"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # 无头模式
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # 禁用图片加载，提高速度
        "profile.managed_default_content_settings.plugins": 2,
        "profile.managed_default_content_settings.popups": 2,
        "profile.managed_default_content_settings.geolocation": 2,
        "profile.managed_default_content_settings.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.page_load_strategy = 'eager'  # 只等待DOM加载完成，不等待资源加载

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    driver.set_page_load_timeout(10)
    driver.set_script_timeout(10)

    return driver


def login_driver(driver, username, password):
    """为单个driver执行登录操作（每个线程独立登录）"""
    try:
        driver.get("https://nutridata.cn/login")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )

        # 密码登录流程
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.LINK_TEXT, "密码登录"))).click()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="请输入用户名或手机号"]'))).send_keys(
            username)
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="请输入密码"]'))).send_keys(password)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
            (By.XPATH, '//button[contains(@class, "primary-btn") and .//span[text()="登 录"]]'))).click()

        # 验证登录成功
        WebDriverWait(driver, 10).until(lambda d: "login" not in d.current_url.lower())
        print(f"✅ 线程登录成功")
        return True
    except Exception as e:
        print(f"❌ 线程登录失败：{e}")
        return False


def process_dish_batch(args):
    """处理一批菜品数据提取（每个线程登录一次处理500个ID）"""
    batch_id, dish_ids, username, password = args  # 接收参数：批次ID、菜品ID列表、账号、密码
    driver = None
    batch_results = []

    # 记录批次开始时间（仅用于控制台输出）
    start_time_ts = time.time()

    try:
        # 每个线程创建独立的driver并登录一次
        driver = init_driver()
        if not login_driver(driver, username, password):
            # 登录失败，为该批次所有ID记录错误
            for dish_id in dish_ids:
                batch_results.append({
                    "菜品ID": dish_id,
                    "错误信息": "登录失败",
                    "图片URL": "",
                    "本地保存路径": ""
                })
            return batch_results

        print(f"\n===== 开始处理批次 {batch_id}，共 {len(dish_ids)} 个菜品 =====")

        # 处理批次中的每个菜品ID
        for idx, dish_id in enumerate(dish_ids, 1):
            try:
                url = f"https://nutridata.cn/database/dishes/{dish_id}"
                print(f"[{batch_id}批次-{idx}/{len(dish_ids)}] 处理菜品 ID: {dish_id} | URL: {url}")

                try:
                    driver.get(url)
                except:
                    print(f"页面加载超时，尝试继续处理 ID: {dish_id}")

                # 等待关键元素
                try:
                    WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".info-title.ellipsis-1"))
                    )
                except:
                    print(f"核心元素加载超时，尝试继续处理 ID: {dish_id}")

                # 提取图片信息
                img_url = "未获取到图片URL"
                img_local_path = ""
                try:
                    img_elem = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "span.el-link--inner img"))
                    )
                    img_url = img_elem.get_attribute("src") or img_url
                    if img_url.startswith("http"):
                        img_local_path = download_image(img_url, "dish_images", dish_id)
                except:
                    pass

                # 展开单位下拉菜单
                try:
                    dropdown = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.unit-select .el-select__caret'))
                    )
                    dropdown.click()
                    WebDriverWait(driver, 2).until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, ".el-select-dropdown__list .el-select-dropdown__item"))
                    )
                except:
                    pass

                # 解析页面数据
                soup = BeautifulSoup(driver.page_source, "html.parser")
                ingredients = get_text(soup, ".ingredients span")
                steps = get_text(soup, ".practice-step", is_single=False)

                batch_results.append({
                    "菜品ID": dish_id,
                    "菜品名称": get_text(soup, ".info-title.ellipsis-1"),
                    "成分":"\n".join([i.replace("\n", " ").strip() for i in
                                      get_text(soup, ".info-tag .tag-item", False)]),
                    "计量单位": get_text(soup, ".title-tip"),
                    "图片URL": img_url,
                    "本地图片路径": img_local_path,
                    "菜肴做法": f"{ingredients}\n" + "\n".join(steps) if (ingredients or steps) else "未获取到做法",
                    "能量及宏量营养素": "\n".join([i.replace("\n", " ").strip() for i in
                                                   get_text(soup, ".chart-item.color-class-0 .item-chart-outer",
                                                            False)]),
                    "维生素": "\n".join([i.replace("\n", " ").strip() for i in
                                         get_text(soup, ".chart-item.color-class-1 .item-chart-outer", False)]),
                    "矿物质": "\n".join([i.replace("\n", " ").strip() for i in
                                         get_text(soup, ".chart-item.color-class-2 .item-chart-outer", False)]),
                    "单位量": "\n".join(
                        get_text(soup, ".el-select-dropdown__list .el-select-dropdown__item", False)) or "未获取到单位量"
                })

            except Exception as e:
                error = f"处理失败: {e}"
                print(f"❌ {error}")
                batch_results.append({
                    "菜品ID": dish_id,
                    "错误信息": error,
                    "图片URL": "",
                    "本地保存路径": ""
                })

        # 记录批次结束时间（仅用于控制台输出）
        end_time_ts =time.time()
        duration = round(end_time_ts - start_time_ts, 2)
        print(f"===== 批次 {batch_id} 完成 | 总耗时：{duration} 秒 =====")

        return batch_results

    except Exception as e:
        error = f"批次处理失败: {e}"
        print(f"❌ {error}")
        # 为该批次剩余未处理的ID记录错误
        for dish_id in dish_ids[len(batch_results):]:
            batch_results.append({
                "菜品ID": dish_id,
                "错误信息": error,
                "图片URL": "",
                "本地保存路径": ""
            })
        return batch_results
    finally:
        if driver:
            driver.quit()  # 批次处理完成后关闭driver


def crawl_dish_data(start_id, end_id, username, password, batch_size=100, max_workers=3):
    """批量爬取菜品数据（每次登录处理100条数据）"""
    all_data = []
    total = end_id - start_id + 1
    print(f"🚀 开始爬取 [{start_id}-{end_id}]，共 {total} 条数据，每批处理 {batch_size} 条，线程数：{max_workers}")

    # 生成所有菜品ID
    all_dish_ids = list(range(start_id, end_id + 1))

    # 分成多个批次
    batches = []
    for i in range(0, len(all_dish_ids), batch_size):
        batch_ids = all_dish_ids[i:i + batch_size]
        batches.append((len(batches) + 1, batch_ids))  # (批次号, 该批次的ID列表)

    print(f"📦 共分为 {len(batches)} 个批次")

    # 准备任务参数：每个任务包含（批次号, 该批次的ID列表, 用户名, 密码）
    task_args = [(batch_id, batch_ids, username, password) for batch_id, batch_ids in batches]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有批次任务
        futures = {executor.submit(process_dish_batch, args): args[0] for args in task_args}

        # 处理完成的任务
        for future in as_completed(futures):
            batch_id = futures[future]
            try:
                batch_data = future.result()
                all_data.extend(batch_data)

                # 实时保存进度
                success = len([d for d in all_data if '错误信息' not in d])
                processed = len(all_data)
                print(f"\n📊 总进度：{processed}/{total} | 成功：{success} | 失败：{processed - success}")
                save_to_json(all_data, "dishes_data_progress.json")
            except Exception as e:
                print(f"处理批次 {batch_id} 时发生异常: {e}")

                # 记录该批次所有ID的错误
                batch_ids = next(b[1] for b in batches if b[0] == batch_id)
                for dish_id in batch_ids:
                    all_data.append({
                        "菜品ID": dish_id,
                        "错误信息": f"批次处理异常: {e}"
                    })

    return all_data


if __name__ == "__main__":
    USERNAME = ""  # https://nutridata.cn/的账号
    PASSWORD = ""  # https://nutridata.cn/的密码
    START_ID = 8456  # 起始ID
    END_ID = 34123  # 结束ID
    BATCH_SIZE = 500  # 每批处理的数量
    MAX_WORKERS = 1  # 线程数（不宜过多，避免触发反爬）

    result = crawl_dish_data(START_ID, END_ID, USERNAME, PASSWORD, BATCH_SIZE, MAX_WORKERS)
    save_to_json(result, "dishes_data_complete.json")

    success_count = len([d for d in result if '错误信息' not in d])
    print(f"\n🎉 爬取完成！总数量：{len(result)} | 成功：{success_count} | 失败：{len(result) - success_count}")
