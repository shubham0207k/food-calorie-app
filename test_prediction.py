import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import io
import urllib.request

# Load mapping
with open("food101_classes.txt", "r") as f:
    food_labels = [line.strip().replace('_', ' ').title() for line in f if line.strip()]

# Preprocessing
predict_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# Load model
model = models.mobilenet_v2(num_classes=101)
model.load_state_dict(torch.load("food101_mobilenet_v2.pth", map_location="cpu"))
model.eval()

# Download a sample pizza image
pizza_url = "https://upload.wikimedia.org/wikipedia/commons/9/91/Pizza-3007395.jpg"
print("Downloading sample pizza image...")
req = urllib.request.Request(pizza_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    img_data = response.read()

img = Image.open(io.BytesIO(img_data)).convert('RGB')
tensor = predict_transform(img).unsqueeze(0)

with torch.no_grad():
    outputs = model(tensor)
    probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

top3_prob, top3_indices = torch.topk(probabilities, 3)
print("Top 3 Predictions for Pizza Image:")
for i in range(3):
    prob = float(top3_prob[i])
    idx = int(top3_indices[i])
    print(f" - {food_labels[idx]}: {prob*100:.1f}%")
