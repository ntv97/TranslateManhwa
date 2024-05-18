import cv2
import easyocr
from matplotlib import pyplot as plt
import numpy as np
from deep_translator import GoogleTranslator
from PIL import ImageFont

image=cv2.imread("input.jpg")
#Displaying image using plt.imshow() method

LANGUAGE = "ko"
reader = easyocr.Reader([LANGUAGE])
result = reader.readtext(image)
print(result)

# Read the image
img_rect = cv2.imread("input.jpg") #cv2.imread(image)
img_temp = cv2.imread("input.jpg") #cv2.imread(image)
h, w, c = img_temp.shape

# Fill temp image with black
img_temp = cv2.rectangle(img_temp, [0,0], [w, h], (0, 0, 0), -1)
img_inpaint = cv2.imread("input.jpg") #cv2.imread(image)
preview_rect = cv2.imread("input.jpg") #cv2.imread(image)

raw_list = []
rects = []
for r in result:
    raw_list.append(r[1])
    bottom_left = tuple(int(x) for x in tuple(r[0][0]))
    top_right = tuple(int(x) for x in tuple(r[0][2]))
    rects.append((top_right, bottom_left))
    # Draw a rectangle around the text
    img_rect = cv2.rectangle(img_rect, bottom_left, top_right, (0,255,0), 3)
    # Fill text with white rectangle
    img_temp = cv2.rectangle(img_temp, bottom_left, top_right, (255, 255, 255), -1)
    # Convert temp image to black and white for mask
    mask = cv2.cvtColor(img_temp, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("./mask.png", mask)
    # "Content-Fill" using mask (INPAINT_NS vs INPAINT_TELEA)
    img_inpaint = cv2.inpaint(img_inpaint, mask, 3, cv2.INPAINT_TELEA)
    cv2.imwrite("./inpaint.png", img_inpaint)
    # Draw a rectangle around the text
    preview_rect = cv2.rectangle(img_rect, bottom_left, top_right, (0,255,0), 3)
    # Draw confidence level on detected text
    cv2.putText(preview_rect, str(round(r[2], 2)), bottom_left, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, 1)
    cv2.imwrite("./rect.png", preview_rect)
    #translated = GoogleTranslator(source='ko', target='en').translate(r[1])
    #cv2.putText(img_inpaint, translated, r[0][0], cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 0, 0), 2)
    #cv2.imwrite("./translated.png", img_inpaint)


    #plt.imshow(img_inpaint)
img = cv2.imread("inpaint.png")
#font = ImageFont.truetype("./Ames-Regular.otf", 12)
threshold = 0.25
for t_, t in enumerate(result):
    bbox, text, score = t
    translated = GoogleTranslator(source='ko', target='en').translate(text)

    if score > threshold:
        cv2.putText(img, translated, bbox[0], cv2.FONT_HERSHEY_COMPLEX, 1.0, (0, 0, 0), 2)
cv2.imwrite("./translated.png", img)

plt.imshow(image)
#hold the window
plt.waitforbuttonpress()
plt.close('all')
#window_name = 'image'
#cv2.imshow(window_name, img) 
#cv2.destroyAllWindows()
