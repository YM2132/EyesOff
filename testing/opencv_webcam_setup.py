import cv2 as cv
import numpy as np

cap = cv.VideoCapture(0)

if not cap.isOpened():
	print("Cannot Open Camera")
	exit()

while True:
	# Capture frame-by-frame
	ret, frame = cap.read()

	# if frame is read correctly then ret==True
	if not ret:
		print("Can't receive frame. Exiting ...")
		break
	# The following is where I can modify the frame
	gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
	# Display the frame
	cv.imshow('frame', gray)
	if cv.waitKey(1) == ord('q'):
		break

cap.release()
cv.destroyAllWindows()