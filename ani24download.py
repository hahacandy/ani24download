import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
from selenium import webdriver
import time
import requests
import math
import re
import os
from datetime import datetime

form_class = uic.loadUiType("ani24download.ui")[0]


class AniDownThread(QThread):
    # 메인 애니 페이지에서 가져옴
    ani_list_url_array = None
    ani_list_name_array = None

    # 1 메인페이지 애니 전부 다운, 2 해당 애니만 다운
    down_mode = 1

    # 해당 애니만 다운로드 할 때, 해당 애니의 id를 전달받음
    ani_id = ""

    download_info_signal = pyqtSignal(str)
    download_progress_signal = pyqtSignal(int)
    download_server_signal = pyqtSignal(str)
    download_speed_signal = pyqtSignal(str)
    download_capacity_signal = pyqtSignal(str)
    download_remain_time_signal = pyqtSignal(str)
    download_exit_set_signal = pyqtSignal()

    def __init__(self, mode=1, ani_id=""):
        super(AniDownThread, self).__init__()
        self.down_mode = mode
        if self.down_mode == 2:
            self.ani_id = ani_id

    def run(self):
        while True:
            self.ani_list_url_array = []
            self.ani_list_name_array = []
            # 메인페이지 애니 다운로드
            if self.down_mode == 1:
                self.ani_list_down()
                # 배열에 담긴 애니 다운로드
                self.ani_story_down()
            # 해당 애니만 다운로드
            elif self.down_mode == 2:
                # 애니24주소를 가져옴
                f = open('./files/ani24url.txt', 'r')
                ani24url = f.readline()
                f.close()
                # 해당 애니 id를 가지고 해당 애니 페이지 url 생성
                ani_id_url = ani24url + "ani_list/" + self.ani_id + ".html"
                print(ani_id_url)
                self.ani_list_url_array.append(ani_id_url)
                self.ani_list_name_array.append(self.ani_id)
                # 배열에 담긴 애니 다운로드
                self.ani_story_down()
                # 버튼, 정보창 다시 보이게 하기
                self.download_exit_set_signal.emit()
                break

    # 애니24에 있는 메인페이지 애니 리스트를 가져와서 배열에 저장
    def ani_list_down(self):

        # 애니24주소를 가져옴
        f = open('./files/ani24url.txt', 'r')
        ani24url = f.readline()
        f.close()

        # 다운 받지 않을 애니를 가져옴
        ani_no_down_array = []
        f = open('./files/aniNoDown.txt', 'r+')
        while True:
            line = f.readline()
            if not line:
                break
            ani_no_down_array.append(line)
        f.close()

        # 애니24접속
        self.download_info_signal.emit(ani24url + " 페이지 기다리는 중")

        driver = ""
        try:
            driver = self.driver_set()
            driver.get(ani24url)

            # 월~일 완결 애니 주소 가져옴
            day_index = 1
            while day_index <= 8:
                today = ""
                if day_index == 1:
                    today = "월요일"
                elif day_index == 2:
                    today = "화요일"
                elif day_index == 3:
                    today = "수요일"
                elif day_index == 4:
                    today = "목요일"
                elif day_index == 5:
                    today = "금요일"
                elif day_index == 6:
                    today = "토요일"
                elif day_index == 7:
                    today = "일요일"
                elif day_index == 8:
                    today = "완결"

                # 해당 요일에 애니 몇개 들어있는지 가져옴
                ani_list = driver.find_element_by_xpath("/html/body/div[6]/div[2]/div[" + str(day_index) + "]")
                ani_list = ani_list.find_elements_by_tag_name("a")
                for idx, ani in enumerate(ani_list):
                    ani_name = str(ani.find_element_by_class_name("image").get_attribute("title"))
                    # 현재 애니가 노다운 애니면 다운 받지 않도록 함
                    no_down = False
                    for ani_no_down in ani_no_down_array:
                        if ani_name in ani_no_down:
                            no_down = True
                            break
                    if no_down is True:
                        print(ani_name + " 노다운")
                        continue
                    # 노다운 애니 아니면 애니 주소를 배열에 저장
                    self.ani_list_url_array.append(ani.get_attribute("href"))
                    self.ani_list_name_array.append(ani.find_element_by_class_name("subject").get_attribute("title"))
                    self.download_info_signal.emit(today + " 애니 가져오는 중 " + str(idx + 1) + "/" + str(len(ani_list)))
                    self.download_progress_signal.emit(math.ceil(idx / len(ani_list) * 100))
                self.download_progress_signal.emit(100)
                self.download_progress_signal.emit(-1)

                # 다음 요일 애니로 가기 위함
                day_index += 1
            self.download_info_signal.emit("애니 목록 가져오기 완료")
        except Exception as err:
            print("애니24 접속 에러: " + str(err))

        driver.close()

    # 해당 애니의 페이지로 들어가서 애니의 id 번호를 배열에 저장
    def ani_story_down(self):
        # 배열에 저장된 메인 페이지의 전체 애니에 대해 한번씩 들어감
        for idx, url in enumerate(self.ani_list_url_array):
            # 해당 애니 리스트 페이지 접속
            self.download_info_signal.emit("(" + str(len(self.ani_list_url_array)) + "편 중 " + str(idx + 1) + "번째) " +
                                           self.ani_list_name_array[idx] + " 페이지 기다리는 중")

            driver = ""
            try:
                driver = self.driver_set()
                driver.get(url)
            except Exception as err:
                print("해당 애니 접속 에러: " + str(err))

            ani_story_id_array = []
            ani_story_name_array = []
            ani_date = ""
            ani_story = ""
            ani_name = ""

            try:
                # 1화부터 끝화까지 id를 검색해 배열에 저장함
                ani_story = driver.find_element_by_class_name("ani_video_list").find_elements_by_tag_name(
                    "a")
                ani_story.reverse()  # 마지막화 부터 담겨져 있어서 뒤집음
                ani_name = str(driver.find_element_by_class_name("ani_info_title_font_box").text)  # 해당 애니 이름 추출

                # 애니 방영일 추출 하고 폴더 이름을 작성
                ani_date = str(driver.find_element_by_xpath("/html/body/div[7]/div[2]/div[2]/div[12]/span[2]").text)

            except Exception as err:
                print("애니 방영일 추출 에러: " + str(err))

            try:
                # 방영일 추출 하지 못했을 경우, 1화의 업로드 날짜를 가져옴
                if len(ani_date) < 3:
                    ani_date = str(driver.find_element_by_xpath("/html/body/div[8]/div[2]/div[2]/a[" +
                                                                str(len(ani_story)) + "]/div[2]/div[2]").text)
            except Exception as err:
                print("애니 방영일 추출 에러: " + str(err))
                driver.close()
                return

            # 애니 출시일자를 저장폴더이름으로 사용하기 위해 가공
            ani_date_year = ani_date[0:4] + "년도"
            ani_date_month = int(ani_date[5:7])
            if ani_date_month <= 3:
                ani_date_quarter = 1
            elif ani_date_month <= 6:
                ani_date_quarter = 2
            elif ani_date_month <= 9:
                ani_date_quarter = 3
            else:
                ani_date_quarter = 4
            ani_date_quarter = str(ani_date_quarter) + "분기"
            ani_name_folder = ani_date_year
            ani_name_folder2 = ani_date_quarter

            try:
                # driver 연동된 배열을 물리적배열에 변환시킴 (driver.close()가 되어도 되게끔)
                for idx2, ani in enumerate(ani_story):
                    # 애니 id 추출
                    ani_url = ani.get_attribute("href")
                    print(ani_url)
                    regex = re.compile('[0-9]{3,5}')
                    ani_id = regex.search(ani_url).group()
                    if ani_id is None:
                        print("id 추출 실패")
                        continue

                    # 애니 몇화인지 추출
                    ani_story_name = ani.find_element_by_class_name("subject").text

                    ani_story_id_array.append(ani_id)
                    ani_story_name_array.append(ani_story_name)
            except Exception as err:
                print("애니 리스트 추출 에러: " + str(err))
                return

            driver.close()

            # 배열에 저장된 애니를 다운 받음
            for idx2, ani_id in enumerate(ani_story_id_array):
                current_episode = idx2 + 1
                # 애니아이디, 분기, 애니이름, 애니이름 (몇화 포함), 전체 몇화, 지금 몇화, 전체 몇편, 지금 몇편
                self.ani_down(ani_id, ani_name_folder, ani_name_folder2, ani_name, ani_story_name_array[idx2],
                              len(ani_story_id_array), current_episode,
                              len(self.ani_list_url_array), idx + 1)

                # res = requests.head(url='http://goiyel.com/abab/id_39525.mp4')
                # print(res.headers['Content-Length'])

    # id를 가지고 여러개의 다운로드 서버에 접속하여 다운로드
    def ani_down(self, m_ani_id, m_ani_name_folder, m_ani_name_folder2, m_ani_name_folder3, m_ani_name,
                 m_all_episode, m_current_episode,
                 m_ani_all_all_count, m_ani_all_all_count2, re_start=False):
                 
        # 제목에 물음표 잇으면 지움
        m_ani_name_folder3 = m_ani_name_folder3.replace("?","")
        m_ani_name = m_ani_name.replace("?","")
        # 저장 경로 지정
        f = open('./files/aniSavePath.txt', 'r')
        m_dir = f.readline()
        f.close()
        # 저장 될 파일 이름
        m_save = m_ani_name + ".mp4"
        # 현재 몇편 중 몇번째인지
        m_all_progress = "(" + str(m_ani_all_all_count) + "편 중 " + str(m_ani_all_all_count2) + "편, " + \
                         str(m_all_episode) + "화 중 " + str(m_current_episode) + "화)"

        # res = requests.head(url=url)
        # print(res.headers)
        # print(res.status_code)

        # 다운로드 시도 로그 작성
        # self.down_log(m_dir, m_ani_name, 3)

        # 다운로드 서버 목록 불러와서 배열에 저장
        server_list_array = []
        f = open('./files/aniDownServers.txt', 'r+')
        while True:
            line = f.readline()
            if not line:
                break
            if len(line) > 5:
                line = line.replace("\n", "")
                server_list_array.append(line)
        f.close()

        # 다운로드 됐나 안됏나 확인
        downloaded = False
        # 배열에 저장된 서버 목록을 가지고 다운로드 시도
        for idx, value in enumerate(server_list_array):
            url = str(value) + "id_" + str(m_ani_id) + ".mp4"
            server_name = str(idx + 1) + "서버"
            self.download_server_signal.emit(server_name)
            self.download_info_signal.emit(m_all_progress + " " + m_ani_name + " 다운로드 시도 중")
            print(server_name + " " + m_ani_name + " 다운로드 시도 중")

            try:
                res = requests.head(url=url, verify=False, allow_redirects=True)
                total_size = int(res.headers.get('content-length'))
                # 파일 용량 10메가 이상만 받음
                if total_size < 10240000:
                    continue

                # 폴더 생성
                save_path = m_dir + "/" + m_ani_name_folder + "/" + m_ani_name_folder2 + "/" + m_ani_name_folder3.replace("?","")
                if not os.path.exists(save_path):
                    os.makedirs(save_path)

                # 다운 받을 애니 이미 저장 돼 있는지 확인
                try:
                    saved_ani_size = os.path.getsize(save_path + "/" + m_save)
                    if saved_ani_size == total_size:
                        self.download_info_signal.emit(m_all_progress + " (" + server_name + ") " + m_ani_name +
                                                       " 이미 다운 받음")
                        downloaded = True
                        print(m_ani_name + " 이미 존재함")
                        break
                except os.error:
                    print(m_ani_name + " 존재하지 않음")

                # 파일 저장
                with open(save_path + "/" + m_save, "wb") as f:
                    r = requests.get(url, stream=True, verify=False, allow_redirects=True)
                    total_size = int(r.headers.get('content-length'))
                    current_size = 0
                    last_time = 0
                    last_size = 0
                    speed = 0
                    if total_size is not None:
                        self.download_info_signal.emit(m_all_progress + " " + m_ani_name + " 다운로드 중")

                        for chunk in r.iter_content(1024):
                            # 현재 파일 사이즈
                            current_size += len(chunk)

                            # 파일 덧 붙여서 저장 중
                            f.write(chunk)

                            # 1초 마다 정보 변경
                            current_time = time.perf_counter()
                            if last_time + 1 <= current_time:
                                # 프로그래스 바 변경
                                down_percent = math.floor(current_size / total_size * 100)
                                if down_percent is not None:
                                    self.download_progress_signal.emit(down_percent)

                                # 다운 속도 구함
                                time_interval = current_time - last_time
                                speed = round((current_size/1024-last_size/1024) / time_interval)
                                last_size = current_size
                                last_time = time.perf_counter()

                                # 속도
                                self.download_speed_signal.emit(str(speed) + " Kb/s")

                                # 전체 크기 / 현재 크기
                                total_size_str = str(round(total_size / 1024 / 1024, 1)) + "MB"
                                current_size_str = str(round(current_size / 1024 / 1024, 1)) + "MB"
                                self.download_capacity_signal.emit(total_size_str + " 중 " + current_size_str)

                                # 남은 시간
                                if speed > 0:
                                    remain_time = math.ceil(((total_size / 1024) - (current_size / 1024)) / speed)
                                    remain_hour = math.floor(remain_time / 60 / 60)
                                    remain_min = math.floor((remain_time / 60) % 60)
                                    remain_sec = math.floor(remain_time % 60)
                                    if remain_hour != 0:
                                        remain_time_str = str(remain_hour) + "시간 " + str(remain_min) + "분 " + \
                                                          str(remain_sec) + "초 남음"
                                    elif remain_min != 0:
                                        remain_time_str = str(remain_min) + "분 " + str(remain_sec) + "초 남음"
                                    else:
                                        remain_time_str = str(remain_sec) + "초 남음"
                                else:
                                    remain_time_str = "알 수 없음"
                                self.download_remain_time_signal.emit(remain_time_str)

                        # 다운로드 다 했으니 다운로드 시도 빠져나옴
                        downloaded = True
                        self.download_info_signal.emit(m_ani_name + " 다운로드 완료")
                        self.download_progress_signal.emit(-1)
                        self.download_server_signal.emit("비활성")
                        self.download_speed_signal.emit("비활성")
                        self.download_capacity_signal.emit("비활성")
                        self.download_remain_time_signal.emit("비활성")
                        # avs 파일 작성
                        self.create_avs(m_dir, m_ani_name_folder, m_ani_name_folder2, m_ani_name_folder3, m_ani_name)
                        # 완료 로그 작성
                        self.down_log(m_dir, m_ani_name, 1, m_ani_name_folder, m_ani_name_folder2)
                        # 완료 print 로그 작성
                        print(m_ani_name + " 다운로드 완료 (" + m_ani_name_folder + " " + m_ani_name_folder2)
                        break
            except Exception as err:
                print(err)
        # 다운로드 실패시 다운서버 목록 추가하고, 한번만 더 애니 다운 시도함
        self.download_server_signal.emit("비활성")
        if downloaded is False:
            if re_start is False:
                print(m_ani_name + " 다운 안됨, 서버목록 추가 후 재시도")
                if self.ani_down_re(m_ani_id):
                    self.ani_down(m_ani_id, m_ani_name_folder, m_ani_name_folder2, m_ani_name_folder3, m_ani_name,
                                  m_all_episode, m_current_episode,
                                  m_ani_all_all_count, m_ani_all_all_count2, True)
                else:
                    # 다운로드 실패 로그 작성
                    self.down_log(m_dir, m_ani_name, 2)
            # 다운로드 재시도 했는데도 실패면 로그 작성
            elif re_start is True:
                print(m_ani_name + " 다운 안됨")
                self.down_log(m_dir, m_ani_name, 2)

    # 애니가 다운이 안됐을떄, 다운서버 주소 추가하고 성공, 실패 리턴함
    def ani_down_re(self, _m_ani_id):
        driver = ""
        try:
            driver = self.driver_set()
            # 애니24주소를 가져옴
            f = open('./files/ani24url.txt', 'r')
            ani24url = f.readline()
            f.close()
            url = ani24url + "ani_view/" + _m_ani_id + ".html"

            # 다운서버 주소 추출 미가공된 상태
            driver.get(url)
            driver.find_element_by_class_name("view_box_left").click()
            time.sleep(5)
            iframes = driver.find_elements_by_tag_name('iframe')
            driver.switch_to_frame(iframes[0])
            server_url = str(driver.find_element_by_class_name("link_video").get_attribute("data-link"))

            driver.close()

            # 다운서버 주소 가공
            server_url = server_url.replace("id_" + _m_ani_id + ".mp4", "")
            if len(server_url) > 5:
                # 다운서버 주소 추가
                f = open('./files/aniDownServers.txt', 'a')
                f.write("\n" + server_url)
                f.close()
                print("다운서버 추가 완료")
                
            # 다운서버 중복 제거
            ani_down_server_array = []
            f = open('./files/aniDownServers.txt', 'r')
            while True:
                line = f.readline()
                if not line:
                    break
                if len(line) > 5:
                    ani_down_server_array.append(line)
            f.close()

            # 배열 중복 제거
            ani_down_server_array = list(set(ani_down_server_array))

            # 다운 서버 txt 재생성시 오류 대비 백업 생성
            os.rename('./files/aniDownServers.txt', './files/aniDownServers_bak.txt')

            # 다운 서버 txt 재생성
            f = open('./files/aniDownServers.txt', 'a')
            for idx, value in enumerate(ani_down_server_array):
                value = value.replace("\n", "")
                if idx == 0:
                    f.write(value)
                else:
                    f.write("\n" + value)
            f.close()

            # 다운 서버 txt 완료했으니 bak파일 삭제
            os.remove('./files/aniDownServers_bak.txt')
            print("다운서버 중복 제거 완료")

            return True

        except Exception as err:
            print(err)
            driver.close()
            return False

    # 다운 완료시 로그 작성
    def down_log(self, m_dir, m_ani_name, mode=1, m_ani_name_folder="", m_ani_name_folder2=""):
        # 로그 폴더 없으면 생성
        if not os.path.exists(m_dir + "/" + "log"):
            os.makedirs(m_dir + "/" + "log")
        # 현재 날짜 추출
        now = datetime.now()
        log_time = "%04d%02d%02d" % (now.year, now.month, now.day)
        # 다운로드 완료 로그 생성
        if mode == 1:
            f = open(m_dir + "/" + "log" + "/" + log_time + " down.txt", 'a')
            now_str = '[%04d-%02d-%02d %02d:%02d:%02d]' % (now.year, now.month, now.day, now.hour,
                                                           now.minute, now.second)
            if len(m_ani_name_folder) > 0 and len(m_ani_name_folder2) > 0:
                f.write(now_str + " " + m_ani_name + " (다운로드 완료) (" + m_ani_name_folder +
                        ", " + m_ani_name_folder2 + ")\n")
            else:
                f.write(now_str + " " + m_ani_name + " (다운로드 완료)\n")
            f.close()
        # 다운로드 실패 로그
        elif mode == 2:
            f = open(m_dir + "/" + "log" + "/" + log_time + " error.txt", 'a')
            now_str = '[%04d-%02d-%02d %02d:%02d:%02d]' % (now.year, now.month, now.day, now.hour,
                                                           now.minute, now.second)
            f.write(now_str + " " + m_ani_name + " (다운로드 실패)\n")
            f.close()
        elif mode == 3:
            f = open(m_dir + "/" + "log" + "/" + log_time + " log.txt", 'a')
            now_str = '[%04d-%02d-%02d %02d:%02d:%02d]' % (now.year, now.month, now.day, now.hour,
                                                           now.minute, now.second)
            f.write(now_str + " " + m_ani_name + " (다운로드 시도)\n")
            f.close()

    # 방금 다운 받은 애니 AVS 파일 만듬
    def create_avs(self, m_dir, m_folder, m_folder2, m_folder3, m_ani_name):
        m_path = m_dir + "/" + m_folder + "/" + m_folder2 + "/" + m_folder3
        # m_ani_name_avs = "(24FPS) " + m_ani_name
        m_ani_name_avs = "" + m_ani_name
        if os.path.isfile(m_path + "/" + m_ani_name_avs + ".avs"):
            os.remove(m_path + "/" + m_ani_name_avs + ".avs")
        f = open(m_path + "/" + m_ani_name_avs + ".avs", 'a')
        f.write(
            "DirectShowSource(\".\\" + m_ani_name + ".mp4\", convertfps=true)\nChangeFPS(24)\nConvertToYV12()")
        f.close()
        return

    def driver_set(self):
        option = webdriver.ChromeOptions()

        # option.add_argument('--headless')

        option.add_argument('--disable-infobars')
        option.add_argument('--window-size=100x100')
        option.add_argument('--disable-gpu')

        extensions_option = "--load-extension=" + os.getcwd() + "/files/Extensions/adBlock/3.6.3_0,"
        option.add_argument(extensions_option)

        # 비활성 상태에서는 적용도 안되고 실행도 안됨 망할
        chrome_prefs = {}
        option.experimental_options["prefs"] = chrome_prefs
        chrome_prefs["profile.default_content_settings"] = {"images": 2}
        chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
        option.add_argument('--user-data-dir=' + os.getcwd() + '/files/dataDir')

        driver = webdriver.Chrome('./driver/chromedriver', options=option)
        driver.set_window_size(700, 1000)
        return driver



