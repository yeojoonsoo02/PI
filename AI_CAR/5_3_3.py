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
        
        cv2.imshow('crop+gray+blur',blur)
        
        if cv2.waitKey(1) == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
