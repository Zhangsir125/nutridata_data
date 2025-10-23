from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (NoSuchElementException, TimeoutException,
                                        ElementClickInterceptedException)
import csv
import time
import random


# 工具函数：随机延迟（提取通用逻辑）
def random_delay(min_sec=0.2, max_sec=1):
    time.sleep(random.uniform(min_sec, max_sec))


# 1. 初始化浏览器驱动（精简配置项，保留核心反爬设置）
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # 无头模式
    chrome_options.add_argument("--disable-extensions")  # 禁用扩展
    chrome_options.add_argument("--disable-plugins")  # 禁用插件
    chrome_options.add_argument("--no-sandbox")  # 禁用沙盒（Linux环境必要，Windows可选）
    chrome_options.add_argument("--disable-gpu")  # 禁用GPU加速（无头模式无需）
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    # 性能优化：禁用不必要资源加载
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    # 拦截图片、CSS、JS（更彻底的资源禁用）
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # 禁用图片
        "profile.managed_default_content_settings.stylesheets": 2,  # 禁用CSS
        "javascript.enabled": False  # 禁用JS（若页面数据不依赖JS渲染则可用）
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # 反爬核心配置
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(options=chrome_options)
        # 清除webdriver标记
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver
    except Exception as e:
        print(f"浏览器初始化失败: {e}")
        return None


# 2. 提取单页菜品信息（简化逻辑，合并异常处理）
def extract_single_page(driver, page_num):
    try:
        # 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "tbody"))
        )
        random_delay()

        # 提取页面文本并处理
        lines = [line.strip() for line in driver.find_element(By.TAG_NAME, "body").text.split('\n')
                 if line.strip()]
        if not lines:
            print(f"第{page_num}页无有效内容")
            return []

        # 提取名称列表
        name_marker = "Name"
        if name_marker not in lines:
            print(f"第{page_num}页未找到Name标记")
            return []

        name_start = lines.index(name_marker) + 1
        name_end = lines.index("0: 估计0值，理论上为0值或不存在，或测定后为0")
        name_list = lines[name_start:name_end]

        # 提取数据列表
        try:
            data_start = lines.index("Major") + 1
            data_end = lines.index(name_marker)
            data_list = lines[data_start:data_end]
        except ValueError:
            print(f"第{page_num}页数据标记异常")
            return []

        # 数据匹配（取最小匹配量）
        match_count = min(len(name_list), len(data_list) // 3)
        if match_count == 0:
            print(f"⚠️  第{page_num}页无匹配数据")
            return []

        # 组装数据
        return [{
            "总序号": (page_num - 1) * 10 + i + 1,
            "页码": page_num,
            "名称": name_list[i],
            "能量": data_list[3 * i],
            "分类": data_list[3 * i + 1],
            "配料": data_list[3 * i + 2]
        } for i in range(match_count)]

    except Exception as e:
        print(f"第{page_num}页提取异常: {str(e)[:50]}")
        return []


# 3. 分页爬取核心逻辑（简化分页跳转，合并重复判断）
def crawl_all_pages(driver, start_page, max_page, batch_size=5):
    all_dishes = []  # 存储所有数据
    current_batch = []  # 存储当前批次数据
    batch_number = 1  # 批次编号
    current_page = start_page
    target_url = "https://nutridata.cn/database/list?id=2"

    try:
        driver.get(target_url)
        print(f"🚀 开始从第{start_page}页爬取，共{max_page}页，每批{batch_size}页")

        while current_page <= max_page:
            # 提取当前页数据
            page_data = extract_single_page(driver, current_page)
            if page_data:
                all_dishes.extend(page_data)
                current_batch.extend(page_data)
                print(f"✅ 第{current_page}页提取成功: {len(page_data)} 条菜品")

                # 当达到批次大小或最后一页时，保存批次数据
                if len(current_batch) >= batch_size * 10 or current_page == max_page:
                    # 保存当前批次到独立文件
                    batch_filename = f"批次{batch_number}.csv"
                    save_batch_data(current_batch, batch_filename)

                    # 同时附加到总文件
                    save_matched_data(current_batch, "菜品信息.csv", mode='a')

                    print(f"💾 批次{batch_number}保存完成，文件: {batch_filename}")
                    print(f"💾 已将批次{batch_number}附加到总文件，累计{len(all_dishes)}条")

                    # 重置当前批次并递增批次编号
                    current_batch = []
                    batch_number += 1

            # 跳转下一页
            if current_page < max_page:
                if not navigate_next_page(driver, current_page):
                    break  # 跳转失败则终止
            current_page += 1
            random_delay()

    except Exception as e:
        print(f"❌ 爬取中断: {e}")
    finally:
        # 处理可能剩余的未完成批次
        if current_batch:
            batch_filename = f"批次{batch_number}.csv"
            save_batch_data(current_batch, batch_filename)
            save_matched_data(current_batch, "总数据_所有菜品信息.csv", mode='a')
            print(f"💾 最后批次{batch_number}保存完成，文件: {batch_filename}")

        print(f"🎉 爬取完成！共提取{len(all_dishes)}条菜品信息")
        print(f"📁 总数据文件：总数据_所有菜品信息.csv")
        return all_dishes

# 辅助函数：保存批次数据（带表头）
def save_batch_data(batch_data, filename):
    if not batch_data:
        return

    headers = ["总序号", "页码", "名称", "能量", "分类", "配料"]
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(batch_data)

# 辅助函数：处理下一页跳转（分离关注点）
def navigate_next_page(driver, current_page):
    try:
        # 尝试点击下一页按钮
        next_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-next"))
        )

        if "disabled" in next_btn.get_attribute("class"):
            print(f"🔚 第{current_page}页已是最后一页")
            return False

        driver.execute_script("arguments[0].click();", next_btn)
        WebDriverWait(driver, 10).until(
            lambda d: str(current_page + 1) in d.page_source
        )
        return True

    except Exception as e:
        print(f"❌ 页码跳转失败: {e}")
        return False


# 4. 数据保存（精简参数处理）
def save_matched_data(dish_list, filename="总数据_所有菜品信息.csv", mode='a'):
    if not dish_list:
        return

    headers = ["总序号", "页码", "名称", "能量", "分类", "配料"]
    # 检查文件是否存在，不存在则写入表头
    file_exists = False
    try:
        with open(filename, 'r') as f:
            file_exists = True
    except FileNotFoundError:
        pass

    with open(filename, mode, encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if mode == 'w' or (mode == 'a' and not file_exists):
            writer.writeheader()
        writer.writerows(dish_list)


# 5. 主执行逻辑
if __name__ == '__main__':
    print("=" * 60)
    print("      菜品数据库全量爬取（2218页）      ")
    print("=" * 60)

    driver = init_driver()
    if not driver:
        print("❌ 程序退出")
        exit()

    try:
        all_dishes = crawl_all_pages(driver, start_page=1, max_page=2218, batch_size=100)
        print(f"\n📊 最终结果：共爬取{len(all_dishes)}条菜品信息")
        print(f"📁 数据文件：匹配后的菜品信息.csv")
    finally:
        driver.quit()
        print("\n🔚 浏览器已关闭")
        print("=" * 60)