class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(462, 161)
        self.ani_down_thread = None
        # 정보창 숨김
        self.aniProgressBar.hide()
        self.aniServer.hide()
        self.aniSpeed.hide()
        self.aniCapacity.hide()
        self.aniRemainTime.hide()
        # 버튼 이랑 함수랑 연결
        self.startBtn.clicked.connect(self.btn_start)
        self.startAniIdBtn.clicked.connect(self.btn_start_ani_id)
        self.avsResetBtn.clicked.connect(self.avs_reset)
        self.aniNoDownBtn.clicked.connect(self.ani_no_down_set)

    # 애니 메인페이지 전부 다운로드
    def btn_start(self):
        # 애니 다운로드 하는 쓰레드 실행
        self.q_start(1)

    # 해당 애니만 다운로드
    def btn_start_ani_id(self):
        ani_id = self.aniIdInput.text()
        if len(ani_id) > 0:
            if self.is_number(ani_id):
                # 애니 다운로드 하는 쓰레드 실행
                self.q_start(2, ani_id)
            else:
                self.aniIdInput.setFocus()
                self.set_info_value("애니 id를 숫자로 입력해주세요.")
        else:
            self.aniIdInput.setFocus()
            self.set_info_value("애니 id를 입력해주세요.")

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    # 시작 버튼 눌렀을때 Q 쓰레드 기본 셋팅
    def q_start(self, mode=1, ani_id=""):
        # Q 쓰레드 지정 (mode 1이면 메인페이지 전체 다운로드, 2이면 해당 애니 id만 다운로드함
        self.ani_down_thread = AniDownThread(mode, ani_id)
        # Q 쓰레드랑 정보창이랑 연결 시킴
        self.ani_down_thread.download_info_signal.connect(self.set_info_value)
        self.ani_down_thread.download_progress_signal.connect(self.set_progressbar_value)
        self.ani_down_thread.download_server_signal.connect(self.set_server_value)
        self.ani_down_thread.download_speed_signal.connect(self.set_speed_value)
        self.ani_down_thread.download_capacity_signal.connect(self.set_capacity_value)
        self.ani_down_thread.download_remain_time_signal.connect(self.set_remain_value)
        self.ani_down_thread.download_exit_set_signal.connect(self.q_exit_set)
        # 시작 버튼 숨기기
        self.startBtnLabel.hide()
        self.startBtn.hide()
        self.startAniIdBtn.hide()
        # 정보창 감추기 또는 비활성화
        if mode == 1:
            self.aniIdInfo.hide()
            self.aniIdInput.hide()
        elif mode == 2:
            self.aniIdInfo.setEnabled(False)
            self.aniIdInput.setEnabled(False)
        # Q 쓰레드 실행
        self.ani_down_thread.start()

    # 다운로드 끝나면 다시 버튼, 정보창 살아나게 함
    def q_exit_set(self):
        self.startBtnLabel.show()
        self.startBtn.show()
        self.startAniIdBtn.show()
        self.aniIdInfo.setEnabled(True)
        self.aniIdInput.setEnabled(True)
        self.set_info_value("시작 버튼을 눌러주세요.")



    # 애니 노다운 txt 열게 해줌
    def ani_no_down_set(self):
        os.popen(os.getcwd() + "/files/aniNoDown.txt")

    # avs 초기화 버튼 누르면 avs 파일 경로 초기화
    def avs_reset(self):
        # 저장 경로 지정
        f = open('./files/aniSavePath.txt', 'r')
        m_path = f.readline()
        f.close()
        # 해당 경로의 avs 파일 다 지움
        for (path, dir, files) in os.walk(m_path):
            for filename in files:
                file_name = os.path.splitext(filename)[0]
                ext = os.path.splitext(filename)[1]
                if ext == '.avs':
                    if os.path.isfile(path + "/" + file_name + ".avs"):
                        os.remove(path + "/" + file_name + ".avs")
                        print(path + "/" + file_name)
        # 실제로 있는 애니의 avs만을 작성
        for (path, dir, files) in os.walk(m_path):
            for filename in files:
                file_name = os.path.splitext(filename)[0]
                ext = os.path.splitext(filename)[1]
                if ext == '.mp4':
                    file_name2 = "(24FPS) " + file_name
                    f = open(path + "/" + file_name2 + ".avs", 'a')
                    f.write(
                        "DirectShowSource(\".\\" + file_name + ".mp4\", convertfps=true)\nChangeFPS(24)\nConvertToYV12()")
                    f.close()
                    self.set_info_value("avs 초기화 완료!")

    def set_info_value(self, value):
        if value == "비활성":
            self.aniInfo.hide()
        else:
            self.aniInfo.setText(value)
            self.aniInfo.show()

    def set_progressbar_value(self, value):
        if value == -1:
            self.aniProgressBar.hide()
        else:
            self.aniProgressBar.setValue(value)
            self.aniProgressBar.show()

    def set_server_value(self, value):
        if value == "비활성":
            self.aniServer.hide()
        else:
            self.aniServer.setText(value)
            self.aniServer.show()

    def set_speed_value(self, value):
        if value == "비활성":
            self.aniSpeed.hide()
        else:
            self.aniSpeed.setText(value)
            self.aniSpeed.show()

    def set_capacity_value(self, value):
        if value == "비활성":
            self.aniCapacity.hide()
        else:
            self.aniCapacity.setText(value)
            self.aniCapacity.show()

    def set_remain_value(self, value):
        if value == "비활성":
            self.aniRemainTime.hide()
        else:
            self.aniRemainTime.setText(value)
            self.aniRemainTime.show()

    # 창 닫히면 쓰레드도 같이 꺼짐
    def closeEvent(self, *args, **kwargs):
        if self.ani_down_thread is not None:
            self.ani_down_thread.terminate()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    app.exec_()
