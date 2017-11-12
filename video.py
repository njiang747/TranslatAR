import numpy as np
import cv2
from AppKit import NSScreen

screenwidth = int(NSScreen.mainScreen().frame().size.width)
screenheight = int(NSScreen.mainScreen().frame().size.height)

print(screenwidth, screenheight)

left = cv2.VideoCapture(0)
right = cv2.VideoCapture(2)

while True:
    _, left_img = left.read()
    _, right_img = right.read()

    height, width, _ = left_img.shape
    scaledheight = screenheight
    scaledwidth = int(width * screenheight / height)

    left_img = cv2.resize(left_img, (scaledwidth, scaledheight))
    right_img = cv2.resize(right_img, (scaledwidth, scaledheight))

    cutoff = int(scaledwidth / 2 - screenwidth / 4)

    comb = np.concatenate((left_img[:, cutoff:-cutoff, :], right_img[:, cutoff:-cutoff, :]), axis=1)

    cv2.putText(comb, "Hello World!!!", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, 255)

    cv2.imshow("dongLe", comb)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
