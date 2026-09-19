import cv2
from win32com.client import Dispatch
from win32api import GetSystemMetrics
from numpy import interp
from time import time
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key
from pynput.mouse import Controller as MouseController
from pynput.mouse import Button
import pydirectinput  # 추가

from Handcontroller import Hand_Controller

class VirtualGameController:
    def __init__(self):
        print("[시스템] 1. 컨트롤러 초기화 시작...")
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        
        print("[시스템] 2. 음성 엔진 비활성화 처리 중...")
        # 윈도우 음성 기능이 멈춤을 유발할 수 있으므로 완전히 강제 비활성화합니다.
        self.voice_engine = None 
            
        print("[시스템] 3. 인공지능(MediaPipe) 손 인식 모델 불러오는 중... (몇 초 걸릴 수 있습니다)")
        self.hand_detector = Hand_Controller()
        
        print("[시스템] 4. 카메라 연결 시도 중...")
        # 반드시 cv2.CAP_DSHOW 를 추가하여 윈도우 카메라 충돌을 방지합니다.
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
        self.cam_width, self.cam_height = 960, 720
        self.cap.set(3, self.cam_width)
        self.cap.set(4, self.cam_height)
        
        if self.cap.isOpened():
            print("[시스템] 카메라 연결 성공!")
        else:
            print("[시스템] 카메라 연결 실패! (카메라 권한이나 연결 상태를 확인하세요)")
        
        print("[시스템] 5. 화면 및 컨트롤 변수 설정 중...")
        self.setup_display_settings()
        
        self.controller_mode = 1  
        self.setup_control_variables()
        
        self.gesture_mappings = {
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'jump': Key.space
        }
        
        self.quit_confirmed = False
        import pydirectinput
        pydirectinput.PAUSE = 0.0  
        
        print("[시스템] 모든 초기화 완료! GUI를 띄웁니다.")
    def say(self, message):
        """음성 출력 기능"""
        if self.voice_engine:
            self.voice_engine.Speak(message)
        else:
            print(f"Voice: {message}")
            
    def setup_display_settings(self):
        """화면 표시 설정"""
        # 폰트 설정
        self.font_type = cv2.FONT_HERSHEY_PLAIN
        self.font_size = 1
        self.font_color = (215, 255, 214)
        self.font_thickness = 2
        
        # 화면 영역 설정
        self.start_x, self.start_y = 225, 50
        self.end_x, self.end_y = 575, 400
        self.hand_start_x, self.hand_start_y = 225, 100
        self.hand_end_x, self.hand_end_y = 575, 400
        self.mid_x = (self.start_x + self.end_x) // 2
        self.screen_width, self.screen_height = GetSystemMetrics(0), GetSystemMetrics(1)
    
    def setup_control_variables(self):
        """컨트롤 변수 설정"""
        # 방향 및 점프 상태
        self.v_dir, self.h_dir, self.jump = 0, 0, 0
        
        # 손가락 상태 변수
        self.thumb = self.index_finger = self.middle_finger = self.ring_finger = self.pinky_finger = 1
        self.finger_up_state = []
        
        # FPS 계산 변수
        self.prev_time, self.cur_time = 0, 0
        
        # 마우스 포인터 변수
        self.pointer_x, self.pointer_y = 0, 0
        self.clicked = 0
        self.clk = 0
        
    def init_camera(self):
        """카메라 초기화"""
        self.say('카메라 연결 중')
        self.cap = cv2.VideoCapture(0)
        self.cam_width, self.cam_height = 960, 720
        self.cap.set(3, self.cam_width)
        self.cap.set(4, self.cam_height)
        if self.cap.isOpened():
            self.say('카메라 연결됨')
        else:
            self.say('카메라 연결 실패')
    
    def check_in_area(self, point_list, area_type=0):
        """
        손가락 위치가 특정 영역 안에 있는지 확인
        area_type: 
        0 - 인식 영역 내 손가락 확인
        1 - 제스처 영역 내 손가락 확인
        2 - 어떤 상태 박스에 손가락이 있는지 확인
        3 - 종료 버튼 영역 내 손가락 확인
        """
        if area_type == 0:
            if self.start_x < point_list[0] < self.end_x and self.start_y < point_list[1] < self.hand_start_y:
                return True
            return False

        if area_type == 1:
            if self.hand_start_x < point_list[0] < self.hand_end_x and self.hand_start_y < point_list[1] < self.hand_end_y:
                return True
            return False

        elif area_type == 2:
            if self.start_x < point_list[0] < self.mid_x and self.start_y < point_list[1] < self.hand_start_y:
                return 1
            elif self.mid_x < point_list[0] < self.end_x and self.start_y < point_list[1] < self.hand_start_y:
                return 2
            return 0

        elif area_type == 3:
            if (self.start_x-100) < point_list[0] < self.start_x and self.start_y < point_list[1] < self.hand_start_y:
                return True
            return False
        
        return 0
        
    def mouse_pointer_click(self, centre, dis, clicked, image):
        """마우스 포인터 클릭 처리"""
        cx, cy = centre
        cv2.circle(image, (cx, cy), 15, (181, 181, 181), cv2.FILLED)   
        if clicked >= 1:
            clicked = 0

        if dis < 30:
            cv2.circle(image, (cx, cy), 15, (0, 252, 51), cv2.FILLED)
            if clicked == 0:
                clicked = 1

        if clicked == 1:
            clicked += 1
        return clicked
    
    def set_gesture_mapping(self, gesture, key):
        """제스처와 키 매핑 설정"""
        self.gesture_mappings[gesture] = key
        
    def get_gesture_mapping(self, gesture):
        """제스처에 매핑된 키 반환"""
        return self.gesture_mappings.get(gesture, None)
    
    def process_frame(self, active=False):
        """카메라 프레임 처리"""
        if not self.cap.isOpened():
            return None, False
            
        ret, cap_img = self.cap.read()
        if not ret:
            return None, False
            
        self.cur_time = time()
        main_img = cv2.flip(cap_img, 1)
        
        # 손 인식 처리
        main_img = self.hand_detector.findhand(main_img, True)
        lm_list = self.hand_detector.findPosition()
        
        # 방향 상태 초기화
        self.v_dir, self.h_dir, self.jump = 0, 0, 0
        state_text = ""
        hand_detection = False
        detected_gestures = []
        
        # 손이 인식된 경우 처리
        if lm_list:
            hand_detection = True
            state_text, detected_gestures = self.process_hand_gestures(lm_list, main_img)
            
            # 인식된 제스처에 따라 키 입력 처리 (활성화 상태인 경우에만)
            if active:
                self.apply_gesture_controls(detected_gestures)
        
        # 화면 표시 업데이트
        self.update_display(main_img, hand_detection, state_text)
        
        # FPS 계산
        fps = 1 / (self.cur_time - self.prev_time)
        self.prev_time = self.cur_time
        cv2.putText(main_img, f'FPS: {int(fps)}', (40, 40), self.font_type, self.font_size, (90, 140, 185), self.font_thickness)
        
        return main_img, self.quit_confirmed
    def process_hand_gestures(self, lm_list, main_img):
        """손 제스처 처리"""
        # 손가락 상태 인식
        self.finger_up_state = self.hand_detector.fingersUp()
        detected_gestures = []
        state = ""
        
        # 각 손가락 위치 추출
        index_pos = lm_list[8][1:]
        middle_pos = lm_list[12][1:]
        pinky_pos = lm_list[20][1:]
        thumb_pos = lm_list[4][1:]
        
        # 손가락이 인식된 경우
        if self.finger_up_state.size != 0:
            index_finger_in_detection = self.check_in_area(index_pos)
            middle_finger_in_detection = self.check_in_area(middle_pos)
            
            # 컨트롤러 모드 전환 확인
            if index_finger_in_detection or middle_finger_in_detection:
                index_button_area = self.check_in_area(index_pos, 2)
                middle_button_area = self.check_in_area(middle_pos, 2)
                
                if index_button_area == middle_button_area:
                    z = 0
                    [dis, centre] = self.hand_detector.findDistance(main_img, 1, 2)
                    if centre and dis:
                        self.clicked = self.mouse_pointer_click(centre, dis, self.clicked, main_img)
                        if self.clicked == 2:
                            z = 1
                    
                    if index_button_area == 1 and z == 1:
                        state += " 마우스 모드"
                        self.controller_mode = 0
                    elif index_button_area == 2 and z == 1:
                        state += " 키보드 모드"
                        self.controller_mode = 1
            else:
                # 손가락 상태 분석
                [self.thumb, self.index_finger, self.middle_finger, self.ring_finger, self.pinky_finger] = self.finger_up_state
                sum_fingers = sum(self.finger_up_state[1:])
                
                # 손가락별 영역 확인
                thumb_in_gesture_area = self.check_in_area(thumb_pos, 1)
                index_in_gesture_area = self.check_in_area(index_pos, 1)
                middle_in_gesture_area = self.check_in_area(middle_pos, 1)
                pinky_in_gesture_area = self.check_in_area(pinky_pos, 1)
                
                # 종료 버튼 확인
                index_in_quit = self.check_in_area(index_pos, 3)
                middle_in_quit = self.check_in_area(middle_pos, 3)
                
                # 점프 제스처 확인
                if sum_fingers == 0 and thumb_in_gesture_area and not self.thumb:
                    state += "Jump "
                    self.jump = 1
                    detected_gestures.append('jump')
                else:
                    # 방향 제어 제스처 확인
                    if self.index_finger and index_in_gesture_area:
                        if not self.middle_finger:
                            state += "Up "
                            self.v_dir = 1
                            detected_gestures.append('up')
                        elif middle_in_gesture_area and self.middle_finger and not self.ring_finger:
                            state += "Down "
                            self.v_dir = -1
                            detected_gestures.append('down')
                    
                    if self.thumb and thumb_in_gesture_area and not self.pinky_finger:
                        state += "Left "
                        self.h_dir = -1
                        detected_gestures.append('left')
                    elif self.pinky_finger and pinky_in_gesture_area and not self.thumb:
                        state += "Right "
                        self.h_dir = 1
                        detected_gestures.append('right')
                
                # 컨트롤러 모드별 처리
                if self.controller_mode == 0:  # 마우스 모드
                    if self.v_dir == 1:
                        # 마우스 이동
                        px, py = lm_list[8][1:]
                        self.pointer_x = int(interp(px, (self.hand_start_x, self.end_x), (0, self.screen_width)))
                        self.pointer_y = int(interp(py, (self.hand_start_y, self.end_y), (0, self.screen_height)))
                        state = "Mouse Pointer"
                        cv2.circle(main_img, (px, py), 5, (200, 200, 200), cv2.FILLED)
                        cv2.circle(main_img, (px, py), 10, (200, 200, 200), 3)
                        self.mouse.position = (int(self.pointer_x), int(self.pointer_y))
                    else:
                        # 클릭 처리
                        [dis, centre] = self.hand_detector.findDistance(main_img, 1, 2)
                        
                        if index_in_quit and middle_in_quit and sum_fingers <= 3:
                            state = "Quit Check"
                            if centre and dis:
                                self.clicked = self.mouse_pointer_click(centre, dis, self.clicked, main_img)
                                if self.clicked == 2:
                                    self.quit_confirmed = True
                        
                        if self.v_dir == -1 and (centre and dis):
                            state = "Click mouse"
                            self.clicked = self.mouse_pointer_click(centre, dis, self.clicked, main_img)
                            if self.clicked == 2:
                                if self.clk == 0:
                                    self.mouse.position = (int(self.pointer_x), int(self.pointer_y))
                                    self.mouse.click(Button.left)   
                                    self.clk += 1
                                else:
                                    self.clk -= 1
        
        return state, detected_gestures
    
    def apply_gesture_controls(self, detected_gestures):
        """인식된 제스처에 대한 컨트롤 적용"""
        if self.controller_mode == 1:  # 키보드 모드
            # 가로 방향키 처리
            key_map = {
                Key.up: 'up',
                Key.down: 'down',
                Key.left: 'left',
                Key.right: 'right',
                Key.space: 'space',
            }
            
            # DirectInput 방식으로 키 처리
            if self.h_dir == 1:  # 오른쪽
                key = self.get_gesture_mapping('right')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyDown(key_str)
            elif self.h_dir == -1:  # 왼쪽
                key = self.get_gesture_mapping('left')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyDown(key_str)
            else:
                key = self.get_gesture_mapping('right')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyUp(key_str)
                key = self.get_gesture_mapping('left')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyUp(key_str)
            
            # 세로 방향키 처리
            if self.v_dir == 1:  # 위
                key = self.get_gesture_mapping('up')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyDown(key_str)
            elif self.v_dir == -1:  # 아래
                key = self.get_gesture_mapping('down')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyDown(key_str)
            else:
                key = self.get_gesture_mapping('up')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyUp(key_str)
                key = self.get_gesture_mapping('down')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyUp(key_str)
                
            # 점프 처리
            if self.jump == 1:
                key = self.get_gesture_mapping('jump')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyDown(key_str)
            else:
                key = self.get_gesture_mapping('jump')
                key_str = key_map.get(key, str(key))
                pydirectinput.keyUp(key_str)
    
    def update_display(self, main_img, hand_detection, state):
        """화면 표시 업데이트"""
        # 모드 버튼 텍스트
        cv2.putText(main_img, 'MOUSE', (self.start_x + 60, self.start_y + 30), self.font_type, self.font_size, self.font_color, 2)
        cv2.putText(main_img, 'ARROW', (self.mid_x + 60, self.start_y + 30), self.font_type, self.font_size, self.font_color, 2)
        
        # 영역 그리기
        cv2.line(main_img, (self.mid_x, self.start_y), (self.mid_x, self.hand_start_y), (10, 10, 250), 2)            
        cv2.rectangle(main_img, (self.start_x, self.start_y), (self.end_x, self.end_y), (10, 10, 250), 2)
        cv2.rectangle(main_img, (self.hand_start_x, self.hand_start_y), (self.hand_end_x, self.hand_end_y), (10, 10, 250), 2)
        
        # 상태 정보
        cv2.putText(main_img, f'DETECTION: {hand_detection}', (40, 20), self.font_type, self.font_size, self.font_color, self.font_thickness)
        cv2.putText(main_img, f'STATE: {state}', (250, 20), self.font_type, self.font_size, self.font_color, self.font_thickness)
        
        # 종료 버튼
        cv2.putText(main_img, 'QUIT', (self.start_x-65, self.start_y + 30), self.font_type, self.font_size, self.font_color, 2)
        cv2.rectangle(main_img, (self.start_x-100, self.start_y), (self.start_x, self.hand_start_y), (10, 10, 250), 2)
        
        # 컨트롤러 타입
        controller_type = "Mouse" if self.controller_mode == 0 else 'Arrow'
        cv2.putText(main_img, f"CONTROL TYPE: {controller_type}", (250, 40), self.font_type, self.font_size, self.font_color, self.font_thickness)
    
    def release_all_keys(self):
        """모든 키 해제"""
        for key in self.gesture_mappings.values():
            try:
                self.keyboard.release(key)
            except:
                pass
    
    def close(self):
        """프로그램 종료 작업"""
        self.release_all_keys()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        self.say("프로그램 종료")
