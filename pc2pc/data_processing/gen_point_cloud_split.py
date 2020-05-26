import os, sys
import numpy as np
import pickle

point_cloud_dir = '../data/ShapeNet_v1_point_cloud/02933112/point_cloud_clean_full'

all_ply_filenames = [f for f in os.listdir(point_cloud_dir)]
print('Total: %d'%(len(all_ply_filenames)))

train_portion = 0.85
val_portion = 0.05
test_portion = 0.10

train_ply_filenames = []
val_ply_filenames = []
trainval_ply_filenames = []
test_ply_filenames = []
for pf in all_ply_filenames:
    odd = np.random.rand()
    if odd <= train_portion: # train
        train_ply_filenames.append(pf)
        trainval_ply_filenames.append(pf)
    elif odd > train_portion and odd < (train_portion+val_portion):
        val_ply_filenames.append(pf)
        trainval_ply_filenames.append(pf)
    else:
        test_ply_filenames.append(pf)

print('#trains: %d'%(len(train_ply_filenames)))
print('#vals: %d'%(len(val_ply_filenames)))
print('#trainvals: %d'%(len(trainval_ply_filenames)))
print('#tests: %d'%(len(test_ply_filenames)))

base_dir = os.path.dirname(point_cloud_dir)
base_name = os.path.basename(point_cloud_dir)
with open(os.path.join(base_dir, base_name+'_train_split.pickle'), 'wb') as pf:
    pickle.dump(train_ply_filenames, pf)

with open(os.path.join(base_dir, base_name+'_val_split.pickle'), 'wb') as pf:
    pickle.dump(val_ply_filenames, pf)

with open(os.path.join(base_dir, base_name+'_trainval_split.pickle'), 'wb') as pf:
    pickle.dump(trainval_ply_filenames, pf)

with open(os.path.join(base_dir, base_name+'_test_split.pickle'), 'wb') as pf:
    pickle.dump(test_ply_filenames, pf)

with open(os.path.join(base_dir, base_name+'_all_split.pickle'), 'wb') as pf:
    pickle.dump(all_ply_filenames, pf)

