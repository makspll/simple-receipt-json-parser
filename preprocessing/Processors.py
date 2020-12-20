from abc import ABC, abstractmethod
import cv2 
import numpy as np
import pytesseract
from pytesseract import Output

class Processor(ABC):
    @abstractmethod
    def process(self,img):  
        pass

class Denoiser(Processor):
    """ Attempts to remove noise from receipt using thresholding and denoising """
    def __init__(self,lo_intensity_thresh=120):
        self.lo_intensity_thresh = lo_intensity_thresh

    def process(self,img):
        ret,thresh = cv2.threshold(img,self.lo_intensity_thresh,255,cv2.THRESH_BINARY)
        thresh = cv2.fastNlMeansDenoising(thresh)

        return thresh

class ArtifactRemover():
    """ attempts to remove non-textual data from the image """


    def __init__(self,text_area_frac_threshold_lo=0.01,text_area_frac_threshold_hi=0.95):
       """  the bounding box area cutoff argument determines the cutoff point (<,>) for text bounding boxes to be included as text and not treated as noise when they're above the given percentage of the total area of the image"""
       self.text_area_frac_threshold_lo = text_area_frac_threshold_lo
       self.text_area_frac_threshold_hi = text_area_frac_threshold_hi

    def process(self,img):

        # find text and remove things which are not in its bounding boxes
        d = pytesseract.image_to_data(img, output_type=Output.DICT)
        n_boxes = len(d['level'])


        total_mask = np.zeros(img.shape,np.uint8)
        img_area = img.shape[0] * img.shape[1]

        for i in range(n_boxes):
            (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])    
            

            # ignore bounding boxes outside some % of the images area range set
            area = w*h
            if area < self.text_area_frac_threshold_lo * img_area or area > self.text_area_frac_threshold_hi * img_area:
                continue

            min_vals = (min(x,x + w),max(x,x+w),min(y,y+h),max(y,y+h))
            mask = np.zeros(img.shape,np.uint8)
            mask = cv2.rectangle(mask,(x,y),(x+w,y+h),(255),thickness=cv2.FILLED)

            total_mask = cv2.bitwise_or(total_mask,mask)

        # leave only mask in
        n_img = cv2.bitwise_and(img,total_mask)
        
        # make background white
        bg = 255 - total_mask
        n_img = cv2.bitwise_or(n_img,bg) 

        return n_img

class Deskewer(Processor):
    """ tries to straighten out the text in the given image"""

    def __init__(self,text_area_frac_threshold=0.05):
        self.text_area_frac_threshold = text_area_frac_threshold

    def process(self,img):
        return self.deskew(img)

    def getSkewAngle(self,cvImage) -> float:
        """ Calculate skew angle of an image, modified from:  https://becominghuman.ai/how-to-automatically-deskew-straighten-a-text-image-using-opencv-a0c30aed83df"""
        
        # Prep image, copy, convert to gray scale, blur, and threshold
        newImage = cvImage.copy()
        img_area = cvImage.shape[:2][0] * cvImage.shape[:2][1]

        blur = cv2.GaussianBlur(newImage, (9, 9), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Apply dilate to merge text into meaningful lines/paragraphs.
        # Use larger kernel on X axis to merge characters into single line, cancelling out any spaces.
        # But use smaller kernel on Y axis to separate between different blocks of text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilate = cv2.dilate(thresh, kernel, iterations=5)

        # Find all contours
        contours, hierarchy = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key = cv2.contourArea, reverse = True)

        # Find most skewed contour and determine angle
        max_skew_ang_abs = 0
        max_skew_ang = 0
        for c in contours:
            minAreaRect = cv2.minAreaRect(c)
            area = minAreaRect[1][0] * minAreaRect[1][1]

            # ignore little bounding blobs areas, otherwise we might get real noisy angles
            if area < self.text_area_frac_threshold * img_area:
                continue

            # Determine the angle. Convert it to the value that was originally used to obtain skewed image
            angle = self.determine_rot_angle_from_rot_box(minAreaRect)
            if abs(angle) > max_skew_ang_abs:
                max_skew_ang_abs = abs(angle)
                max_skew_ang = angle
        return max_skew_ang

    def determine_rot_angle_from_rot_box(self,minAreaRect):
        """ determine the rotation of a box of text given its rotated minimum bounding box"""
        angle = minAreaRect[-1]
        if angle < -45:
            angle = 90 + angle
        return -1.0 * angle

    def rotateImage(self,cvImage, angle: float):
        """ Rotate the image around its center """

        M = cv2.moments(cvImage)
        cX = int(M["m10"]/M["m00"])
        cY = int(M["m01"]/M["m00"])

        newImage = cvImage.copy()
        (h, w) = newImage.shape[:2]
        center = (cX, cY)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        newImage = cv2.warpAffine(newImage, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,borderValue=255)
        return newImage


    def deskew(self,cvImage):
        """ Deskew image """
        angle = self.getSkewAngle(cvImage)
        return self.rotateImage(cvImage, -1.0 * angle)

class Dilater(Processor):
    """ boldens the contours present in the image """

    def __init__(self,iterations=1,kernel_shape=(2,2)):
        self.iterations= iterations
        self.kernel_shape = kernel_shape

    def process(self,img):

        # since our letters are black and not white, erosion becomes dilation
        kernel = np.ones(self.kernel_shape, np.uint8) 
        return cv2.erode(img,kernel,iterations=self.iterations)

class Eroder(Processor):
    """ shrinks the contours present in the image, good for removing small noises """
    
    def __init__(self,iterations=1,kernel_shape=(2,2)):
        self.iterations= iterations
        self.kernel_shape = kernel_shape

    def process(self,img):

        # since our letters are black and not white, erosion becomes dilation
        kernel = np.ones(self.kernel_shape, np.uint8) 
        return cv2.dilate(img,kernel,iterations=self.iterations)

