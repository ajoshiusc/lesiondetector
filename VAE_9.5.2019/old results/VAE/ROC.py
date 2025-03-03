from __future__ import print_function
import argparse
import torch
import torch.utils.data
from torch import nn, optim
from torch.autograd import Variable
from torch.nn import functional as F
from torchvision import datasets, transforms
from torchvision.utils import save_image
import json
import numpy as np
import math
import datetime
import os
from keras.datasets import mnist
from torchsummary import summary
import matplotlib.pyplot as plt
from sklearn import metrics
import scipy.signal

import VAE_models_functional
from sklearn.model_selection import train_test_split
seed = 10009
epochs = 250
batch_size = 8
log_interval = 10
beta=0.00035
sigma = 1
z = 32

parser = argparse.ArgumentParser(description='VAE MNIST Example')
parser.add_argument('--batch-size',
                    type=int,
                    default=128,
                    metavar='N',
                    help='input batch size for training (default: 128)')
parser.add_argument('--epochs',
                    type=int,
                    default=10,
                    metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--no-cuda',
                    action='store_true',
                    default=False,
                    help='enables CUDA training')
parser.add_argument('--seed',
                    type=int,
                    default=1,
                    metavar='S',
                    help='random seed (import matplotlib.pyplot as pltult: 1)')
parser.add_argument(
    '--log-interval',
    type=int,
    default=10,
    metavar='N',
    help='how many batches to wait before logging training status')

args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)

device = torch.device("cuda" if args.cuda else "cpu")

torch.manual_seed(seed)


kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}

#print(y_test[1:10])
d = np.load(
   '/big_disk/akrami/Projects/lesion_detector_data/VAE_GAN/data_24_ISEL.npz')
X = d['data']
X=X[0:(15*20), :, :,:]
X_data = X[:, :, :, 0:3]


max_val = np.max(X_data)
#max_val = np.max(max_val, 1)
#max_val = np.reshape(max_val, (-1, 1, 1, 3))
X_data = X_data / max_val
X_data = X_data.astype('float64')
X_data=np.clip(X_data,0,1)
D = X_data.shape[1] * X_data.shape[2]
X_valid = np.transpose(X_data, (0, 3, 1, 2))

validation_data = torch.from_numpy(X_valid).float()
validation_data = validation_data.to(
    'cuda') if args.cuda else validation_data.to('cpu')

Validation_loader = torch.utils.data.DataLoader(validation_data,
                                                batch_size=batch_size,
                                                shuffle=False)
model = VAE_models_functional.VAE_nf(z)
model.load_state_dict(torch.load(
    '/big_disk/akrami/git_repos_new/lesion-detector/VAE_9.5.2019/VAE/results/model_skip_%f_%f_%f.pt'
    % (z, beta,sigma)),
                      strict=False)
model.have_cuda = args.cuda

if args.cuda:
    model.cuda()

print(model)
summary(model, (3, 128, 128))
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)


# Reconstruction + KL divergence losses summed over all elements and batch
def MSE_loss(Y, X):
    ret = (X - Y)**2
    ret = torch.sum(ret, 1)
    return ret


def BMSE_loss(Y, X, beta, sigma, D):
    term1 = -((1 + beta) / beta)
    K1 = 1 / pow((2 * math.pi * (sigma**2)), (beta * D / 2))
    term2 = MSE_loss(Y, X)
    term3 = torch.exp(-(beta / (2 * (sigma**2))) * term2)
    loss1 = torch.sum(term1 * (K1 * term3 - 1))
    return loss1


# Reconstruction + KL divergence losses summed over all elements and batch
def beta_loss_function(recon_x, x, mu, logvar, beta):

    if beta > 0:
        # If beta is nonzero, use the beta entropy
        BBCE = BMSE_loss(recon_x.view(-1, 128 * 128 * 3),
                         x.view(-1, 128 * 128 * 3), beta, sigma, D)
    else:
        # if beta is zero use binary cross entropy
        BBCE = torch.sum(
            MSE_loss(recon_x.view(-1, 128 * 128 * 3),
                     x.view(-1, 128 * 128 * 3)))

    # compute KL divergence
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())

    return BBCE + KLD


