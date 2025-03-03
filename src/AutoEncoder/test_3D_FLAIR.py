from read_test_data import read_test_data
from slice2vol_pred import slice2vol_pred
from keras.models import load_model
import numpy as np
from tqdm import tqdm
import nilearn.image as ni
import os
from deep_auto_encoder2 import square_loss
from deep_auto_encoder2 import corrent_loss
from deep_auto_encoder2 import TV_reconstructed_loss
from deep_auto_encoder2 import FLAIR_loss
import math

alpha=0

study_dir = '/big_disk/ajoshi/ISLES2015/preproc/Training/'
#study_dir ='/big_disk/ajoshi/fitbir/preproc/maryland_rao_v1/'
with open('/big_disk/ajoshi/ISLES2015/ISLES2015_Training_done.txt') as f:
    tbidoneIds = f.readlines()
tbidoneIds = [l.strip('\n\r') for l in tbidoneIds]
subid=tbidoneIds[0]
#subid=tbidoneIds[30]
t1file = os.path.join(study_dir, subid, 'T1mni.nii.gz')
t1model=ni.load_img(t1file )
test_image=read_test_data(study_dir, subid)
im_size=64
#model=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_L12_50_50_MSE_0.1_bactchnorm.h5',custom_objects={'TV_R': TV_reconstructed_loss(alpha)})
#model=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_L12_50_50_MSE_0.01_bactchnorm.h5',custom_objects={'MSE_FLAIR': FLAIR_loss(alpha)})
#model=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_L12_20iter_lamb1_alpha0.5.h5',custom_objects={'TV_R': TV_reconstructed_loss(alpha)})
#model=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_SV_bactchnorm.h5',custom_objects={'SV': square_loss(alpha)})
#model=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_RAE_0.3.h5',custom_objects={'RAE': corrent_loss(alpha)})
#odel=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_L12_50_2_MSE_0_re.h5')
model=load_model('/big_disk/akrami/git_repos/lesion-detector/src/AutoEncoder/models/tp_model_200_512_merryland_30_L12_50_2_MSE_10000_re.h5')
vol_data=np.copy(test_image)
out_vol = np.zeros((vol_data.shape[0],vol_data.shape[1],vol_data.shape[2],1)) # output volume
indf = np.zeros((vol_data.shape[0],vol_data.shape[1],vol_data.shape[2],1))
vol_size = vol_data.shape
step_size=8
for j in tqdm(range(0, vol_size[0] - im_size, step_size)):
    for k in range(0, vol_size[1] - im_size, step_size):
        temp=model.predict([np.transpose(vol_data[j:im_size + j,k:im_size + k,:,:],(2,0,1,3))])
        out_vol[j:im_size + j,k:im_size +
                k,:,:] += np.transpose(temp,(1,2,0,3))
        indf[j:im_size + j,k:im_size + k ,:,:] += 1
out_vol = out_vol / (indf + 1e-12)  #[...,None]

MSE_image=((vol_data[:,:,:,2]-out_vol[:,:,:,0])**2)
#MSE_image=MSE_image.mean(axis=0)
img = ni.new_img_like(t1model, MSE_image)
img.to_filename('/big_disk/akrami/MSE_ISLES2015_1_MSE_R10000.nii.gz')


img = ni.new_img_like(t1model, out_vol[:,:,:,0])
img.to_filename('/big_disk/akrami/outFLAIR_ISLES2015_1_MSE_R10000.nii.gz')



img = ni.new_img_like(t1model, vol_data[:,:,:,2]-out_vol[:,:,:,0])
img.to_filename('/big_disk/akrami/difFLAIR_ISLES2015_1_MSE_R10000.nii.gz')




#test_re =slice2vol_pred(model, test_image, im_size,8)
