import cv2
import numpy as np

img = np.zeros((100, 300, 3), dtype=np.uint8)

ft = cv2.freetype.createFreeType2()
ft.loadFontData(fontFileName='Ames-Regular.otf',
                id=0)
ft.putText(img=img,
           text='Quick Fox',
           org=(15, 70),
           fontHeight=60,
           color=(255,  255, 255),
           thickness=-1,
           line_type=cv2.LINE_AA,
           bottomLeftOrigin=True)

cv2.imwrite('image.pngx', img)
