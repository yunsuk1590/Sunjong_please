import sys
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QComboBox, 
                            QGroupBox, QFormLayout, QAction, QMenu, QDialog,
                            QSizePolicy)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon
from VirtualGameController import VirtualGameController
from pynput.keyboard import Key
import numpy as np

# 다크 모드 색상 테마 정의
DARK_BG = "#1e1e1e"         # 배경색 (짙은 진한 회색)
DARK_BG_LIGHT = "#2d2d30"   # 약간 밝은 배경색 (위젯 배경)
DARK_TEXT = "#ffffff"       # 텍스트 색상 (흰색)
DARK_TEXT_MUTED = "#b0b0b0" # 흐릿한 텍스트 색상 (연한 회색)
DARK_ACCENT = "#569cd6"     # 강조색 (부드러운 파란색)
DARK_ACCENT_ALT = "#c586c0" # 대체 강조색 (연한 보라색)
DARK_BORDER = "#444444"     # 테두리 색상
DARK_SUCCESS = "#4ec9b0"    # 성공 색상 (청록색)
DARK_WARNING = "#d7ba7d"    # 경고 색상 (황금색)
DARK_DANGER = "#ce9178"     # 위험/중지 색상 (연한 주황색)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("키 매핑 설정")
        self.setModal(True)
        self.initUI()
        self.resize(500, 400)  # 넉넉한 크기의 설정창
        
        # 다크모드 배경 적용
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {DARK_TEXT};")
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 사용 설명 추가 (기존 코드 유지)
        info_label = QLabel("각 제스처에 매핑할 키를 선택하세요. 설정은 즉시 적용됩니다.")
        info_label.setStyleSheet(f"font-size: 24px; color: {DARK_TEXT_MUTED}; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 설정 그룹박스 (기존 코드 유지)
        self.settings_group = QGroupBox("제스처 키 매핑 설정")
        self.settings_group.setStyleSheet(f"font-size: 24px; color: {DARK_TEXT}; border: 1px solid {DARK_BORDER}; border-radius: 8px;")  
        self.settings_layout = QFormLayout()
        self.settings_layout.setVerticalSpacing(30)  # 간격 넓히기
        
        # 제스처별 키 매핑 드롭다운 (기존 코드 유지)
        self.jump_combo = QComboBox()
        self.up_combo = QComboBox()
        self.down_combo = QComboBox()
        self.left_combo = QComboBox()
        self.right_combo = QComboBox()
        
        # 콤보박스 스타일 및 크기 설정 (기존 코드 유지)
        combo_style = f"""
            font-size: 25px;  # 일관성을 위해 22px로 통일
            background-color: {DARK_BG_LIGHT};
            color: {DARK_TEXT};
            border: 1px solid {DARK_BORDER};
            border-radius: 8px;
            padding: 10px;  # 일관성을 위해 패딩 10px로 통일
        """
        
        for combo in [self.jump_combo, self.up_combo, self.down_combo, 
                    self.left_combo, self.right_combo]:
            combo.setMinimumHeight(60)
            combo.setStyleSheet(combo_style)
        
        # 현재 매핑 표시 레이블 추가 (새로운 코드)
        self.jump_current = QLabel()
        self.up_current = QLabel()
        self.down_current = QLabel()
        self.left_current = QLabel()
        self.right_current = QLabel()
        
        # 현재 매핑 레이블 스타일 설정 (새로운 코드)
        for label in [self.jump_current, self.up_current, self.down_current, 
                    self.left_current, self.right_current]:
            label.setStyleSheet(f"color: {DARK_ACCENT}; font-size: 22px; padding-left: 12px;")
        
        # 드롭다운에 키 옵션 추가 (기존 코드 유지)
        for combo in [self.jump_combo, self.up_combo, self.down_combo, 
                    self.left_combo, self.right_combo]:
            for key_name in self.parent.key_options.keys():
                combo.addItem(key_name)
        
        # SettingsDialog의 초기화에서 매핑 가져오는 부분 수정
        # 기존 코드 (오류 발생)
        current_mappings = self.parent.controller.gesture_mappings

        # 수정된 코드
        current_mappings = {
            'jump': self.parent.controller.get_gesture_mapping('jump'),
            'up': self.parent.controller.get_gesture_mapping('up'),
            'down': self.parent.controller.get_gesture_mapping('down'),
            'left': self.parent.controller.get_gesture_mapping('left'),
            'right': self.parent.controller.get_gesture_mapping('right')
        }

        key_names = {v: k for k, v in self.parent.key_options.items()}
        
        def get_key_name(key):
            if key in key_names.keys():
                return key_names[key]
            return str(key).replace('Key.', '')
        
        # 콤보박스 현재 값 설정 (기존 코드 유지)
        self.jump_combo.setCurrentText(get_key_name(current_mappings['jump']))
        self.up_combo.setCurrentText(get_key_name(current_mappings['up']))
        self.down_combo.setCurrentText(get_key_name(current_mappings['down']))
        self.left_combo.setCurrentText(get_key_name(current_mappings['left']))
        self.right_combo.setCurrentText(get_key_name(current_mappings['right']))
        
        # 현재 매핑 레이블 값 설정 (새로운 코드)
        self.jump_current.setText(f"현재: {get_key_name(current_mappings['jump'])}")
        self.up_current.setText(f"현재: {get_key_name(current_mappings['up'])}")
        self.down_current.setText(f"현재: {get_key_name(current_mappings['down'])}")
        self.left_current.setText(f"현재: {get_key_name(current_mappings['left'])}")
        self.right_current.setText(f"현재: {get_key_name(current_mappings['right'])}")
        
        # 콤보박스 이벤트 연결 (기존 코드 유지)
        self.jump_combo.currentTextChanged.connect(lambda: self.update_mapping('jump'))
        self.up_combo.currentTextChanged.connect(lambda: self.update_mapping('up'))
        self.down_combo.currentTextChanged.connect(lambda: self.update_mapping('down'))
        self.left_combo.currentTextChanged.connect(lambda: self.update_mapping('left'))
        self.right_combo.currentTextChanged.connect(lambda: self.update_mapping('right'))
        
        # 제스처 설명 레이블 추가
        jump_desc = QLabel("모든 손가락을 구부리면(주먹) 점프합니다.")
        up_desc = QLabel("중지 손가락만 구부리면 위로 이동합니다.")
        down_desc = QLabel("약지 손가락만 구부리면 아래로 이동합니다.")
        left_desc = QLabel("소지(새끼) 손가락만 구부리면 왼쪽으로 이동합니다.")
        right_desc = QLabel("엄지 손가락만 구부리면 오른쪽으로 이동합니다.")
        
        # 설명 스타일 지정 (기존 코드 유지)
        for label in [jump_desc, up_desc, down_desc, left_desc, right_desc]:
            label.setStyleSheet(f"color: {DARK_TEXT_MUTED}; font-style: italic; font-size: 22px;")
        
        # 레이아웃 수정: 콤보박스 + 현재값 표시 (새로운 코드)
        for gesture, combo, current, desc in [
            ("점프", self.jump_combo, self.jump_current, jump_desc),
            ("위로", self.up_combo, self.up_current, up_desc),
            ("아래로", self.down_combo, self.down_current, down_desc),
            ("왼쪽", self.left_combo, self.left_current, left_desc),
            ("오른쪽", self.right_combo, self.right_current, right_desc)
        ]:
            # 콤보박스와 현재 레이블을 포함할 수평 레이아웃
            combo_layout = QHBoxLayout()
            combo_layout.addWidget(combo)
            combo_layout.addWidget(current)
            combo_layout.setStretch(0, 2)  # 콤보박스가 더 넓게
            combo_layout.setStretch(1, 1)  # 현재 레이블은 좁게
            
            # 폼 레이아웃에 추가
            self.settings_layout.addRow(QLabel(f'<span style="color: {DARK_TEXT}; font-size: 24px;">{gesture}:</span>'), combo_layout)
            self.settings_layout.addRow("", desc)
        
        self.settings_group.setLayout(self.settings_layout)
        
        # 확인 버튼 (기존 코드 유지)
        close_button = QPushButton("닫기")
        close_button.setMinimumHeight(80)
        close_button.setStyleSheet(f"""
            font-size: 22px; 
            background-color: {DARK_ACCENT}; 
            color: {DARK_TEXT}; 
            border-radius: 8px;
            padding: 10px;
        """)
        close_button.clicked.connect(self.close)
        
        layout.addWidget(self.settings_group)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def update_mapping(self, gesture):
        """제스처에 대한 키 매핑 업데이트"""
        combo_map = {
            'jump': self.jump_combo,
            'up': self.up_combo,
            'down': self.down_combo,
            'left': self.left_combo,
            'right': self.right_combo
        }
        
        selected_key = combo_map[gesture].currentText()
        key_value = self.parent.key_options[selected_key]
        
        # 컨트롤러에 매핑 설정
        self.parent.controller.set_gesture_mapping(gesture, key_value)
        
        # 부모 창의 매핑 표시 업데이트
        self.parent.update_key_mapping_display()

class GameControllerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 키매핑 사전 (먼저 정의)
        self.key_options = {
            'space': Key.space,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'enter': Key.enter,
            'esc': Key.esc,
            'tab': Key.tab,
            'a': 'a',
            'b': 'b',
            'c': 'c',
            'd': 'd',
            'e': 'e',
            'f': 'f',
            'g': 'g',
            'w': 'w',
            's': 's',
            'd': 'd',
            'z': 'z',
            'x': 'x',
            '1': '1',
            '2': '2',
            '3': '3',
            '4': '4'
        }
        
        # 창 속성 변경 - 항상 위에 표시
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # 가상 게임 컨트롤러 생성
        self.controller = VirtualGameController()
        
        # 컨트롤러 활성화 상태 설정 (기본값: 비활성화)
        self.controller_active = False
        self.compact_mode = False
        
        # UI 초기화
        self.initUI()
        
        # 타이머 설정 (영상 프레임 처리)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms 마다 프레임 업데이트
        
        # 상태 메시지 초기화
        self.status_msg.setText("상태: 준비됨")
        
        # 현재 키 매핑 설정
        self.update_key_mapping_display()

    def initUI(self):
        # 다크 모드 배경 적용
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {DARK_TEXT};")
        
        # 메뉴바 설정
        self.setup_menu()
        
        # 메뉴바 폰트 크기 설정
        menubar = self.menuBar()
        menubar.setStyleSheet(f"font-size: 30px; background-color: {DARK_BG_LIGHT}; color: {DARK_TEXT}; border: none;")  
        
        # 메인 위젯 및 레이아웃 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(20)  # 레이아웃 간격 확대
        
        # 카메라 화면 영역
        self.video_layout = QVBoxLayout()
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(QSize(960, 720))  # 카메라 화면 크기 2배 확대
        self.video_label.setStyleSheet(f"background-color: {DARK_BG_LIGHT}; border: 1px solid {DARK_BORDER}; border-radius: 10px;")
        self.video_layout.addWidget(self.video_label)
        
        # 사용 안내 메시지 추가
        self.instruction_label = QLabel("손을 카메라 앞에서 움직여 보세요! 시작 버튼을 누르면 게임 제어가 시작됩니다.")
        self.instruction_label.setStyleSheet(f"font-size: 28px; color: {DARK_TEXT_MUTED};")  # 글자 크기 확대
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.video_layout.addWidget(self.instruction_label)
        
        # 상태 표시 영역
        self.status_msg = QLabel("상태: 준비됨")
        self.status_msg.setStyleSheet(f"font-weight: bold; color: {DARK_ACCENT}; font-size: 24px;")  # 글자 크기 확대
        self.video_layout.addWidget(self.status_msg)
        
        # 키 매핑 표시 영역
        self.mapping_group = QGroupBox("현재 키 매핑")
        self.mapping_group.setStyleSheet(f"""
            font-size: 24px; 
            color: {DARK_TEXT}; 
            background-color: {DARK_BG_LIGHT}; 
            border: 1px solid {DARK_BORDER}; 
            border-radius: 8px;
        """)  
        self.mapping_layout = QHBoxLayout()
        self.mapping_layout.setSpacing(15)  # 간격 확대
        
        self.jump_label = QLabel("점프: Space")
        self.up_label = QLabel("위: Up")
        self.down_label = QLabel("아래: Down")
        self.left_label = QLabel("왼쪽: Left")
        self.right_label = QLabel("오른쪽: Right")
        
        # 각 레이블 스타일 적용
        label_style = f"padding: 10px; background-color: {DARK_BG_LIGHT}; border: 1px solid {DARK_BORDER}; border-radius: 8px; font-size: 22px; color: {DARK_ACCENT};"
        for label in [self.jump_label, self.up_label, self.down_label, self.left_label, self.right_label]:
            label.setStyleSheet(label_style)  # 글자 크기 및 패딩 확대
        
        self.mapping_layout.addWidget(self.jump_label)
        self.mapping_layout.addWidget(self.up_label)
        self.mapping_layout.addWidget(self.down_label)
        self.mapping_layout.addWidget(self.left_label)
        self.mapping_layout.addWidget(self.right_label)
        
        self.mapping_group.setLayout(self.mapping_layout)
        
        # 컨트롤 버튼
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(20)  # 버튼 간격 확대
        
        self.start_button = QPushButton("시작")
        self.start_button.setStyleSheet(f"""
            background-color: {DARK_SUCCESS}; 
            color: {DARK_TEXT}; 
            font-size: 32px; 
            padding: 16px 32px;
            border-radius: 10px;
        """)
        self.start_button.setMinimumHeight(80)  # 버튼 높이 확대
        self.start_button.clicked.connect(self.start_controller)
        
        self.stop_button = QPushButton("정지")
        self.stop_button.setStyleSheet(f"""
            background-color: {DARK_DANGER}; 
            color: {DARK_TEXT}; 
            font-size: 32px; 
            padding: 16px 32px;
            border-radius: 10px;
        """)
        self.stop_button.setMinimumHeight(80)  # 버튼 높이 확대
        self.stop_button.clicked.connect(self.stop_controller)
        self.stop_button.setEnabled(False)
        
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        
        # 메인 레이아웃에 컴포넌트 추가
        self.main_layout.addLayout(self.video_layout)
        self.main_layout.addWidget(self.mapping_group)
        self.main_layout.addLayout(self.button_layout)
        
        # 윈도우 설정
        self.setWindowTitle('가상 게임 컨트롤러')
        self.resize(1200, 900)  # 창 크기 2배 확대
        self.show()
    
    def setup_menu(self):
        # 메뉴바 생성
        menubar = self.menuBar()
        
        # 설정 메뉴
        settings_menu = menubar.addMenu('설정')
        
        # 키 매핑 설정 액션
        key_mapping_action = QAction('키 매핑 설정', self)
        key_mapping_action.triggered.connect(self.show_key_mapping_dialog)
        settings_menu.addAction(key_mapping_action)
        
        # 항상 위에 표시 토글 액션
        self.always_on_top_action = QAction('항상 위에 표시', self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setChecked(True)
        self.always_on_top_action.triggered.connect(self.toggle_always_on_top)
        settings_menu.addAction(self.always_on_top_action)
    
    def show_key_mapping_dialog(self):
        """키 매핑 설정 다이얼로그 표시"""
        dialog = SettingsDialog(self)
        dialog.exec_()
        
    def toggle_always_on_top(self, checked):
        """항상 위에 표시 설정 토글"""
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()  # 플래그 변경 후 창을 다시 표시해야 함
    
    def toggle_compact_mode(self, enable_compact=True):
        """컴팩트 모드 전환"""
        self.compact_mode = enable_compact
        
        if enable_compact:
            # 컴팩트 모드에서 불필요한 요소 숨기기
            self.mapping_group.hide()  # 키 매핑 그룹 숨기기
            self.instruction_label.hide()
            
            # 비디오 레이블만 표시 (최소/최대 크기 조정)
            self.video_label.setMinimumSize(QSize(320, 240))
            self.video_label.setMaximumSize(QSize(400, 300))
            
            # 레이아웃 여백 줄이기
            self.main_layout.setContentsMargins(5, 5, 5, 5)
            self.main_layout.setSpacing(5)
            self.video_layout.setSpacing(5)
            
            # 상태 메시지 폰트 크기 줄이기
            self.status_msg.setStyleSheet(f"font-weight: bold; color: {DARK_ACCENT}; font-size: 25px;")
            
            # 버튼 크기 조정
            for button in [self.start_button, self.stop_button]:
                button.setMinimumHeight(40)
                button.setStyleSheet(button.styleSheet().replace("font-size: 32px", "font-size: 25px"))
            
            # 창 크기 설정 (레이아웃 요소 숨긴 후 적용)
            QTimer.singleShot(100, lambda: self.resize(400, 400))
            self.setWindowTitle('가상 게임 컨트롤러 [실행 중]')
                
        else:
            # 일반 모드 - 숨긴 요소 다시 표시
            self.mapping_group.show()
            self.instruction_label.show()
            
            # 레이아웃 여백 복원
            self.main_layout.setContentsMargins(11, 11, 11, 11)
            self.main_layout.setSpacing(20)
            self.video_layout.setSpacing(10)
            
            # 비디오 레이블 크기 복원
            self.video_label.setMinimumSize(QSize(960, 720))
            self.video_label.setMaximumSize(QSize(16777215, 16777215))
            
            # 상태 메시지 폰트 크기 복원
            self.status_msg.setStyleSheet(f"font-weight: bold; color: {DARK_ACCENT}; font-size: 30px;")
            
            # 버튼 크기 복원
            for button in [self.start_button, self.stop_button]:
                button.setMinimumHeight(80)
                button.setStyleSheet(button.styleSheet().replace("font-size: 16px", "font-size: 32px"))
            
            # 창 크기 복원
            self.resize(1200, 900)
            self.setWindowTitle('가상 게임 컨트롤러')
    
    def update_mapping(self, gesture):
        """제스처에 대한 키 매핑 업데이트"""
        combo_map = {
            'jump': self.jump_combo,
            'up': self.up_combo,
            'down': self.down_combo,
            'left': self.left_combo,
            'right': self.right_combo
        }
        
        selected_key = combo_map[gesture].currentText()
        key_value = self.key_options[selected_key]
        
        # 컨트롤러에 매핑 설정
        self.controller.set_gesture_mapping(gesture, key_value)
        
        # 매핑 표시 업데이트
        self.update_key_mapping_display()
        
        self.status_msg.setText(f"상태: {gesture} 제스처가 {selected_key} 키로 매핑됨")
    
    def update_key_mapping_display(self):
        """현재 키 매핑 표시 업데이트"""
        # 컨트롤러 현재 매핑 - 잘못된 코드
        mapping = self.controller.get_gesture_mapping
        
        # 올바른 코드로 수정
        mapping = {
            'jump': self.controller.get_gesture_mapping('jump'),
            'up': self.controller.get_gesture_mapping('up'),
            'down': self.controller.get_gesture_mapping('down'),
            'left': self.controller.get_gesture_mapping('left'),
            'right': self.controller.get_gesture_mapping('right')
        }
        
        # 매핑 표시 업데이트
        key_names = {v: k for k, v in self.key_options.items()}
        
        def get_key_name(key):
            if key in key_names.keys():
                return key_names[key]
            return str(key).replace('Key.', '')
        
        self.jump_label.setText(f"점프: {get_key_name(mapping['jump'])}")
        self.up_label.setText(f"위: {get_key_name(mapping['up'])}")
        self.down_label.setText(f"아래: {get_key_name(mapping['down'])}")
        self.left_label.setText(f"왼쪽: {get_key_name(mapping['left'])}")
        self.right_label.setText(f"오른쪽: {get_key_name(mapping['right'])}")
    
    @pyqtSlot()
    def update_frame(self):
        """카메라 프레임 업데이트 및 처리"""
        try:
            # 프레임 처리 (컨트롤러 활성화 여부 전달)
            frame, quit_flag = self.controller.process_frame(self.controller_active)
            
            if frame is None or quit_flag:
                self.stop_controller()
                return
            
            # 디버그 정보 표시 - 숫자 대신 텍스트로 현재 인식된 제스처 표시
            if self.controller_active:
                # 모드 표시 부분 삭제 (키보드만 사용하므로)
                
                # 제스처 상태 텍스트로 변환
                gestures = []
                if self.controller.jump == 1:
                    gestures.append("점프")
                if self.controller.v_dir == 1:
                    gestures.append("위로")
                elif self.controller.v_dir == -1:
                    gestures.append("아래로")
                if self.controller.h_dir == -1:
                    gestures.append("왼쪽")
                elif self.controller.h_dir == 1:
                    gestures.append("오른쪽")
                    
                gesture_text = ", ".join(gestures) if gestures else "없음"
                self.status_msg.setText(f"상태: 실행중 | 제스처: {gesture_text}")
            
            # OpenCV 프레임을 QImage로 변환
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            convert_to_qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(convert_to_qt_format)
            
            # QLabel에 표시
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.width(), 
                self.video_label.height(), 
                Qt.KeepAspectRatio
            ))
            
        except Exception as e:
            self.status_msg.setText(f"오류: {str(e)}")
            self.stop_controller()
    
    def start_controller(self):
        """컨트롤러 시작"""
        self.controller_active = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_msg.setText("상태: 컨트롤러 실행 중")
        self.status_msg.setStyleSheet("font-weight: bold; color: #007bff; font-size: 24px;")
        
        # 컴팩트 모드로 전환
        self.toggle_compact_mode(True)
        
        # 알림 메시지 표시
        self.status_msg.setText("컨트롤러가 활성화되었습니다. 제어하려는 게임을 클릭하세요.")
        QTimer.singleShot(3000, lambda: self.status_msg.setText("상태: 실행 중"))
    
    def stop_controller(self):
        """컨트롤러 정지"""
        self.controller_active = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_msg.setText("상태: 컨트롤러 정지됨")
        
        # 일반 모드로 복원
        self.toggle_compact_mode(False)
        
        # 모든 키 해제
        self.controller.release_all_keys()    
    def closeEvent(self, event):
        """앱 종료 시 처리"""
        self.controller.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameControllerGUI()
    sys.exit(app.exec_())
