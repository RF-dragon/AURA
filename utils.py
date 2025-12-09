import pickle

import numpy as np

DATASETS = ('data_away.pkl', 'data_away.pkl', 'data_sleep.pkl', 'data_study.pkl')
LABELS = {
    'AWAY': 0,
    'RELAX': 1,
    'SLEEP': 2,
    'STUDY': 3
}

def num_data(path):
    with open(path, 'rb') as f:
        dataset = pickle.load(f)
    return len(dataset)

def data_combination():
    res = []
    for dataset in DATASETS:
        with open(dataset, 'rb') as f:
            dataset = pickle.load(f)
            temp = []
            for i in range(9):
                data = dataset[i][1]
                temp += [data[i] for i in data.keys()]
            for i in range(9, len(dataset)):
                data = dataset[i]
                label = LABELS[data[0]]
                temp += [data[1][i] for i in data[1].keys()]
                res.append((np.array(label), np.array(temp)))
                temp = temp[4:]
    with open('data.pkl', 'wb') as f:
        pickle.dump(res, f)

def view_data(path='data.pkl'):
    with open(path, 'rb') as f:
        dataset = pickle.load(f)
    for i in range(10):
        print(dataset[i])

if __name__ == '__main__':
    view_data('data_relax.pkl')