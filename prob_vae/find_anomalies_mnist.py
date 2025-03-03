from __future__ import print_function
import argparse
import torch
import torch.utils.data
from torch import nn, optim
from torch.nn import functional as F
from torchvision import datasets, transforms
from torchvision.utils import save_image
from keras.datasets import mnist
import numpy as np
from tqdm import tqdm
from torch.autograd import Variable
import scipy.stats
from vaemodel import VAE
from utils import make_lesion
from statsmodels.stats.multitest import multipletests

parser = argparse.ArgumentParser(description='VAE MNIST Example')
parser.add_argument('--batch-size',
                    type=int,
                    default=128,
                    metavar='N',
                    help='input batch size for training (default: 128)')
parser.add_argument('--epochs',
                    type=int,
                    default=50,
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
                    help='random seed (default: 1)')
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

kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}

(_, _), (x_test, _) = mnist.load_data()

x_test = x_test / 255
x_test = x_test.astype(float)

in_data = x_test
in_data = torch.tensor(in_data).float().view(in_data.shape[0], 1, 28, 28)

#x_train = torch.from_numpy(x_train).float().view(x_train.shape[0],1,28,28)
#x_test = torch.from_numpy(x_test).float().view(x_test.shape[0],1,28,28)

model_mean = VAE().to(device)
model_std = VAE().to(device)

model_mean.load_state_dict(torch.load('results/VAE_mean.pth'))
model_std.load_state_dict(torch.load('results/VAE_std.pth'))

out_mean = torch.zeros(in_data.shape)
out_std = torch.zeros(in_data.shape)

model_mean.eval()
model_std.eval()

with torch.no_grad():

    for i, data in enumerate(tqdm(in_data)):
        # add artificial lesion
        data[0, :, :] = data[0, :, :] + \
            torch.tensor(make_lesion(data[0, :, :]))
        data = data[None, ].to(device)
        rec, mean, logvar = model_mean(data)
        out_mean[i, ] = rec.view(1, 28, 28).cpu()
        rec, mean, logvar = model_std(data)
        out_std[i, ] = rec.view(1, 28, 28).cpu() / 2
        # division by 2 to compensate for multiplication ny 2 in the std dev autoencoder code

np.savez('results/rec_mean_std.npz',
         out_mean=out_mean,
         out_std=out_std,
         in_data=in_data)

z_score = (in_data - out_mean) / out_std

p_value = torch.tensor(scipy.stats.norm.sf(z_score)).float()

p_value_orig = p_value.clone()

for ns in tqdm(range(p_value.shape[0])):
    fdrres = multipletests(p_value[ns, 0, :, :].flatten(),
                           alpha=0.05,
                           method='fdr_bh',
                           is_sorted=False,
                           returnsorted=False)
    p_value[ns, 0, :, :] = torch.tensor(fdrres[1]).reshape((28, 28))

msk = ((in_data.clone().detach() > .01) |
       (out_mean.clone().detach() > .01)).float()
#p_value = p_value*msk + (1 - msk)

n = 8

pv = p_value[:n].clone().detach()

sig_msk = (pv < 0.05).clone().detach().float()
comparison = torch.cat([
    in_data[:n], out_mean[:n],
    abs(in_data[:n] - out_mean[:n]), out_std[:n], z_score[:n] / 3.0,
    1 - p_value_orig[:n], sig_msk
])

save_image(comparison,
           'results/recon_mean_std.png',
           nrow=n,
           scale_each=False,
           normalize=True,
           range=(0, 1))

input("Press Enter to continue...")
