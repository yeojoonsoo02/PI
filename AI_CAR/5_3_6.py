import mycamera
import cv2

def main():
    camera = mycamera.MyPiCamera(320,240)

    while( camera.isOpened() ):
        _, image = camera.read()
        image = cv2.flip(image,-1)
        cv2.imshow('normal',image)
        
        height, width, _ = image.shape
        crop_img = image[height //2 :, :]
        
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    
        blur = cv2.GaussianBlur(gray,(5,5),0)
        
        ret,thresh1 = cv2.threshold(blur,130,255,cv2.THRESH_BINARY_INV)
        
        mask = cv2.erode(thresh1, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cv2.imshow('mask',mask)
    
        contours,hierarchy = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)
        
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)
            
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            
            if cx >= 190 and cx <= 250:              
                print("Turn Left!")
            elif cx >= 80 and cx <= 130:
                print("Turn Right")
            else:
                print("go")
        
        if cv2.waitKey(1) == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()



