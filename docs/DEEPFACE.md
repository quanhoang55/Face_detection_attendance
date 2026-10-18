## Installation [![PyPI](https://img.shields.io/pypi/v/deepface.svg)](https://pypi.org/project/deepface/)

The easiest way to install deepface is to download it from [`PyPI`](https://pypi.org/project/deepface/). It's going to install the library itself and its prerequisites as well.

```shell
# runs deepface on onnxruntime by default
$ pip install deepface

# or to run deepface on tensorflow
# $ pip install deepface[tensorflow]

# or to run deepface on pytorch
# $ pip install deepface[pytorch]

# manage backend deep learning framework if you have many
# export DEEPFACE_BACKEND_ENGINE=onnx
```

**Face Anti Spoofing** - [`Demo`](https://youtu.be/UiK1aIjOBlQ)

DeepFace also includes an anti-spoofing analysis module to understand given image is real or fake. To activate this feature, set the `anti_spoofing` argument to True in any DeepFace tasks.

```python
# anti spoofing test in face detection
face_objs = DeepFace.extract_faces(img_path="dataset/img1.jpg", anti_spoofing = True)
assert all(face_obj["is_real"] is True for face_obj in face_objs)

# anti spoofing test in real time analysis
DeepFace.stream(db_path = "C:/database", anti_spoofing = True)
```
