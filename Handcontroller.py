import cv2
import mediapipe as mp
import numpy as np

class Hand_Controller:
    def __init__(self):
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.mpDraw = mp.solutions.drawing_utils
        self.fingertips = [4, 8, 12, 16, 20]
        self.lmlist = []
        self.fingers_up_status = np.array([])

    def findhand(self, frame, draw=True):
        """손을 감지하고 필요한 경우 손의 랜드마크를 그림"""
        imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        
        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(frame, handLms, self.mpHands.HAND_CONNECTIONS)
        return frame

    def findPosition(self, draw=False):
        """손의 랜드마크 위치 찾기"""
        self.lmlist = []
        if self.results.multi_hand_landmarks:
            hand = self.results.multi_hand_landmarks[0]
            for id, lm in enumerate(hand.landmark):
                h, w, c = 720, 960, 3  # 이미지 높이, 너비 기본값
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lmlist.append([id, cx, cy])
        return self.lmlist

    def fingersUp(self):
        """손가락이 펴져 있는지 확인"""
        fingers = []
        if len(self.lmlist) != 0:
            # 엄지
            if self.lmlist[self.fingertips[0]][1] < self.lmlist[self.fingertips[0]-1][1]:
                fingers.append(1)
            else:
                fingers.append(0)

            # 다른 손가락들 - 임계값 조정으로 더 정확한 감지
            for id in range(1, 5):
                # 손가락 끝이 관절보다 더 위에 있으면 펴진 상태(1), 그렇지 않으면 굽힘 상태(0)
                # 임계값을 약간 조정하여 더 명확하게 구분
                threshold = 10  # 픽셀 단위 임계값
                if self.lmlist[self.fingertips[id]][2] < self.lmlist[self.fingertips[id]-2][2] - threshold:
                    fingers.append(1)
                else:
                    fingers.append(0)
            
            return np.array(fingers)
        return np.array([])

    def findDistance(self, img, p1, p2, draw=True):
        """두 손가락 사이의 거리 계산"""
        if len(self.lmlist) >= max(p1, p2) + 1:
            x1, y1 = self.lmlist[p1*4][1:] if p1 < 5 else self.lmlist[p1][1:]
            x2, y2 = self.lmlist[p2*4][1:] if p2 < 5 else self.lmlist[p2][1:]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            if draw:
                cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                cv2.circle(img, (cx, cy), 10, (255, 0, 255), cv2.FILLED)
            
            length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            return [length, (cx, cy)]
        return [None, None]
