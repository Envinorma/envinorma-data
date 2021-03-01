'''
Temporary script: Testing text zone detection in images to improve tesseract detection.
'''

# Explored Tesseract options
# -c hocr_font_info=1 -c hocr_char_boxes=1 -c tessedit_create_txt=1 -c tessedit_create_hocr=1 -c tessedit_create_alto=1 -c tessedit_create_lstmbox=1 -c tessedit_create_tsv=1 -c tessedit_create_wordstrbox=1 -c tessedit_create_pdf=1 -c textonly_pdf=1

import cv2
import pdf2image

filename = "B_0_8b553fb48eea4243a733f35c8066c880.pdf"
pages = pdf2image.convert_from_path(f'/Users/remidelbouys/EnviNorma/ap_sample/pdf_image_workspace/{filename}')


pages[0].save('tmpimage2.png')
img = cv2.imread('tmpimage2.png')
rects, draw, chainBBs = cv2.text.detectTextSWT(img, True)
for rect in rects:
    cv2.rectangle(img, rect, (255, 0, 0), 2)
