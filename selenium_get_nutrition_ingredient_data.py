import os
import json
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import RotatingFileHandler

# ==================== 配置常量 ====================
BASE_URL = "https://nutridata.cn"
LOGIN_URL = f"{BASE_URL}/login"
FOOD_DETAIL_URL = f"{BASE_URL}/database/ingredient/{{food_id}}?baseId=1"
IMAGE_SAVE_DIR = "food_images"
PROGRESS_JSON = "foods_data_progress.json"  # 修正笔误 foodes->foods
COMPLETE_JSON = "foods_data_complete.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


# ==================== 日志配置 ====================
def setup_logging():
    """配置日志系统，输出到控制台和文件"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（限制大小和备份）
    file_handler = RotatingFileHandler(
        'crawl.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# ==================== 工具函数 ====================
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
        logger.error(f"解析选择器 [{selector}] 失败：{e}")
        return "" if is_single else []


def download_image(image_url, save_dir, food_id, max_retries=2):
    """下载图片并以食物ID命名（支持重试）"""
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{food_id}.jpg" if str(food_id).strip() else "none.jpg"
    save_path = os.path.join(save_dir, filename)

    for retry in range(max_retries):
        try:
            with requests.Session() as session:
                headers = {"User-Agent": USER_AGENT}
                resp = session.get(
                    image_url,
                    headers=headers,
                    timeout=15,
                    stream=True
                )
                resp.raise_for_status()

                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info(f"图片下载成功（ID:{food_id}）：{save_path}")
            return save_path
        except Exception as e:
            logger.warning(f"图片下载失败（ID:{food_id}，重试 {retry + 1}/{max_retries}）：{e}")
            if retry < max_retries - 1:
                time.sleep(1)  # 重试间隔
    logger.error(f"图片下载最终失败（ID:{food_id}）")
    return ""


def save_to_json(data, filename):
    """保存数据到JSON文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已保存到：{filename}")
    except Exception as e:
        logger.error(f"保存JSON失败（{filename}）：{e}")


