'''
Feature for detecting text in an image -- useless for now
'''
# from dataclasses import dataclass
# from typing import List, Tuple

# import cv2
# import numpy as np


# @dataclass(unsafe_hash=True)
# class Rectangle:
#     x: int
#     y: int
#     width: int
#     height: int

#     def upper_left_point(self) -> Tuple[int, int]:
#         return (self.x, self.y)

#     def lower_right_point(self) -> Tuple[int, int]:
#         return (self.x + self.width, self.y + self.height)


# def _extract_character_rectangles(image: np.ndarray) -> List[Rectangle]:
#     rects, _, _ = cv2.text.detectTextSWT(image, True)
#     return [Rectangle(*rect) for rect in rects]


# def _hide_exterior(image: np.ndarray, rectangles: List[Rectangle]) -> np.ndarray:
#     mask = np.full((image.shape[0], image.shape[1]), 255, dtype=np.uint8)
#     for rectangle in rectangles:
#         cv2.rectangle(
#             img=mask,
#             rec=(rectangle.x, rectangle.y, rectangle.width, rectangle.height),
#             color=(0, 0, 0),
#             thickness=-1,
#         )
#     mask = cv2.bitwise_not(mask)
#     cv2.imwrite('test0.png', mask)
#     cv2.imwrite('test0.png', cv2.bitwise_or(image, image, mask=mask))
#     return cv2.bitwise_or(image, image, mask=mask)


# def _grow_rectangle(rectangle: Rectangle, image_width: int, image_height: int) -> Rectangle:
#     x_0 = max(rectangle.x - rectangle.width // 2, 0)
#     y_0 = max(rectangle.y - rectangle.height // 2, 0)
#     x_1 = min(rectangle.x + 3 * rectangle.width // 2, image_width)
#     y_1 = min(rectangle.y + 3 * rectangle.height // 2, image_height)
#     return Rectangle(x_0, y_0, x_1 - x_0, y_1 - y_0)


# def _grow_rectangles(rectangles: List[Rectangle], image_width: int, image_height: int) -> List[Rectangle]:
#     return [_grow_rectangle(rect, image_width, image_height) for rect in rectangles]


# def remove_images(image: np.ndarray) -> np.ndarray:
#     rectangles = _grow_rectangles(_extract_character_rectangles(image), image.shape[0], image.shape[1])
#     return _hide_exterior(image, rectangles)


# if __name__ == '__main__':
#     img = cv2.imread('tmpimage.png')
#     clean = remove_images(img)
#     cv2.imwrite('out.png', img)
