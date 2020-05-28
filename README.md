
# RediSafe - An AI Tool for PPE safety checks during COVID-19
During the COVID-19 pandemic, Redisafe is developed to be a secured AI platform with the purpose of detecting PPE on medical staff for safety protocol to prevent the spread of virus.
This project combines several [Redis](https://redis.io) data structures and [Redis Modules](https://redis.io/topics/modules-intro)
to process a stream of images and classify them with the Tensorflow detection model.

It uses:
* Redis Streams to capture the input video stream: `camera:0`
* [RedisAI](https://oss.redislabs.com/redisai/) to classify the images with TensorFlow mask detection model.
* Express.js to serve the client side.

It forwards the classifies images to a stream: `results`

## Architecture
![Architecture](https://i.ibb.co/9gTwtCH/redisafe-architecturediagram.png)

## Runtime
Python 3.6

## Requirements
* OpenCV
* Redis - python client
* RedisAI - python client
* Numpy

## Running the Demo
To run the demo:
```
$ git clone https://github.com/sagban/redisPPEScan.git
$ cd redisPPEScan
$ pip install -r requirements.txt # Now install the python dependencies
```
## RedisAi Detection Model
Start the redisAI detction model:
```
$ cd app/mask_detection
$ python detection.py
```
## Camera Feed
Open a second terminal for the video capturing:
```
$ python camera/read_camera.py
```

## UI
Open a third terminal for the express.js client application:
```
$ cd client
$ npm install
$ node server.js
```
`http://localhost:3000` shows all the classified frames.

## Limitations
This demo is designed to be easy to setup, so it relies heavily on docker.
You can get better performance and a higher FPS by runninng this demo outside docker.

## Contributer
**Sagar Bansal**
**VI LY**
