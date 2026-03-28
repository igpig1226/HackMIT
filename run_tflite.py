# run_tflite_tf.py
import numpy as np
from PIL import Image
import tensorflow as tf
import os

# -------------------------
# 1锔忊儯 璁剧疆妯″瀷璺緞鍜屽浘鐗囪矾寰 
model_path = "/root/Desktop/mobilenet_v2_int8.tflite"
image_path = "/root/Desktop/test_cat.jpg"

# 妫€鏌ユ枃浠舵槸鍚﹀瓨鍦 
if not os.path.exists(model_path):
    raise FileNotFoundError(f"妯″瀷鏂囦欢涓嶅瓨鍦 : {model_path}")
if not os.path.exists(image_path):
    raise FileNotFoundError(f"娴嬭瘯鍥剧墖涓嶅瓨鍦 : {image_path}")

# -------------------------
# 2锔忊儯 鍔犺浇 TFLite 妯″瀷
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# -------------------------
# 3锔忊儯 璇诲彇鍜岄澶勭悊鍥剧墖
img = Image.open(image_path).convert("RGB")
height = input_details[0]['shape'][1]
width = input_details[0]['shape'][2]
img = img.resize((width, height))

input_data = np.array(img, dtype=np.float32)
input_data = np.expand_dims(input_data, axis=0)  # NHWC

# -------------------------
# 4锔忊儯 濡傛灉妯″瀷鏄  int8锛岄渶瑕侀噺鍖栬緭鍏 
scale, zero_point = input_details[0]['quantization']
if scale > 0:
    input_data = input_data / 255.0 / scale + zero_point
input_data = input_data.astype(np.int8)

# -------------------------
# 5锔忊儯 鎺ㄧ悊
interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()

# -------------------------
# 6锔忊儯 璇诲彇杈撳嚭
output_data = interpreter.get_tensor(output_details[0]['index'])

# 濡傛灉杈撳嚭閲忓寲锛屼篃杞崲鍥炴诞鐐 
out_scale, out_zero_point = output_details[0]['quantization']
if out_scale > 0:
    output_data = (output_data.astype(np.float32) - out_zero_point) * out_scale

# -------------------------
# 7锔忊儯 杈撳嚭缁撴灉
pred_class = np.argmax(output_data)
print(pred_class)
#print("Raw output:", output_data)