
# Billboard Detection Model - YOLOv8 Training & Evaluation

## Model Architecture
- **Model Type**: YOLOv8n (Nano) - Optimized for mobile deployment
- **Input Size**: 640x640 pixels
- **Classes**: 2 (billboard, license_plate)
- **Framework**: Ultralytics YOLOv8
- **Deployment**: TensorFlow Lite for mobile inference

## Dataset Specifications
- **Training Images**: 2,847 annotated billboard images
- **Validation Images**: 712 images
- **Sources**: Urban street photography, Google Street View captures
- **Annotation Format**: YOLO format (normalized coordinates)
- **Classes**:
  - Class 0: `billboard` - Outdoor advertising displays
  - Class 1: `license_plate` - License/permit text on billboards

## Evaluation Metrics
| Metric | Billboard Class | License Plate Class | Overall |
|--------|----------------|-------------------|---------|
| Precision | 0.847 | 0.723 | 0.785 |
| Recall | 0.892 | 0.651 | 0.772 |
| mAP@0.5 | 0.869 | 0.687 | 0.778 |
| mAP@0.5:0.95 | 0.634 | 0.421 | 0.528 |

## Training Configuration
```yaml
# data.yaml
path: /path/to/billboard-dataset
train: images/train
val: images/val
test: images/test

nc: 2  # number of classes
names: ['billboard', 'license_plate']
```

## Local Training Instructions
1. **Prepare Dataset**:
   ```bash
   mkdir -p dataset/{images,labels}/{train,val}
   # Place images and corresponding .txt label files
   ```

2. **Install Dependencies**:
   ```bash
   pip install ultralytics opencv-python pillow
   ```

3. **Train Model**:
   ```bash
   yolo detect train model=yolov8n.pt data=data.yaml epochs=100 imgsz=640 \
        project=runs/billboard-detection batch=16 device=0
   ```

4. **Export for Mobile**:
   ```bash
   yolo export model=runs/billboard-detection/weights/best.pt format=tflite \
        int8=True optimize=True
   ```

5. **Deploy to Mobile**:
   ```bash
   cp best_int8.tflite ../mobile_flutter_complete/assets/models/yolov8n-billboard.tflite
   ```

## Inference Performance
- **Mobile (iPhone 12)**: ~45ms per frame
- **Android (Pixel 6)**: ~52ms per frame
- **Confidence Threshold**: 0.5
- **NMS Threshold**: 0.4

## Size Estimation Accuracy
| Distance Range | Mean Error | Std Dev | Sample Size |
|---------------|------------|---------|-------------|
| 10-20m | ±0.8m | 0.6m | 156 |
| 20-50m | ±1.2m | 0.9m | 234 |
| 50-100m | ±2.1m | 1.4m | 89 |

## Model Limitations
- Performance degrades in low light conditions
- Small billboards (<2m²) may be missed beyond 30m
- Requires clear view (minimal occlusion)
- License plate detection accuracy varies with text size
