import pickle

import numpy as np
from torch.utils.data import Dataset

DATA_PATH = 'data.pkl'
LABELS = {
    'AWAY': 0,
    'RELAX': 1,
    'SLEEP': 2,
    'STUDY': 3
}


class AURADataset(Dataset):
    
    def __init__(self, division='all'):
        """The dataset class.

        Args:
            division (str, optional): The portion of data to be loaded, can be
                'all' or 'upper'/'lower' followed by a float number that
                represents the proportion of data such as 'upper0.8'. Defaults
                to 'all'.
        """        
        with open(DATA_PATH, 'rb') as f:
            data = pickle.load(f)
        if division == 'all':
            self.data = data
        else:
            l = int(len(data) * eval(division[5:]))
            if division.startswith('upper'):
                self.data = data[:l]
            else:
                self.data = data[len(data) - l:]
        self.mode = 'demo'
        
    def __getitem__(self, index):
        return self.data[index]
    
    def __len__(self):
        return len(self.data)
    
    def __str__(self):
        num_data = min(len(self.data), 10)
        res = f'Showing the first {num_data} sample.\n'
        for i in range(num_data):
            res += f'Label: {self[i][0]}   Data: {self[i][1]}\n'
        return res
    
    def set_mode(self, mode):
        self.mode = mode
    

if __name__ == '__main__':
    dataset = AURADataset()
    dataset.set_mode('train')
    print(dataset[0])