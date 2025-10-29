import mycamera
import cv2

def main():
    camera = mycamera.MyPiCamera(640,480)
        
    while( camera.isOpened() ):
        _, image = camera.read()
        image = cv2.flip(image,-1)
        cv2.imshow('camera test',image)
        
        if cv2.waitKey(1) == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
