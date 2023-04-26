#!/usr/bin/env python3
import cv2, threading, params
from threading import Thread
from threading import Lock

#flag specifications
switchesVarDefaults = (
    (('-v', '--video'), 'video', 'clip.mp4'),
    (('-f', '--frames'), 'frames', '72'),
    (('-?', '--usage'), "usage", False),
)
progname = "playVideo"
paramMap = params.parseParams(switchesVarDefaults)
filename, usage = paramMap["video"], paramMap["usage"]
numFrames = int(paramMap['frames']) # num of frames to display
if usage:
    params.usage()

#Thread Queue Class
class ThreadQ:
    #initialize queue with max capacity 10 as default
    def __init__(self, max = 10):
        self.queue = []
        self.capacity = max
        self.semaphoreMax = threading.Semaphore(max)
        self.semaphoreUsed = threading.Semaphore(0)
        self.mutex = Lock()

    #enqueue: acquire mutex lock, append element, release lock
    #semaphore used for concurrent access
    def enqueue(self, element):
        self.semaphoreMax.acquire()
        self.mutex.acquire()
        self.queue.append(element)
        self.mutex.release()
        self.semaphoreUsed.release()

    #dequeue acquire mutex lock, pop element, release lock
    #semaphore used for concurrent access
    def dequeue(self):
        self.semaphoreUsed.acquire()
        self.mutex.acquire()
        element = self.queue.pop(0)
        self.mutex.release()
        self.semaphoreMax.release()
        return element

#extract series of frames from video file in sequence
def extractFrames(video_file, frames_q, maxFrames):
    #initialize frame count
    count = 0
    #open video clip
    vidcap = cv2.VideoCapture(video_file)
    #read one frame
    success, image = vidcap.read()
    print(f'Reading Frame #{count} {success}')

    while success and count < maxFrames:
        #get a jpg encoded frame
        success, jpgImage = cv2.imencode('.jpg', image)
        #queueing jpg
        frames_q.enqueue(jpgImage)
        #reading next frame
        success, image = vidcap.read()
        print(f'Reading frame #{count}')
        #increment frame count
        count += 1
    #queue null for stopping point
    frames_q.enqueue(None)

#loads a series of frames in sequence from queue
def displayFrames(inputBuffer):
    frameDelay = 42 #the answer to everything
    #initialize frame count
    count = 0
    #first gray frame
    frame = inputBuffer.dequeue()

    while frame is not None:
        print(f'Displaying frame #{count}')
        #decoding
        image = cv2.imdecode(frame, cv2.IMREAD_UNCHANGED)
        cv2.imshow('Video', image)

        #wait for 42 ms and check if the user wants to quit
        if cv2.waitKey(frameDelay) and 0xFF == ord("q"):
            break
        #get the next filename
        count += 1
        #reads next frame
        frame = inputBuffer.dequeue()
    #make sure we cleanup the windows
    cv2.destroyAllWindows()

#loads a series of frames sequentially and converts to grayscale
def convertGrayscale(frames_q, gray_q):
    #initialize frame count
    count = 0
    #load next file
    inputFrame = frames_q.dequeue()

    while inputFrame is not None and count < numFrames:
        print(f'Converting frame #{count}')
        #decode input frame back to image
        image = cv2.imdecode(inputFrame, cv2.IMREAD_UNCHANGED)
        #converting image to grayscale
        grayscaleFrame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        #encoding and storing in queue
        success, jpgImage = cv2.imencode('.jpg', grayscaleFrame)
        #queueing grayscaled image
        gray_q.enqueue(jpgImage)
        #increment frame count
        count += 1
        #queue next frame
        inputFrame = frames_q.dequeue()
    #queueing null as stopping point
    gray_q.enqueue(None)


#video queue
frames_q = ThreadQ()
#grayscale queue
gray_q = ThreadQ()

#simultaneous threads start
extract_thread = Thread(target=extractFrames, args=(filename, frames_q, numFrames)).start()
convert_gray_thread = Thread(target=convertGrayscale, args=(frames_q, gray_q)).start()
display_thread = Thread(target=displayFrames, args=(gray_q,)).start()