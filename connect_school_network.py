import logging
import time
import configparser
import os
import warnings
import urllib3
import socket
from contextlib import contextmanager
from typing import Tuple, Optional

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException

# Suppress unnecessary warnings
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
config.read('config.ini', encoding="UTF-8")


# ---------------------- 网络连接检测工具 ----------------------
class NetworkUtils:
    @staticmethod
    def is_connected(host="8.8.8.8", port=53, timeout=3):
        """检测是否已连接到互联网"""
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception:
            return False

    @staticmethod
    @contextmanager
    def timeout_handler(timeout_seconds=10):
        """超时处理上下文管理器"""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutException("操作超时")

        # 设置信号处理器
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            yield
        finally:
            # 恢复原始处理器
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)


# ---------------------- 核心功能类 ----------------------
class CampusNetworkConnector:
    def __init__(self):
        self.driver = None
        self.wait_timeout = int(config.get('BROWSER', 'WAIT_TIMEOUT', fallback='30'))
        self.retry_count = int(config.get('BROWSER', 'RETRY_COUNT', fallback='3'))
        self.setup_driver()

    def setup_driver(self):
        """初始化浏览器驱动，确保完全绕过代理直连"""
        try:
            driver_path = config.get('CHROME', 'DRIVER_PATH',
                                     fallback=r"C:\chromedriver\chromedriver.exe")
            chrome_service = Service(driver_path)

            options = webdriver.ChromeOptions()

            # 基本配置
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--disable-notifications')

            # 完全禁用所有代理 - 关键修复
            options.add_argument('--no-proxy-server')
            options.add_argument('--proxy-bypass-list=*')

            # 使用系统代理设置为"never"
            options.add_argument('--proxy-server="direct://"')
            options.add_argument('--proxy-bypass-list=*')
            #无头模式设置
            if config.getboolean('CHROME', 'HEADLESS', fallback=False):
                options.add_argument('--headless')

            # 实验性选项 - 禁用代理检查
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)

            # 关键设置 - 明确禁用所有代理连接
            prefs = {
                'network.proxy.type': 0,  # 直连模式
                'network.proxy.no_proxies_on': '*',
                'network.http.use-cache': False,
            }
            options.add_experimental_option('prefs', prefs)

            # 创建自定义环境变量 - 绕过系统代理
            os.environ['no_proxy'] = '*'
            # 禁用urllib3代理
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''

            # 创建浏览器实例
            self.driver = webdriver.Chrome(
                service=chrome_service,
                options=options
            )

            # 使用CDP命令禁用代理（Chrome DevTools Protocol）
            self.driver.execute_cdp_cmd("Network.enable", {})
            self.driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
                "offline": False,
                "latency": 0,
                "downloadThroughput": -1,
                "uploadThroughput": -1,
                "connectionType": "none"
            })

            # 最后再次确认禁用代理
            self.driver.execute_script('''
                navigator.connection.type = "none";
                navigator.connection.downlinkMax = Infinity;
            ''')

            logging.info("浏览器初始化成功，已强制配置直连模式")

        except Exception as e:
            logging.critical(f"浏览器初始化失败: {str(e)}", exc_info=True)
            raise

    def safe_click(self, locator: Tuple[str, str], retries: int = 3) -> bool:
        """带重试机制的点击操作"""
        for attempt in range(retries):
            try:
                element = WebDriverWait(self.driver, self.wait_timeout).until(
                    EC.element_to_be_clickable(locator)
                )

                # 确保元素在视图中
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});",
                    element
                )

                # 尝试普通点击
                element.click()
                time.sleep(0.5)  # 短暂等待确保操作完成
                return True

            except ElementClickInterceptedException:
                # 如果元素被遮挡，尝试JS点击
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass

            except Exception as e:
                if attempt < retries - 1:
                    logging.warning(f"点击元素 {locator} 失败，尝试第 {attempt + 2} 次: {str(e)}")
                    time.sleep(1)  # 等待后重试
                else:
                    logging.error(f"点击元素 {locator} 失败: {str(e)}")
                    return False

        return False

    def safe_input(self, locator: Tuple[str, str], text: str) -> bool:
        """带等待的安全文本输入"""
        try:
            element = WebDriverWait(self.driver, self.wait_timeout).until(
                EC.visibility_of_element_located(locator)
            )

            # 确保元素在视图中
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});",
                element
            )

            # 清空输入框并用JS设置值
            element.clear()
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; " +
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true})); " +
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                element, text
            )

            return True
        except Exception as e:
            logging.error(f"输入文本到 {locator} 失败: {str(e)}")
            return False

    def connect_network(self):
        """执行完整的连接流程，包含自动重试和断网检测"""
        if NetworkUtils.is_connected():
            logging.info("检测到网络已连接，无需执行登录")
            self.driver.quit()
            return True

        start_time = time.time()

        try:
            # 打开登录页面
            url = config.get('NETWORK', 'LOGIN_URL', fallback="http://172.168.100.21")
            self.driver.get(url)
            logging.info(f"已访问校园网登录页面: {url}")

            # 等待页面完全加载
            WebDriverWait(self.driver, self.wait_timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )

            # 登录流程
            if self._perform_login() and self._select_provider() and self._submit_login():
                # 等待连接完成
                time.sleep(3)

                # 验证连接结果
                if "success" in self.driver.page_source.lower() or NetworkUtils.is_connected():
                    elapsed_time = time.time() - start_time
                    logging.info(f"网络连接成功，耗时 {elapsed_time:.2f} 秒")
                    print("连接成功!")
                    return True
                else:
                    logging.warning("连接状态未知，请手动确认")
            else:
                logging.error("登录流程执行失败")

        except TimeoutException as e:
            logging.error(f"页面加载超时: {str(e)}")
        except WebDriverException as e:
            logging.error(f"浏览器驱动异常: {str(e)}")
        except Exception as e:
            logging.error(f"网络连接流程异常: {str(e)}", exc_info=True)
        finally:
            # 确保资源释放
            try:
                if self.driver:
                    self.driver.quit()
            except Exception as e:
                logging.error(f"资源释放失败:{str(e)}",exc_info=True)

        return False

    def _perform_login(self) -> bool:
        """处理账号密码输入"""
        try:
            # 输入账号
            username = config.get('ACCOUNT', 'USERNAME')
            if not self.safe_input((By.CSS_SELECTOR, '#username'), username):
                return False

            # 输入密码 - 更安全的方式
            password = config.get('ACCOUNT', 'PASSWORD')
            password_script = """
                // 获取密码输入框元素
                var pwdField = document.querySelector('#pwd');
                if (!pwdField) return false;

                // 先模拟点击激活输入框
                pwdField.focus();

                // 设置密码值并触发完整事件
                pwdField.value = arguments[0];

                // 触发必要的事件
                ['input', 'change', 'blur'].forEach(eventType => {
                    var event = new Event(eventType, {
                        bubbles: true,
                        cancelable: true
                    });
                    pwdField.dispatchEvent(event);
                });

                return true;
            """

            result = self.driver.execute_script(password_script, password)
            if not result:
                logging.error("密码输入框未找到")
                return False

            logging.info("账号密码已通过安全方式输入")
            return True

        except Exception as e:
            logging.error(f"账号密码输入失败: {str(e)}")
            return False

    def _select_provider(self) -> bool:
        """选择网络服务商 - 增强版"""
        provider_id = config.get('NETWORK', 'PROVIDER_ID', fallback='bch_service_3')
        provider_name = config.get('NETWORK', 'PROVIDER_NAME', fallback='电信互联网服务')

        try:
            # 展开下拉菜单
            if not self.safe_click((By.CSS_SELECTOR, '#selectDisname'), retries=3):
                logging.warning("展开下拉菜单失败，尝试备用方案")
                # 使用JS直接展开
                self.driver.execute_script(
                    "var el = document.querySelector('#selectDisname'); if(el) el.click();"
                )
                time.sleep(1)

            # 尝试三种选择方式
            # 1. 常规XPath选择
            try:
                option_locator = (By.XPATH,
                                  f"//div[@id='{provider_id}']//div[@class='right' and contains(., '{provider_name}')]")

                element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(option_locator))
                ActionChains(self.driver).move_to_element(element).pause(0.3).click().perform()
                logging.info(f"通过XPath成功选择运营商: {provider_name}")
                return True

            except Exception:
                logging.warning("XPath选择失败，尝试备用方案")

            # 2. ID直接选择
            try:
                id_locator = (By.ID, provider_id)
                if self.safe_click(id_locator, retries=2):
                    logging.info(f"通过ID成功选择运营商: {provider_name}")
                    return True
            except Exception:
                logging.warning("ID选择失败，尝试JS方案")

            # 3. JavaScript终极方案
            select_script = f"""
                // 尝试多种选择器
                const targets = [
                    document.querySelector('div[id="{provider_id}"]'),
                    document.querySelector('#{provider_id}'),
                    document.querySelector('div:contains("{provider_name}")')
                ].filter(el => el);

                // 对每个可能的目标元素尝试点击
                for (const target of targets) {{
                    try {{
                        // 确保元素可见
                        target.scrollIntoView({{block: 'center'}});

                        // 模拟鼠标悬停
                        const mouseOverEvent = new MouseEvent('mouseover', {{
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }});
                        target.dispatchEvent(mouseOverEvent);

                        // 执行点击
                        target.click();

                        // 再尝试一次原生click方法
                        const clickEvent = new MouseEvent('click', {{
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }});
                        target.dispatchEvent(clickEvent);

                        return true;
                    }} catch (e) {{
                        continue;
                    }}
                }}

                // 尝试直接设置选择框的值
                try {{
                    const selectBox = document.querySelector('#selectDisname');
                    if (selectBox) {{
                        selectBox.value = "{provider_id}";
                        selectBox.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return true;
                    }}
                }} catch (e) {{}}

                return false;
            """

            result = self.driver.execute_script(select_script)
            if result:
                logging.info(f"通过JavaScript成功选择运营商: {provider_name}")
                return True

            logging.error(f"所有方法都无法选择运营商: {provider_name}")
            return False

        except Exception as e:
            logging.error(f"选择运营商失败: {str(e)}")
            return False

    def _submit_login(self) -> bool:
        """提交登录请求"""
        try:
            # 尝试多种方式点击登录按钮
            # 1. 通过CSS选择器
            if self.safe_click((By.CSS_SELECTOR, '#loginLink_div'), retries=2):
                logging.info("已通过CSS选择器提交登录请求")
                return True

            # 2. 通过ID
            if self.safe_click((By.ID, 'loginLink_div'), retries=2):
                logging.info("已通过ID提交登录请求")
                return True

            # 3. 通过JavaScript
            login_script = """
                // 尝试多种选择器找到登录按钮
                const loginButtons = [
                    document.querySelector('#loginLink_div'),
                    document.querySelector('.login_btn'),
                    document.querySelector('input[type="submit"]'),
                    document.querySelector('button[type="submit"]'),
                    ...Array.from(document.querySelectorAll('button')).filter(el => 
                        el.textContent.includes('登录') || 
                        el.textContent.includes('Login')
                    )
                ].filter(el => el);

                // 尝试点击找到的第一个按钮
                for (const btn of loginButtons) {
                    try {
                        btn.click();
                        return true;
                    } catch (e) {}
                }

                return false;
            """

            result = self.driver.execute_script(login_script)
            if result:
                logging.info("已通过JavaScript提交登录请求")
                return True

            logging.error("所有方法都无法提交登录请求")
            return False

        except Exception as e:
            logging.error(f"提交登录请求失败: {str(e)}")
            return False


