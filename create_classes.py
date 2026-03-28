from datasets import load_dataset

print("Downloading Food101 dataset...")

ds = load_dataset("food101")

classes = ds["train"].features["label"].names

with open("food101_classes.txt", "w") as f:
    for c in classes:
        f.write(c + "\n")

print("DONE ✅")