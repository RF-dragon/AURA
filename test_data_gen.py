import pickle
import random

LABELS = ('AWAY', 'RELAX', 'SLEEP', 'STUDY')

res = []
for i in range(100):
    data = (LABELS[random.randint(0, 3)], {})
    for j in range(6):
        data[1][f'test{j}'] = random.random()
    res.append(data)
with open('data.pkl', 'wb') as f:
    pickle.dump(res, f)