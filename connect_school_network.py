import logging

from httpcore import TimeoutException
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import configparser
import os
import warnings
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
# ---------------------- 配置初始化 ----------------------
# 配置日志记录
logging.basicConfig(
    filename='network_connect.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini',encoding="UTF-8")


# ---------------------- 核心功能类 ----------------------
class CampusNetworkConnector:
    def __init__(self):
        self.driver = None
        self.wait_timeout = 30
        self.setup_driver()

    def setup_driver(self):
        """初始化浏览器驱动"""
        try:
            chrome_service = Service(
                config.get('CHROME', 'DRIVER_PATH',
                           fallback=r"C:\chromedriver\chromedriver.exe")
            )

            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-infobars')
            options.add_argument('--headless')
            #忽略SSL错误并重定向错误信息到NUL
            options.add_argument('--ignore-ssl-errors=yes')



            if config.getboolean('CHROME', 'HEADLESS', fallback=False):
                options.add_argument('--headless-new')

            self.driver = webdriver.Chrome(
                service=chrome_service,
                options=options
            )
            # self.driver.maximize_window()
            logging.info("浏览器初始化成功")

        except Exception as e:
            logging.critical("浏览器初始化失败", exc_info=True)
            raise

    def safe_click(self, locator):
        """带重试机制的点击操作"""
        element = WebDriverWait(self.driver, self.wait_timeout).until(
            EC.element_to_be_clickable(locator)
        )
        element.click()
        time.sleep(1)  # 防止快速操作导致的点击失效

    def safe_input(self, locator, text):
        """带等待的文本输入"""
        element = WebDriverWait(self.driver, self.wait_timeout).until(
            EC.visibility_of_element_located(locator)
        )
        element.clear()
        element.send_keys(text)

    def connect_network(self):
        """执行完整的连接流程"""
        try:
            # 打开登录页面
            url = config.get('NETWORK', 'LOGIN_URL',
                             fallback="http://172.168.100.21")
            self.driver.get(url)
            logging.info(f"已访问校园网登录页面: {url}")

            # 等待页面完全加载
            WebDriverWait(self.driver, self.wait_timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )

            # 登录流程
            self._perform_login()
            self._select_provider()
            self._submit_login()

            # 结果验证
            if "success" in self.driver.page_source.lower():
                logging.info("网络连接成功")
            else:
                logging.warning("连接状态未知，请手动确认")

        except Exception as e:
            logging.error("网络连接流程异常终止", exc_info=True)
            raise
        finally:
            self.driver.quit()

    def _perform_login(self):
        """处理账号密码输入"""
        # 输入账号
        self.safe_input(
            (By.CSS_SELECTOR, '#username'),
            config.get('ACCOUNT', 'USERNAME')
        )

        # 密码输入优化方案
        password_script = """
            // 获取密码输入框元素
            var pwdField = document.querySelector('#pwd');

            // 先模拟点击激活输入框
            pwdField.click();

            // 等待浏览器完成点击响应
            await new Promise(resolve => setTimeout(resolve, 100));

            // 设置密码值并触发完整事件
            pwdField.value = arguments[0];
            var event = new Event('input', {
                bubbles: true,
                cancelable: true
            });
            pwdField.dispatchEvent(event);

            // 额外触发change事件确保表单验证
            var changeEvent = new Event('change');
            pwdField.dispatchEvent(changeEvent);
        """
        self.driver.execute_script(
            password_script,
            config.get('ACCOUNT', 'PASSWORD')
        )
        logging.info("密码已通过安全方式输入")

    def _select_provider(self):
        """选择网络服务商（增强中文兼容版）"""
        provider_name = config.get('NETWORK', 'PROVIDER')
        try:
            # 展开下拉菜单
            self.safe_click((By.CSS_SELECTOR, '#selectDisname'))

            # 显式等待选项容器加载
            #                联通为:bch_service_1  联通互联网服务
            #                移动为:bch_service_2  移动互联网服务
            #                电信为:bch_service_3  电信互联网服务
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'bch_service_3')))
            # 复合定位策略
            option_locator = (By.XPATH,
                              "//div[@id='bch_service_3']"
                              "//div[@class='right' and contains(., '电信互联网服务')]")
            # 等待元素可交互
            element =WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(option_locator))

            # 滚动到元素中心点
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});",
                element)

            # 模拟完整的人机交互
            ActionChains(self.driver).move_to_element(element).pause(0.3) \
                .click().pause(0.2).perform()

            logging.info(f"成功选择运营商：{provider_name}")

        except TimeoutException:
            logging.warning("常规选择失败，尝试备用方案")
            # JavaScript直接执行选择
            select_script = """
                const target = document.querySelector('div[id="bch_service_3"]');
                if (target) {
                    // 触发必要的鼠标事件
                    const mouseOverEvent = new MouseEvent('mouseover');
                    target.dispatchEvent(mouseOverEvent);

                    // 执行原始点击事件
                    const clickEvent = new MouseEvent('click');
                    target.dispatchEvent(clickEvent);
                    return true;
                }
                return false;
            """
            result = self.driver.execute_script(select_script)
            if not result:
                raise Exception(f"运营商选择失败：{provider_name}")

    def _submit_login(self):
        """提交登录"""
        self.safe_click((By.CSS_SELECTOR, '#loginLink_div'))
        logging.info("已提交登录请求")


# ---------------------- 主程序 ----------------------
if __name__ == "__main__":
    try:
        # 检查配置文件
        if not os.path.exists('config.ini'):
            raise FileNotFoundError("缺少配置文件 config.ini")

        connector = CampusNetworkConnector()
        connector.connect_network()
        logging.info("脚本执行完毕")

    except Exception as e:
        logging.critical("主程序异常终止", exc_info=True)