# ==================== 浏览器配置 ====================
def init_driver():
    """初始化Chrome浏览器配置（增强反检测）"""
    options = webdriver.ChromeOptions()
    # 基础配置
    options.add_argument("--headless=new")  # 无头模式
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-agent={USER_AGENT}")

    # 禁用不必要资源加载
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # 禁用图片（提高速度）
        "profile.managed_default_content_settings.plugins": 2,
        "profile.managed_default_content_settings.popups": 2,
        "profile.managed_default_content_settings.geolocation": 2,
        "profile.managed_default_content_settings.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.page_load_strategy = 'eager'  # 只等待DOM加载

    # 初始化driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    # 增强反爬：伪装浏览器特征
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        """
    })

    # 超时设置
    driver.set_page_load_timeout(10)
    driver.set_script_timeout(10)

    return driver


def login_driver(driver, username, password, max_retries=3):
    """执行登录操作（支持重试）"""
    for retry in range(max_retries):
        try:
            driver.get(LOGIN_URL)
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )

            # 密码登录流程
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "密码登录"))
            ).click()

            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="请输入用户名或手机号"]'))
            ).send_keys(username)

            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="请输入密码"]'))
            ).send_keys(password)

            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(@class, "primary-btn") and .//span[text()="登 录"]]'))
            ).click()

            # 验证登录成功
            WebDriverWait(driver, 10).until(
                lambda d: "login" not in d.current_url.lower()
            )
            logger.info(f"登录成功（重试次数：{retry}）")
            return True
        except Exception as e:
            logger.warning(f"登录失败（重试 {retry + 1}/{max_retries}）：{e}")
            if retry < max_retries - 1:
                time.sleep(2)  # 重试间隔
    logger.error("登录重试次数耗尽，登录失败")
    return False


# ==================== 数据处理 ====================
def process_single_food(driver, food_id):
    """处理单个食物ID的数据提取"""
    try:
        url = FOOD_DETAIL_URL.format(food_id=food_id)
        logger.info(f"处理食物 ID: {food_id} | URL: {url}")

        # 加载页面
        try:
            driver.get(url)
        except TimeoutException:
            logger.warning(f"页面加载超时（ID: {food_id}），继续处理")
        except Exception as e:
            logger.warning(f"页面加载错误（ID: {food_id}）：{e}")

        # 等待关键元素
        try:
            WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".info-title.ellipsis-1"))
            )
        except TimeoutException:
            logger.warning(f"核心元素加载超时（ID: {food_id}）")

        # 提取图片信息
        img_url = "未获取到图片URL"
        img_local_path = ""
        try:
            img_elem = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.el-link--inner img"))
            )
            img_url = img_elem.get_attribute("src") or img_url
            if img_url.startswith(("http://", "https://")):
                img_local_path = download_image(img_url, IMAGE_SAVE_DIR, food_id)
        except Exception as e:
            logger.warning(f"提取图片失败（ID: {food_id}）：{e}")

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
        except Exception as e:
            logger.warning(f"展开单位下拉菜单失败（ID: {food_id}）：{e}")

        # 解析页面数据
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 成分提取映射（减少重复代码）
        components = [
            ("能量及宏量营养素", ".chart-item.color-class-0 .item-chart-outer"),
            ("维生素", ".chart-item.color-class-1 .item-chart-outer"),
            ("矿物质", ".chart-item.color-class-2 .item-chart-outer")
        ]

        food_data = {
            "食物ID": food_id,
            "食物名称": get_text(soup, ".info-title.ellipsis-1"),
            "成分": "\n".join([i.replace("\n", " ").strip() for i in
                               get_text(soup, ".info-desc .desc-item", False)]),
            "计量单位": get_text(soup, ".title-tip"),
            "图片URL": img_url,
            "本地图片路径": img_local_path,
            "单位量": "\n".join(
                get_text(soup, ".el-select-dropdown__list .el-select-dropdown__item", False)) or "未获取到单位量"
        }

        # 批量提取成分数据
        for name, selector in components:
            food_data[name] = "\n".join([i.replace("\n", " ").strip() for i in get_text(soup, selector, False)])

        return food_data

    except Exception as e:
        error = f"处理失败: {str(e)}"
        logger.error(f"{error}（ID: {food_id}）")
        return {
            "食物ID": food_id,
            "食物名称": error,
            "成分": "",
            "计量单位": "",
            "图片URL": "",
            "本地保存路径": "",
            "单位量": ""
        }


def process_food_batch(args):
    """处理一批食物数据（每个线程独立处理）"""
    batch_id, food_ids, username, password = args
    driver = None
    batch_results = []
    start_time_ts = time.time()

    try:
        driver = init_driver()
        if not login_driver(driver, username, password):
            # 登录失败，标记批次内所有ID错误
            for food_id in food_ids:
                batch_results.append({
                    "食物ID": food_id,
                    "食物名称": "",
                    "成分": "",
                    "计量单位": "",
                    "图片URL": "",
                    "本地保存路径": "",
                    "单位量": ""
                })
            return batch_results

        logger.info(f"\n===== 开始处理批次 {batch_id}，共 {len(food_ids)} 个食物 =====")

        for idx, food_id in enumerate(food_ids, 1):
            logger.info(f"[{batch_id}批次-{idx}/{len(food_ids)}] 启动处理")
            food_data = process_single_food(driver, food_id)
            batch_results.append(food_data)
            # 随机延迟避免反爬（模拟人工操作）
            time.sleep(random.uniform(0.3, 1.5))

        # 批次完成统计
        end_time_ts = time.time()
        duration = round(end_time_ts - start_time_ts, 2)
        logger.info(f"===== 批次 {batch_id} 完成 | 耗时：{duration} 秒 =====")
        return batch_results

    except Exception as e:
        error = f"批次处理失败: {str(e)}"
        logger.error(f"{error}（批次 {batch_id}）")
        # 补充未处理的ID错误信息
        processed_count = len(batch_results)
        for food_id in food_ids[processed_count:]:
            batch_results.append({
                "食物ID": food_id,
                "食物名称": error,
                "成分": "",
                "计量单位": "",
                "图片URL": "",
                "本地保存路径": "",
                "单位量": ""
            })
        return batch_results
    finally:
        if driver:
            driver.quit()
            logger.info(f"批次 {batch_id} 的浏览器已关闭")


def crawl_food_data(start_id, end_id, username, password, batch_size=100, max_workers=3):
    """批量爬取食物数据主函数"""
    all_data = []
    total = end_id - start_id + 1
    logger.info(f"开始爬取 [{start_id}-{end_id}]，共 {total} 条数据，每批 {batch_size} 条，线程数：{max_workers}")

    # 生成所有食物ID并分批次
    all_food_ids = list(range(start_id, end_id + 1))
    batches = [(i + 1, all_food_ids[i:i + batch_size])
               for i in range(0, len(all_food_ids), batch_size)]
    logger.info(f"共分为 {len(batches)} 个批次")

    # 提交线程任务
    task_args = [(batch_id, batch_ids, username, password) for batch_id, batch_ids in batches]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_food_batch, args): args[0] for args in task_args}

        # 处理完成的任务
        for future in as_completed(futures):
            batch_id = futures[future]
            try:
                batch_data = future.result()
                all_data.extend(batch_data)

                # 实时保存进度
                success = len([d for d in all_data if '错误信息' not in d])
                processed = len(all_data)
                logger.info(f"\n总进度：{processed}/{total} | 成功：{success} | 失败：{processed - success}")
                save_to_json(all_data, PROGRESS_JSON)
            except Exception as e:
                logger.error(f"处理批次 {batch_id} 时发生异常: {e}")
                # 标记该批次所有ID为异常
                batch_ids = next(b[1] for b in batches if b[0] == batch_id)
                for food_id in batch_ids:
                    all_data.append({"食物ID": food_id, "错误信息": f"批次异常: {e}"})

    return all_data


if __name__ == "__main__":
    # 配置参数（请根据实际情况修改）
    USERNAME = ""  # 账号
    PASSWORD = ""  # 密码
    START_ID = 1  # 起始ID
    END_ID = 5004  # 结束ID（包含）
    # 5004
    BATCH_SIZE = 500  # 每批次数量（建议根据反爬严格程度调整）
    MAX_WORKERS = 1  # 线程数（建议1-3，避免触发反爬）

    logger.info("===== 启动食物数据爬取任务 =====")
    result = crawl_food_data(START_ID, END_ID, USERNAME, PASSWORD, BATCH_SIZE, MAX_WORKERS)
    save_to_json(result, COMPLETE_JSON)

    # 统计结果
    success_count = len([d for d in result if '错误信息' not in d])
    logger.info(f"\n===== 爬取完成 =====")
    logger.info(f"总数量：{len(result)} | 成功：{success_count} | 失败：{len(result) - success_count}")
