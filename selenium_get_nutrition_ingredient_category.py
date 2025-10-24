import os
import csv
import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (TimeoutException, StaleElementReferenceException,
                                        ElementClickInterceptedException, NoSuchElementException)
from logging.handlers import RotatingFileHandler

# ==================== 配置常量 ====================
TARGET_URL = "https://nutridata.cn/database/list?id=1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
TOTAL_DATA_FILE = "food_categories.csv"
LOG_FILE = "category_crawl.log"
DELAY_RANGE = (0.5, 2.5)  # 统一随机延迟范围（秒）

# 表格字段与列索引映射
COLUMN_MAPPING = {
    "食部(%)": 2,     # 食部所在列索引
    "水分(%)": 3,     # 水分所在列索引
    "能量(kcal)": 4,      # 能量所在列索引
    "蛋白质(g)": 5,        # 蛋白质所在列索引
    "脂肪(g)": 6,     # 脂肪所在列索引
    "碳水化合物(g)": 7,      # 碳水化合物所在列索引
    "钠(mg)": 8,     # 钠所在列索引
    "名称": 9     # 名称所在列索引
}


# ==================== 日志配置 ====================
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 控制台+文件输出
    for handler in [logging.StreamHandler(),
                    RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logging()


# ==================== 工具函数 ====================
def random_delay():
    """随机延迟"""
    delay = random.uniform(*DELAY_RANGE)
    time.sleep(delay)


def init_csv():
    """初始化CSV"""
    if not os.path.exists(TOTAL_DATA_FILE):
        with open(TOTAL_DATA_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=["一级分类", "二级分类"] + list(COLUMN_MAPPING.keys())).writeheader()


def save_data(primary, secondary, data_list):
    """保存数据"""
    with open(TOTAL_DATA_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["一级分类", "二级分类"] + list(COLUMN_MAPPING.keys()))
        for data in data_list:
            writer.writerow({"一级分类": primary, "二级分类": secondary, **data})


# ==================== 浏览器配置 ====================
def init_driver():
    """初始化浏览器"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    })
    driver.set_page_load_timeout(30)
    return driver


# ==================== 核心爬取逻辑 ====================
def crawl_table_data(driver, primary_category, secondary_category):
    """爬取当前页面表格数据"""
    try:
        # 等待表格加载完成
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".el-table__body tr.el-table__row"))
        )

        data_list = []
        rows = driver.find_elements(By.CSS_SELECTOR, ".el-table__body tr.el-table__row")

        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td.el-table__cell")
            if len(cells) < len(COLUMN_MAPPING):
                continue
            if not cells[COLUMN_MAPPING["名称"]].text.strip():
                continue

            row_data = {}
            for field, index in COLUMN_MAPPING.items():
                try:
                    value = cells[index].text.strip().replace('\n', ' ')
                    row_data[field] = value
                except IndexError:
                    row_data[field] = ""

            data_list.append(row_data)

        logger.info(f"已爬取 {primary_category} -> {secondary_category} 数据 {len(data_list)} 条")
        return data_list

    except TimeoutException:
        logger.warning(f"{primary_category} -> {secondary_category} 表格加载超时")
        return []
    except Exception as e:
        logger.error(f"爬取表格数据出错: {str(e)}", exc_info=True)
        return []


def handle_pagination(driver, primary, secondary):
    """处理分页"""
    all_data = []
    current_page = 1

    while True:
        page_data = crawl_table_data(driver, primary, secondary)
        if not page_data:
            break
        all_data.extend(page_data)

        # 尝试点击下一页
        try:
            next_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-next:not([disabled])"))
            )
            next_btn.click()
            current_page += 1
            random_delay()
            # 验证页码切换
            WebDriverWait(driver, 10).until(
                EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".el-pager li.active"), str(current_page))
            )
        except (NoSuchElementException, TimeoutException):
            logger.info(f"[{primary}→{secondary}] 共{current_page}页，无更多数据")
            break
        except Exception as e:
            logger.error(f"[{primary}→{secondary}] 分页失败：{str(e)}")
            break

    if all_data:
        save_data(primary, secondary, all_data)
    return len(all_data)


def get_categories(driver, level):
    """获取分类（支持一级/二级）"""
    xpath = f"//div[contains(text(), '{level}分类：')]/following-sibling::div[@class='field-detail']"
    try:
        driver.execute_script("window.scrollTo(0, 300);")
        random_delay()
        container = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, xpath)))
        # 提取非"全部"的分类
        return [cat for cat in container.find_elements(By.CSS_SELECTOR, ".field-group-item")
                if cat.text.strip() and cat.text.strip() != "全部"]
    except Exception as e:
	    logger.warning(f"获取{level}分类失败：{str(e)}")
	    return []


def crawl_all(driver):
    """主爬取逻辑"""
    init_csv()

    # 获取一级分类
    primary_cats = get_categories(driver, "一级")
    if not primary_cats:
        logger.error("无一级分类，终止爬取")
        return

    # 遍历一级分类
    for i, primary_cat in enumerate(primary_cats, 1):
        try:
            primary_name = primary_cat.text.strip()
            logger.info(f"\n===== 处理一级分类 {i}/{len(primary_cats)}：{primary_name} =====")

            # 点击一级分类
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(primary_cat)).click()
            random_delay()

            # 获取二级分类（允许为空）
            secondary_cats = get_categories(driver, "二级")

            # 如果没有二级分类，创建一个虚拟的空二级分类处理
            if not secondary_cats:
                logger.info(f"[{primary_name}] 无二级分类，直接爬取数据")
                # 二级分类设为空字符串
                total = handle_pagination(driver, primary_name, "")
                logger.info(f"[{primary_name}→(无二级分类)] 完成，共{total}条")
                continue

            # 遍历二级分类
            for j, secondary_cat in enumerate(secondary_cats, 1):
                try:
                    secondary_name = secondary_cat.text.strip()
                    logger.info(f"[{primary_name}] 处理二级分类 {j}/{len(secondary_cats)}：{secondary_name}")

                    # 点击二级分类
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(secondary_cat)).click()
                    random_delay()

                    # 爬取当前分类数据
                    total = handle_pagination(driver, primary_name, secondary_name)
                    logger.info(f"[{primary_name}→{secondary_name}] 完成，共{total}条")

                except StaleElementReferenceException:
                    logger.warning(f"[{secondary_name}] 元素失效，跳过")
                except ElementClickInterceptedException:
                    logger.warning(f"[{secondary_name}] 点击被拦截，跳过")
                except Exception as e:
                    logger.error(f"[{secondary_name}] 处理失败：{str(e)}")

        except StaleElementReferenceException:
            logger.warning(f"[{primary_name}] 元素失效，跳过")
        except Exception as e:
            logger.error(f"[{primary_name}] 处理失败：{str(e)}")

    logger.info("\n===== 所有分类爬取完成 =====")


def main():
    driver = None
    try:
        logger.info("===== 启动爬取程序 =====")
        driver = init_driver()
        driver.get(TARGET_URL)
        # 等待页面加载
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "database-warp-container")))
        random_delay()
        # 开始爬取
        crawl_all(driver)
    except Exception as e:
        logger.error(f"主程序错误：{str(e)}")
    finally:
        if driver:
            driver.quit()
            logger.info("浏览器已关闭")
        logger.info("===== 程序结束 =====")


if __name__ == "__main__":
    main()