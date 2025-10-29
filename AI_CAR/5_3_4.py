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
        
        cv2.imshow('thresh1',thresh1)
        
        if cv2.waitKey(1) == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()

