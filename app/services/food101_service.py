from io import BytesIO
from pathlib import Path

from PIL import Image
import torch
import timm
from timm.data import resolve_model_data_config, create_transform


MODEL_NAME = "hf_hub:anonauthors/food101-resnet50"

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABELS_PATH = PROJECT_ROOT / "food101_classes.txt"

model = None
transform = None
food_labels = None


def load_food_labels():
    """Load the 101 Food-101 class names."""
    global food_labels

    if food_labels is None:
        if not LABELS_PATH.exists():
            raise FileNotFoundError(
                f"Food-101 label file not found: {LABELS_PATH}"
            )

        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            food_labels = [
                line.strip()
                for line in f
                if line.strip()
            ]

        if len(food_labels) != 101:
            raise ValueError(
                f"Expected 101 Food-101 labels, found {len(food_labels)}"
            )

    return food_labels


def get_model():
    """Load the pretrained Food-101 ResNet-50 CNN."""

    global model, transform

    if model is None:
        model = timm.create_model(
            MODEL_NAME,
            pretrained=True
        )

        model.eval()

        config = resolve_model_data_config(model)

        transform = create_transform(**config)

    load_food_labels()

    return model, transform


def predict_food(image_file):
    """
    Predict food using the Food-101 ResNet-50 CNN.

    Returns:
        food_name (str)
        confidence (float)
        predictions_list (list)
    """

    if isinstance(image_file, bytes):
        image = Image.open(
            BytesIO(image_file)
        ).convert("RGB")
    else:
        image = Image.open(
            image_file
        ).convert("RGB")

    cnn_model, image_transform = get_model()

    labels = load_food_labels()

    image_tensor = image_transform(image).unsqueeze(0)

    with torch.inference_mode():
        logits = cnn_model(image_tensor)

        probabilities = torch.softmax(
            logits,
            dim=1
        )[0]

    top_probabilities, top_indices = torch.topk(
        probabilities,
        k=3
    )

    predictions_list = []

    for probability, index in zip(
        top_probabilities,
        top_indices
    ):
        class_index = int(index)

        food_name = labels[class_index].replace(
            "_",
            " "
        )

        predictions_list.append({
            "name": food_name,
            "confidence": round(
                float(probability) * 100,
                2
            )
        })

    food_name = predictions_list[0]["name"]

    confidence = float(
        top_probabilities[0]
    )

    return (
        food_name,
        confidence,
        predictions_list
    )