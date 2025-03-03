# coding: utf-8

# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ajoshiusc/lesion-detector/blob/master/main_anatomy_map.ipynb)

# In[1]:
import nilearn.image
import sys
import numpy as np

import numpy as np
from spydernet import train_model, mod_indep_rep
from datautils import read_data
import matplotlib.pyplot as plt
from keras.models import load_model
import nilearn.image as ni
import nilearn.image
import sys
import numpy as np
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import pyplot as plt
from spydernet import train_model, mod_indep_rep_vol, mod_indep_rep_vol_stp
from spydernet import train_model, mod_indep_rep
#from tensorflow.python.client import device_lib
""" Main script that calls the functions objects"""
""" Main script that calls the functions objects"""
data_dir = '/big_disk/ajoshi/fitbir/preproc/tracktbi_pilot'
tbi_done_list = '/big_disk/ajoshi/fitbir/preproc/tracktbi_done.txt'
with open(tbi_done_list) as f:
    tbidoneIds = f.readlines()

# Get the list of subjects that are correctly registered
tbidoneIds = [l.strip('\n\r') for l in tbidoneIds]

data = read_data(
    study_dir=data_dir,
    subids=tbidoneIds,
    nsub=10,
    psize=[64, 64],
    npatch_perslice=16)

#np.savez('tp_data.npz', data=data)

#train_data = data  #[0:-5, :, :, :]

#model1 = train_model(train_data)

#model1.save('tp_model_softmax.h5')

model = load_model(
    '/big_disk/ajoshi/coding_ground/lesion-detector/src/SpyderNet/tp_model_softmax.h5'
)
t1 = ni.load_img(
    '/big_disk/ajoshi/fitbir/preproc/tracktbi_pilot/TBI_INVBB041DZW/T1.nii.gz'
).get_data()
t2 = ni.load_img(
    '/big_disk/ajoshi/fitbir/preproc/tracktbi_pilot/TBI_INVBB041DZW/T2.nii.gz'
).get_data()
flair = ni.load_img(
    '/big_disk/ajoshi/fitbir/preproc/tracktbi_pilot/TBI_INVBB041DZW/FLAIR.nii.gz'
).get_data()
t1o = ni.load_img(
    '/big_disk/ajoshi/fitbir/preproc/tracktbi_pilot/TBI_INVBB041DZW/T1.nii.gz')

p = np.percentile(np.ravel(t1), 95)  #normalize to 95 percentile
t1 = np.float32(t1) / p

p = np.percentile(np.ravel(t2), 95)  #normalize to 95 percentile
t2 = np.float32(t2) / p

p = np.percentile(np.ravel(flair), 95)  #normalize to 95 percentile
flair = np.float32(flair) / p
dat = np.stack((t1, t2, flair), axis=3)

print(dat.shape)
dat = np.float32(dat)
td = dat.copy()
I2 = mod_indep_rep_vol_stp(model, td, 128)

fig = plt.figure(figsize=(20, 20))
for j in range(5):
    plt.subplot(5, 5, j + 1)
    plt.imshow(I2[j + 100, :, :], cmap='gray')

    plt.subplot(5, 5, 5 + j + 1)
    plt.imshow(dat[j + 100, :, :, 0].squeeze(), cmap='gray')

    plt.subplot(5, 5, 10 + j + 1)
    plt.imshow(dat[j + 100, :, :, 1].squeeze(), cmap='gray')

    plt.subplot(5, 5, 15 + j + 1)
    plt.imshow(dat[j + 100, :, :, 2].squeeze(), cmap='gray')

plt.show()

print(I2.shape)

img = ni.new_img_like(t1o, I2)
img.to_filename('/big_disk/ajoshi/out.nii.gz')

# In[8]:
