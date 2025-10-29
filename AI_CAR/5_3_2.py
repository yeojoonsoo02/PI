import mycamera
import cv2

def main():
    camera = mycamera.MyPiCamera(320,240)

    while( camera.isOpened() ):
        _, image = camera.read()
        image = cv2.flip(image,-1)
        cv2.imshow('normal',image)
        
        height, width, _ = image.shape
        print(height,width)
        crop_img = image[height //2 :, :]
        cv2.imshow('crop',crop_img)
        
        if cv2.waitKey(1) == ord('q'):
            break
    
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()