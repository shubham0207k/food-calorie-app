import json
import time
from pathlib import Path

import torch
import timm
from PIL import Image
from sklearn.metrics import precision_score, recall_score, f1_score
from timm.data import create_transform, resolve_model_data_config


# =========================
# Configuration
# =========================

MODEL_NAME = "hf_hub:anonauthors/food101-resnet50"

DATASET_ROOT = Path("evaluation_data/food-101")
IMAGE_ROOT = DATASET_ROOT / "images"
TEST_LIST = DATASET_ROOT / "meta" / "test.txt"

DEVICE = torch.device("cpu")


# =========================
# Load model
# =========================

print("Loading ResNet-50 CNN...")

model = timm.create_model(
    MODEL_NAME,
    pretrained=True,
    num_classes=101,
)

model = model.to(DEVICE)
model.eval()

config = resolve_model_data_config(model)
transform = create_transform(**config)

print("Model loaded.")
print("Device:", DEVICE)
print("Classes:", model.num_classes)


# =========================
# Load official test split
# =========================

if not TEST_LIST.exists():
    raise FileNotFoundError(
        f"Food-101 test list not found: {TEST_LIST}"
    )

test_entries = [
    line.strip()
    for line in TEST_LIST.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

print("Official test images:", len(test_entries))

if len(test_entries) != 25250:
    raise RuntimeError(
        f"Expected 25,250 test images, found {len(test_entries)}"
    )


# Food-101 class names
classes = sorted(
    folder.name
    for folder in IMAGE_ROOT.iterdir()
    if folder.is_dir()
)

if len(classes) != 101:
    raise RuntimeError(
        f"Expected 101 classes, found {len(classes)}"
    )

class_to_index = {
    class_name: index
    for index, class_name in enumerate(classes)
}


# =========================
# Build test samples
# =========================

samples = []

for entry in test_entries:
    # Entries look like:
    # apple_pie/1005649

    class_name, image_id = entry.split("/", 1)

    image_path = IMAGE_ROOT / class_name / f"{image_id}.jpg"

    if not image_path.exists():
        raise FileNotFoundError(
            f"Test image not found: {image_path}"
        )

    samples.append(
        (image_path, class_to_index[class_name])
    )


print("Images selected:", len(samples))
print("Classes:", len(classes))
print("Evaluation: complete Food-101 test split")


# =========================
# Evaluation
# =========================

y_true = []
y_pred = []

top5_correct = 0
total = 0

total_inference_time = 0.0

print("\nStarting full evaluation...\n")

with torch.no_grad():

    for index, (image_path, true_label) in enumerate(
        samples, start=1
    ):

        image = Image.open(image_path).convert("RGB")

        tensor = (
            transform(image)
            .unsqueeze(0)
            .to(DEVICE)
        )

        start = time.perf_counter()

        output = model(tensor)

        elapsed = time.perf_counter() - start

        total_inference_time += elapsed

        probabilities = torch.softmax(
            output, dim=1
        )[0]

        top5 = torch.topk(
            probabilities,
            5
        ).indices.tolist()

        predicted_label = int(
            torch.argmax(probabilities)
        )

        y_true.append(true_label)
        y_pred.append(predicted_label)

        if true_label in top5:
            top5_correct += 1

        total += 1

        if index % 250 == 0 or index == len(samples):
            print(
                f"Processed {index}/{len(samples)}"
            )


# =========================
# Metrics
# =========================

top1_accuracy = sum(
    true == pred
    for true, pred in zip(y_true, y_pred)
) / total

top5_accuracy = top5_correct / total

precision = precision_score(
    y_true,
    y_pred,
    average="macro",
    zero_division=0,
)

recall = recall_score(
    y_true,
    y_pred,
    average="macro",
    zero_division=0,
)

f1 = f1_score(
    y_true,
    y_pred,
    average="macro",
    zero_division=0,
)

average_inference_ms = (
    total_inference_time / total
) * 1000


# =========================
# Results
# =========================

results = {
    "model": "ResNet-50",
    "model_source": MODEL_NAME,
    "dataset": "Food-101",
    "split": "test",
    "classes": len(classes),
    "images_evaluated": total,
    "device": str(DEVICE),
    "top1_accuracy": round(
        top1_accuracy * 100, 2
    ),
    "top5_accuracy": round(
        top5_accuracy * 100, 2
    ),
    "macro_precision": round(
        precision * 100, 2
    ),
    "macro_recall": round(
        recall * 100, 2
    ),
    "macro_f1": round(
        f1 * 100, 2
    ),
    "average_inference_ms": round(
        average_inference_ms, 2
    ),
}


# =========================
# Display results
# =========================

print("\n" + "=" * 55)
print("FoodVision CNN - Full Food-101 Evaluation")
print("=" * 55)

print(f"Model:                 {results['model']}")
print(f"Dataset:               {results['dataset']}")
print(f"Split:                 {results['split']}")
print(f"Classes:               {results['classes']}")
print(f"Images evaluated:      {results['images_evaluated']}")
print(f"Device:                {results['device']}")
print(f"Top-1 Accuracy:        {results['top1_accuracy']}%")
print(f"Top-5 Accuracy:        {results['top5_accuracy']}%")
print(f"Macro Precision:       {results['macro_precision']}%")
print(f"Macro Recall:          {results['macro_recall']}%")
print(f"Macro F1:              {results['macro_f1']}%")
print(
    f"Avg inference time:    "
    f"{results['average_inference_ms']} ms/image"
)

print("=" * 55)


# =========================
# Save results
# =========================

output_path = Path(
    "evaluation/cnn_results.json"
)

with open(
    output_path,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        results,
        f,
        indent=4
    )

print("\nResults saved to:")
print(output_path)