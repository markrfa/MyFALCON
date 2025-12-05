# bring the model, dataloader, and optimizer
# and determine the epoch and train the model

from model.mlp_classifier import MLPClassifier
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
import torch.optim as optim
import torch.nn as nn
from train.train_model import train_loop, eval_loop
import torch
import numpy as np
import matplotlib.pyplot as plt 


def train(dataset, 
          epochs = 10,
          learning_rate = 1e-4, 
          batch_size = 64,
          loss_fn = nn.CrossEntropyLoss()):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model = MLPClassifier()

    train_dataset, test_dataset = train_test_split(dataset, test_size=0.1, random_state=42)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size)

    optimizer = optim.AdamW(model.parameters(), lr=learning_rate)

    train_loss_list, val_loss_list = [], []
    best_loss = np.inf
    for epoch in range(epochs):
        print("-" * 12 + f"Epoch: {epoch}" + "-" * 12)
        train_loss = train_loop(model, train_dataloader, loss_fn, optimizer, device)
        val_loss = eval_loop(model, test_dataloader, loss_fn, device)

        train_loss_list.append(train_loss)
        val_loss_list.append(val_loss)

        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(), 
        }, "latest.pth")
        if val_loss < best_loss:
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict()
            }, "best.pth")
            best_loss = val_loss
            print(f"best model saved from epoch {epoch}")
    print("DONE")

    epochs_range = range(1, len(train_loss_list) + 1)
    plt.figure()
    plt.plot(epochs_range, train_loss_list, color="red", label="Training Loss")
    plt.plot(epochs_range, val_loss_list, color="blue", label="Validation Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training vs Validation Loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig("loss_curves.png")
    plt.close()
