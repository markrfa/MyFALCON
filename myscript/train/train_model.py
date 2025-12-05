from sklearn.metrics import accuracy_score
from tqdm import tqdm
import time


def train_loop(model, dataloader, loss_fn, optimizer, device):
    model.train()
    total_loss = 0
    total_preds, total_labels = [], []
    start_time = time.time()

    for x, y in tqdm(dataloader, desc="Train", leave=False):
        x, y = x.to(device), y.to(device)

        optimizer.zero_grad()
        out = model(x)
        pred = out.argmax(dim=1)
        loss = loss_fn(out, y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        total_preds.extend(pred.cpu().numpy())
        total_labels.extend(y.cpu().numpy())
    
    avg_loss = total_loss / len(dataloader)
    acc = accuracy_score(total_labels, total_preds)
    end_time = time.time()
    print(f" [Train] Average Loss: {avg_loss} | Accuracy: {acc} | Training Time: {end_time - start_time}")
    return avg_loss


def eval_loop(model, dataloader, loss_fn, device):
    model.eval()
    total_loss = 0
    total_preds, total_labels = [], []
    start_time = time.time()

    for x, y in tqdm(dataloader, desc="Eval", leave=False):
        x, y = x.to(device), y.to(device)

        out = model(x)
        pred = out.argmax(dim=1)
        loss = loss_fn(out, y)

        total_loss += loss.item()
        total_preds.extend(pred.cpu().numpy())
        total_labels.extend(y.cpu().numpy())

    avg_loss = total_loss / len(dataloader)
    acc = accuracy_score(total_preds, total_labels)
    end_time = time.time()        
    print(f" [Eval] Average Loss: {avg_loss} | Accuracy: {acc} | Evaluation Time: {end_time - start_time}")
    return avg_loss