def Validation(X):
    model.eval()
    test_loss = 0
    ind = 0
    with torch.no_grad():
        for i, data in enumerate(Validation_loader):
            #        data = (data.gt(0.5).type(torch.FloatTensor)).to(device)
            data = (data).to(device)
            seg = X[ind:ind + batch_size, :, :, 3]
            ind = ind + batch_size
            seg = torch.from_numpy(seg)
            seg = (seg).to(device)
            recon_batch, mu, logvar = model(data)
            #print(mu.shape)
            test_loss += beta_loss_function(recon_batch, data, mu, logvar,
                                            beta).item()
            f_data = data[:, 2, :, :]
            f_recon_batch = recon_batch[:, 2, :, :]
            rec_error = f_data - f_recon_batch
            if i<100:
                n = min(f_data.size(0), 100)
                err=(f_data.view(batch_size, 1, 128, 128)[:n] -
                     f_recon_batch.view(batch_size, 1, 128, 128)[:n])
                median=(err).to('cpu')
                median=median.numpy()
                median=scipy.signal.medfilt(median,(1,1,7,7))
                median=median.astype('float32')
                median = np.clip(median, 0, 1)
                scale_error=np.max(median,axis=2)
                scale_error=np.max(scale_error,axis=2)
                scale_error=np.reshape(scale_error,(-1,1,1,1))
                err=median/scale_error
                err=torch.from_numpy(err)
                err=(err).to(device)

                comparison = torch.cat([
                    f_data.view(batch_size, 1, 128, 128)[:n],
                    f_recon_batch.view(batch_size, 1, 128, 128)[:n],
                    err,
                    torch.abs(
                        f_data.view(batch_size, 1, 128, 128)[:n] -
                        f_recon_batch.view(batch_size, 1, 128, 128)[:n]),
                    seg.view(batch_size, 1, 128, 128)[:n]
                ])
                save_image(comparison.cpu(),
                           'results/reconstruction_b' +str(i)+ '.png',
                           nrow=n)
                
            if i==0:
                mu_all = mu
                logvar_all = logvar
                rec_error_all = rec_error
            else:
                mu_all = torch.cat([mu_all, mu])
                logvar_all = torch.cat([logvar_all, logvar])
                rec_error_all = torch.cat([rec_error_all, rec_error])
    test_loss /= len(Validation_loader.dataset)
    print('====> Test set loss: {:.4f}'.format(test_loss))
    return logvar_all, mu_all, test_loss, rec_error_all


if __name__ == "__main__":
    logvar_all, mu_all, validation_loss, rec_error_all = Validation(X)
    y_true = X[0:(15*20), :, :, 3]
    y_true = np.reshape(y_true, (-1, 1))
    #y_probas = rec_error_all.veiw(-1,1)
    y_probas = (rec_error_all).to('cpu')
    y_probas = y_probas.numpy()
    y_probas = np.reshape(y_probas, (-1, 1))
    y_true = y_true.astype(int)
    #y_true = y_true[:10000, 0]
  #  y_probas = y_probas[:10000, 0]
    print(np.min(y_probas))
    print(np.max(y_probas))
    y_probas = np.clip(y_probas, 0, 1)
    #y_true=y_true[y_probas >=0]
    #y_probas=y_probas[y_probas >= 0]
    
    y_probas = np.reshape(y_probas, (-1, 1,128,128))
    y_probas=scipy.signal.medfilt(y_probas,(1,1,7,7))
    y_probas = np.reshape(y_probas, (-1, 1))
    #y_probas=abs(y_probas)
    #print(np.min(y_probas))
    #print(np.max(y_probas))
    #y_probas=y_probas/np.max(y_probas)
    #print(np.max(y_probas))
    #print(sum(np.isnan(y_true)))
    #metrics.plot_roc_curve(y_true, y_probas)
    #plt.show()
    fpr, tpr, th= metrics.roc_curve(y_true, y_probas)
    L=fpr/tpr
    best_th=th[tpr>=0.5]
    auc = metrics.auc(fpr, tpr)
    plt.plot(fpr, tpr, label="data 1, auc=" + str(auc))
    plt.legend(loc=4)
    plt.show()
    
    #np.savez('/big_disk/akrami/git_repos/lesion-detector/src/VAE/y_probas_VAE_notcons.npz', data=y_probas)
    #np.savez('/big_disk/akrami/git_repos/lesion-detector/src/VAE/y_true_VAE.npz', data=y_true)
    y_probas[y_probas >=0.1]=1
    y_probas[y_probas <0.1]=0

    y_probas = np.reshape(y_probas, (-1,128*128*20))
    y_true = np.reshape(y_true, (-1,128*128*20))
    
    dice=0
    for i in range(y_probas.shape[0]):
        seg=y_probas[i,:]
        gth=y_true[i,:]
        dice += np.sum(seg[gth==1])*2.0 / (np.sum(gth) + np.sum(seg))
        #print((dice))
    print((dice)/y_probas.shape[0])