# 在主程序中，创建连接器前添加以下代码
def disable_system_proxy():
    """禁用系统代理设置"""
    # 设置环境变量绕过系统代理
    os.environ['no_proxy'] = '*'
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''

    # 禁用urllib3代理设置
    import urllib3
    urllib3.disable_warnings()

    # 禁用requests代理
    try:
        import requests
        # 强制requests不使用代理
        requests.Session().trust_env = False
    except ImportError:
        pass

    # 禁用selenium代理
    import selenium
    if hasattr(selenium, 'webdriver'):
        selenium.webdriver.common.utils.is_connectable = lambda port: True


# ---------------------- 主程序 ----------------------
if __name__ == "__main__":
    try:
        # 检查配置文件
        if not os.path.exists('config.ini'):
            logging.critical("缺少配置文件 config.ini")
            print("错误: 缺少配置文件 config.ini")
            exit(1)

        # 检查是否已连接网络
        if NetworkUtils.is_connected():
            logging.info("网络已连接，无需执行登录")
            print("网络已连接，无需执行登录")
            exit(0)

        # 执行连接
        print("开始连接校园网...")
        # 在创建连接器前调用
        disable_system_proxy()
        connector = CampusNetworkConnector()
        success = connector.connect_network()
        if success:
            print("✓ 校园网连接成功!")
            exit(0)
        else:
            print("✗ 校园网连接失败，详情请查看日志")
            exit(1)

    except KeyboardInterrupt:
        print("\n操作已取消")
        logging.info("用户取消操作")
    except Exception as e:
        print(f"错误: {str(e)}")
        logging.critical("主程序异常终止", exc_info=True)
        exit(1)
