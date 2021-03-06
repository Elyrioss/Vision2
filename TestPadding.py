# USAGE
# python TestRecoText.py --image images/11.png --east frozen_east_text_detection.pb
from imutils.object_detection import non_max_suppression
from googletrans import Translator
import numpy as np
import argparse
import time
import pytesseract
import cv2


font                   = cv2.FONT_HERSHEY_SIMPLEX
fontScale              = 1
fontColor              = (0,0,0)
lineType               = 1

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", type=str,
	help="path to input image")
ap.add_argument("-east", "--east", type=str,
	help="path to input EAST text detector")
ap.add_argument("-c", "--min-confidence", type=float, default=0.5,
	help="minimum probability required to inspect a region")
ap.add_argument("-w", "--width", type=int, default=320,
	help="resized image width (should be multiple of 32)")
ap.add_argument("-e", "--height", type=int, default=320,
	help="resized image height (should be multiple of 32)")
ap.add_argument("-p", "--padding", type=int, default=200,
	help="amount of padding to add to each border of ROI")
args = vars(ap.parse_args())


pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
translator = Translator()

image = cv2.imread(args["image"])
orig = image.copy()
(H, W) = image.shape[:2]

(newW, newH) = (args["width"], args["height"])
rW = W / float(newW)
rH = H / float(newH)

image = cv2.resize(image, (newW, newH))
(H, W) = image.shape[:2]

layerNames = [
	"feature_fusion/Conv_7/Sigmoid",
	"feature_fusion/concat_3"]

print("[INFO] loading EAST text detector...")
net = cv2.dnn.readNet(args["east"])


blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
	(123.68, 116.78, 103.94), swapRB=True, crop=False)
start = time.time()
net.setInput(blob)
(scores, geometry) = net.forward(layerNames)
end = time.time()

# show timing information on text prediction
print("[INFO] text detection took {:.6f} seconds".format(end - start))

# grab the number of rows and columns from the scores volume, then
# initialize our set of bounding box rectangles and corresponding
# confidence scores
(numRows, numCols) = scores.shape[2:4]
rects = []
confidences = []

# loop over the number of rows
for y in range(0, numRows):
	# extract the scores (probabilities), followed by the geometrical
	# data used to derive potential bounding box coordinates that
	# surround text
	scoresData = scores[0, 0, y]
	xData0 = geometry[0, 0, y]
	xData1 = geometry[0, 1, y]
	xData2 = geometry[0, 2, y]
	xData3 = geometry[0, 3, y]
	anglesData = geometry[0, 4, y]

	# loop over the number of columns
	for x in range(0, numCols):
		# if our score does not have sufficient probability, ignore it
		if scoresData[x] < args["min_confidence"]:
			continue

		# compute the offset factor as our resulting feature maps will
		# be 4x smaller than the input image
		(offsetX, offsetY) = (x * 4.0, y * 4.0)

		# extract the rotation angle for the prediction and then
		# compute the sin and cosine
		angle = anglesData[x]
		cos = np.cos(angle)
		sin = np.sin(angle)

		# use the geometry volume to derive the width and height of
		# the bounding box
		h = xData0[x] + xData2[x]
		w = xData1[x] + xData3[x]

		# compute both the starting and ending (x, y)-coordinates for
		# the text prediction bounding box
		endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
		endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
		startX = int(endX - w)
		startY = int(endY - h)

		# add the bounding box coordinates and probability score to
		# our respective lists
		rects.append((startX, startY, endX, endY))
		confidences.append(scoresData[x])

# apply non-maxima suppression to suppress weak, overlapping bounding
# boxes
boxes = non_max_suppression(np.array(rects), probs=confidences)




# loop over the bounding boxes
i = 0
ListCrop = []
ListCoord = [[]]
for (startX, startY, endX, endY) in boxes:
	textfr = ""
	# scale the bounding box coordinates based on the respective
	# ratios
	startX = int(startX * rW)
	startY = int(startY * rH)
	endX = int(endX * rW)
	endY = int(endY * rH)
	# draw the bounding box on the image
	#verif
	if len(ListCrop)!=0 :

		for j in range(0,len(ListCrop)-1) :
			if startX > ListCoord[j][1] or endX <  ListCoord[j][0] :
					break
			if startY > ListCoord[j][3] or endY <  ListCoord[j][2] :
					break
			rec = orig[startY - args["padding"] :endY + args["padding"],startX - args["padding"]:endX + args["padding"]]
			ListCrop.append(rec)
			ListCoord.append([])
			ListCoord[len(ListCoord)-1].append(startX - args["padding"])
			ListCoord[len(ListCoord)-1].append(endX + args["padding"])
			ListCoord[len(ListCoord)-1].append(startY -args["padding"])
			ListCoord[len(ListCoord)-1].append(endY + args["padding"])
			cv2.imshow(str(i), rec)
			cv2.rectangle(orig, (startX - args["padding"], startY -args["padding"]), (endX + args["padding"], endY + args["padding"]), (0, 255, 0), 2)
				
	else:
		rec = orig[startY -args["padding"] :endY + args["padding"],startX - args["padding"]:endX + args["padding"]]
		ListCrop.append(rec)
		ListCoord[0].append(startX - args["padding"])
		ListCoord[0].append(endX + args["padding"])
		ListCoord[0].append(startY -args["padding"])
		ListCoord[0].append(endY + args["padding"])
		text = pytesseract.image_to_string(rec)
		text = text.replace("\n"," ")
		textfr += translator.translate(text, dest = 'fr').text + " "
		print(textfr)
		cv2.imshow(str(i), rec)

		crop_img = orig[startY-args["padding"]:endY+args["padding"], startX-args["padding"]:endX+args["padding"]]
		data = np.reshape(crop_img, (-1,3))
		data = np.float32(data)
		criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.05)
		flags = cv2.KMEANS_RANDOM_CENTERS
		K=100
		compactness,labels,centers = cv2.kmeans(data,K,None,criteria,30,flags)
		R=0
		G=0
		B=0
		for k in centers:
			R = R+k[0]
			G = G+k[1]
			B = B+k[2]
		c = (int(R/(K)),int(G/(K)),int(B/(K)))
		if c[0]>200 and c[1]>200 and c[2]>200:
			c=(255,255,255)
		cv2.rectangle(orig,(startX - args["padding"], startY -args["padding"]), (endX + args["padding"], endY + args["padding"]),c,-1)
		cv2.rectangle(orig, (startX - args["padding"], startY -args["padding"]), (endX + args["padding"], endY + args["padding"]), (0, 255, 0), 2)
		cv2.putText(orig,textfr, (startX - args["padding"], endY + args["padding"]-10), font, 0.5,fontColor,lineType) 
	
	i = i+1
	
# show the output image
cv2.imshow("Text Detection", orig)
cv2.waitKey(0)









