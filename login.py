import time
import random
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import logging


class JDLogin:

    def __init__(self):
        option = webdriver.ChromeOptions()
        option.add_argument('--no-sandbox')
        option.add_argument('--headless')
        # self.browser = webdriver.Chrome(chrome_options=option)  # 服务器开启无头模式
        self.browser = webdriver.Chrome()
        self.until = WebDriverWait(self.browser, 10).until
        self.logger = logging.getLogger('login')

    def login(self, username, password):
        self.browser.get('http://brand.shop.jd.com')

        time.sleep(1)
        self.browser.switch_to.frame('loginFrame')

        username_input = self.until(EC.presence_of_element_located((By.ID, 'loginname')))
        self.input_text(username_input, username)
        password_input = self.until(EC.presence_of_element_located((By.ID, 'nloginpwd')))
        self.input_text(password_input, password)

        login_btn = self.until(EC.presence_of_element_located((By.ID, 'paipaiLoginSubmit')))
        login_btn.click()

    def input_text(self, input, text):
        self.logger.info('input: {}'.format(text))
        while text:
            input.send_keys(text[0])
            text = text[1:]
            time.sleep(random.random() / 2)

    def is_element_exists(self, css_selector):
        try:
            self.browser.find_element_by_css_selector(css_selector)
            return True
        except Exception:
            return False

    def check_login(self, times=15):
        if times <= 0:
            self.logger.error('尝试15次也没登录成功')
            return
        try:
            if self.is_element_exists('#bgDiv .item-ifo > .error'):
                self.logger.info('登录失败，用户名或密码错误')
                return
            self.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.JDJRV-suspend-slide')))
            self.logger.info('滑块验证码')
            self.crack_code()
            time.sleep(2)
            return self.check_login(times - 1)
        except Exception:
            if self.is_element_exists('.homeSidebar-bannerMes'):
                self.logger.info('登录成功')
                return {cookie['name']: cookie['value'] for cookie in self.browser.get_cookies()}
            else:
                self.browser.get_screenshot_as_file('{}.png'.format(int(time.time() * 1000)))
                return

    def crack_code(self):
        '''模拟滑动滑块验证码'''
        import base64
        from img import get_gap_x_percent
        img = self.browser.find_element_by_css_selector('.JDJRV-bigimg > img')
        src = img.get_attribute('src')
        src = src.replace('data:image/png;base64,', '')
        img_bytes = base64.b64decode(src)
        file = 'code.png'
        with open(file, 'wb') as f:
            f.write(img_bytes)
        gap_x_percent = get_gap_x_percent(file)
        gap_x = int(img.size['width'] * gap_x_percent)
        self.logger.info('缺口位置：{}'.format(gap_x))
        track = self.get_track(gap_x)
        self.logger.info('移动轨迹:{}'.format(track))
        btn = self.browser.find_element_by_css_selector('.JDJRV-slide-inner.JDJRV-slide-btn')
        self.move_to_gap(btn, track)

    def move_to_gap(self, slider, track):
        """
        拖动滑块到缺口处
        :param slider: 滑块
        :param track: 轨迹
        :return:
        """
        ActionChains(self.browser).click_and_hold(slider).perform()
        for x in track:
            # ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=0).perform()
            ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=random.randint(-3, 3)).perform()  # 加入上下抖动
            time.sleep(random.random() / 50)
        time.sleep(0.3)
        ActionChains(self.browser).release().perform()

    @staticmethod
    def get_track(distance):
        '''
        根据偏移量获取移动轨迹
        :param distance: 偏移量
        :return: 移动轨迹
        '''
        track = []  # 移动轨迹
        current = 0  # 当前位移
        mid = distance * 4 / 5  # 减速阈值
        t = 0.2  # 计算间隔
        v = 0  # 初速度

        while current < distance:
            if current < mid:
                a = 2  # 加速度为正2
            else:
                a = -3  # 加速度为负3
            v0 = v  # 初速度v0
            v = v0 + a * t  # 当前速度v = v0 + at
            move = v0 * t + 1 / 2 * a * t * t  # 移动距离x = v0t + 1/2 * a * t^2
            current += move  # 当前位移
            track.append(round(move))
        return track

    def __del__(self):
        try:
            self.browser.close()
        except Exception as e:
            print(e)


def login(username, password):
    '''
    登录成功 返回cookies
    登录失败 返回None
    '''
    jd = JDLogin()
    jd.login(username, password)
    return jd.check_login()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    cookies = login('username', 'password')
    print(cookies)
