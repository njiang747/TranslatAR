import numpy as np
import cv2


right = cv2.VideoCapture(2)
left = cv2.VideoCapture(0)

while True:
    ret, left_img = left.read()
    ret, right_img = right.read()

    width, height, _ = left_img.shape
    scale = 1
    left_img = cv2.resize(left_img, (int(height/scale), int(width/scale)))
    right_img = cv2.resize(right_img, (int(height/scale), int(width/scale)))

    comb = np.concatenate((left_img, right_img),axis=1)
    cv2.imshow("dongLe",comb)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
