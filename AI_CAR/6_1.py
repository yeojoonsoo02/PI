import mycamera
import cv2

def main():
    camera = mycamera.MyPiCamera(640,480)
  
    while( camera.isOpened() ):
        
        keyValue = cv2.waitKey(10)
        print(str(keyValue))
        
        if keyValue == ord('q') :
            break
        
        _, image = camera.read()
        image = cv2.flip(image,-1)
        cv2.imshow('Original', image)
            
    cv2.destroyAllWindows()
    
if __name__ == '__main__':
    main()
