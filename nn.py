import matplotlib.pyplot as plt
import torch
import torch.nn.functional as F
from torch import nn
from tqdm import tqdm
from torch.utils.data import DataLoader

from dataset import AURADataset

NUM_EPOCHS = 100
LABELS = ('AWAY', 'RELAX', 'SLEEP', 'STUDY')


class MLP(nn.Module):

    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(1, 8)
        self.TransformerEncoderLayer = nn.TransformerEncoderLayer(8, 2, dim_feedforward=64, batch_first=True)
        self.TransformerEncoder = nn.TransformerEncoder(self.TransformerEncoderLayer, 4)
        self.fc2 = nn.Linear(320, 40)
        self.fc3 = nn.Linear(40, 4)

    def forward(self, x):
        x = x.unsqueeze(-1)
        x = self.fc1(x)
        x = self.TransformerEncoder(x)
        x = x.flatten(1)
        x = self.fc2(x)
        x = self.fc3(x)
        return x
    
    def load_state_dict(self, path='model.pt'):
        state_dict = torch.load(path)
        super().load_state_dict(state_dict)

    def predict(self, x):
        self.eval()
        with torch.no_grad():
            x = torch.tensor(x, dtype=torch.float32, device=self.fc1.weight.device)
            x = x.unsqueeze(0)
            x = self(x)
            label = torch.argmax(x).item()
        return LABELS[label]


if __name__ == '__main__':
    model = MLP()
    loss_func = nn.CrossEntropyLoss()
    optim = torch.optim.Adam(model.parameters(), lr=0.001)
    train_losses = []
    train_accs = []
    val_losses = []
    val_accs = []
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # TODO: collect the data
    # data = torch.randint(0, 1024, (100, 9))
    # labels = torch.randint(0, 4, (100,))
    train_dataset = AURADataset('upper0.8')
    train_dataset.set_mode('train')
    train_loader = DataLoader(train_dataset, shuffle=True, batch_size=32)
    val_dataset = AURADataset('lower0.2')
    val_dataset.set_mode('test')
    val_loader = DataLoader(val_dataset, batch_size=64)
    model.to(device)
    loss_func.to(device)
    model.train()

    print(f'Training for {NUM_EPOCHS} epochs...')
    for epoch in tqdm(range(1, 1 + NUM_EPOCHS)):
        # Start training.
        cur_loss = 0
        cur_correct = 0
        model.train()
        for label, x in train_loader:
            x = x.to(device=device, dtype=torch.float32)
            label = label.to(device)
            optim.zero_grad()
            pred = model(x)
            loss = loss_func(pred, label)
            cur_loss += loss.item()
            cur_correct += torch.sum(torch.argmax(pred, dim=1) == label).cpu()
            loss.backward()
            optim.step()
        train_losses.append(cur_loss / len(train_dataset))
        train_accs.append(cur_correct / len(train_dataset))

        # Start validating.
        cur_loss = 0
        cur_correct = 0
        model.eval()
        with torch.no_grad():
            for label, x in val_loader:
                x = x.to(device=device, dtype=torch.float32)
                label = label.to(device)
                pred = model(x)
                loss = loss_func(pred, label)
                cur_loss += loss.item()
                cur_correct += torch.sum(torch.argmax(pred, dim=1) == label).cpu()
        val_losses.append(cur_loss / len(val_dataset))
        val_accs.append(cur_correct / len(val_dataset))

        # Save the model parameters every 10 epochs.
        if epoch % 10 == 0:
            state_dict = model.state_dict()
            torch.save(state_dict, 'model.pt')

        # Plot the loss and the accuracy.
        if epoch > 1:
            plt.cla()
            plt.plot(train_losses[1:], label='Training Loss')
            plt.plot(train_accs[1:], label='Training Accuracy')
            plt.plot(val_losses[1:], label='Validation Loss')
            plt.plot(val_accs[1:], label='Validation Accuracy')
            plt.title('Loss and Accuracy')
            plt.xlabel('Epoch')
            plt.legend()
            plt.savefig('loss.png')