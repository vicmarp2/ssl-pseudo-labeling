#%%
import sys
import argparse
import math
import random
from dataloader import get_cifar10, get_cifar100
from test import test_cifar10
from utils import accuracy, plot, plot_model

from model.wrn import WideResNet
from train import train

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
#%%

# dataloader.py:121: UserWarning UserWarning: To copy construct from a tensor, it is recommended to use sourceTensor.clone().detach()
# or sourceTensor.clone().detach().requires_grad_(True), rather than torch.tensor(sourceTensor).
import warnings
warnings.filterwarnings("ignore")


def save_checkpoint(state, filename='checkpoint.pth.tar'):
    torch.save(state, filename)


def main(args):
    # protect iterations/epoch parameters from erroneous input values
    if args.t2 > args.total_iter:
        print("argument t2 should be larger than total_iter")
        sys.exit()
    if args.t1 > args.t2:
        print("parameter t1 should be smaller or equal than t2")
        sys.exit()
    if args.total_iter % args.iter_per_epoch != 0:
        print("total_iter should be multiple of iter_per_epoch")
        sys.exit()
    if args.t1 % args.iter_per_epoch != 0:
        print("parameter t1 should be multiple of iter_per_epoch")
        sys.exit()
    if args.t2 % args.iter_per_epoch != 0:
        print("parameter t2 should be multiple of iter_per_epoch")
        sys.exit()

    # load data
    if args.dataset == "cifar10":
        args.num_classes = 10
        labeled_dataset, unlabeled_dataset, test_dataset = get_cifar10(args,
                                                                       args.datapath)
    if args.dataset == "cifar100":
        args.num_classes = 100
        labeled_dataset, unlabeled_dataset, test_dataset = get_cifar100(args,
                                                                        args.datapath)
    # TODO decide how to split validation set
    validation_dataset = Subset(unlabeled_dataset, random.sample(range(0, len(labeled_dataset)), args.num_validation))
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    labeled_loader = iter(DataLoader(labeled_dataset,
                                     batch_size=args.train_batch,
                                     shuffle=True,
                                     num_workers=args.num_workers))
    unlabeled_loader = iter(DataLoader(unlabeled_dataset,
                                       batch_size=args.train_batch,
                                       shuffle=True,
                                       num_workers=args.num_workers))
    
    validation_loader = DataLoader(validation_dataset,
                             batch_size=args.train_batch,
                             shuffle=True,
                             num_workers=args.num_workers)
    
    test_loader = DataLoader(test_dataset,
                             batch_size=args.test_batch,
                             shuffle=False,
                             num_workers=args.num_workers)

    # TODO add validation dataloader
    datasets = {
        'labeled': labeled_dataset,
        'unlabeled': unlabeled_dataset,
        'validation': validation_dataset,
        'test': test_dataset,
    }
    dataloaders = {
        'labeled': labeled_loader,
        'unlabeled': unlabeled_loader,
        'validation': validation_loader,
        'test': test_loader
    }

    # create inner arguments
    args.epoch = math.ceil(args.total_iter / args.iter_per_epoch)
    # TODO should we use arguments or fix it for a certain percentaje of the epochs given?
    # TODO check t2 <= epoch
    args.epoch_t1 = math.ceil(args.t1 / args.iter_per_epoch)
    args.epoch_t2 = math.ceil(args.t2 / args.iter_per_epoch)

    # create model
    model = WideResNet(args.model_depth,
                       args.num_classes, widen_factor=args.model_width, dropRate=args.drop_rate)
    model = model.to(device)

    # TODO add scheduler for momentum
    optimizer = torch.optim.SGD(
        model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.wd)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.998)
    criterion = nn.CrossEntropyLoss()


    # train model
    #best_model = train(model, datasets, dataloaders, args.modelpath, criterion, optimizer, scheduler, True, True, args)

    # test
    # test_cifar10(test_dataset, './model/best_model.pt')
    
    # %%
    # plot training loss
    plot_model('./model/last_model.pt', 'training_losses', 'Training Loss')
    # %%
    # plot training loss
    plot_model('./model/last_model.pt', 'test_losses', 'Test Loss', color='r')
    # %%

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description="Pseudo labeling \
                                        of CIFAR10/100 with pytorch")
    parser.add_argument("--dataset", default="cifar10",
                        type=str, choices=["cifar10", "cifar100"])
    parser.add_argument("--datapath", default="./data/",
                        type=str, help="Path to the CIFAR-10/100 dataset")
    parser.add_argument('--num-labeled', type=int,
                        default=4000, help='Total number of labeled samples')
    parser.add_argument("--lr", default=0.03, type=float,
                        help="The initial learning rate")
    parser.add_argument("--momentum", default=0.9, type=float,
                        help="Optimizer momentum")
    parser.add_argument("--wd", default=0.00005, type=float,
                        help="Weight decay")
    parser.add_argument("--expand-labels", action="store_true",
                        help="expand labels to fit eval steps")
    parser.add_argument('--train-batch', default=64, type=int,
                        help='train batchsize')
    parser.add_argument('--test-batch', default=64, type=int,
                        help='test batchsize')
    parser.add_argument('--total-iter', default=16*3, type=int,
                        help='total number of iterations to run')
    parser.add_argument('--iter-per-epoch', default=16, type=int,
                        help="Number of iterations to run per epoch")
    parser.add_argument('--num-workers', default=1, type=int,
                        help="Number of workers to launch during training")
    parser.add_argument('--threshold', type=float, default=0.95,
                        help='Confidence Threshold for pseudo labeling')
    parser.add_argument("--dataout", type=str, default="./path/to/output/",
                        help="Path to save log files")
    parser.add_argument("--model-depth", type=int, default=28,
                        help="model depth for wide resnet")
    parser.add_argument("--model-width", type=int, default=2,
                        help="model width for wide resnet")
    parser.add_argument("--alpha", type=int, default=3,
                        help="alpha regulariser for the loss")
    parser.add_argument("--t1", type=int, default=16*1,
                        help="first stage of iterations for calculating the alpha regulariser")
    parser.add_argument("--t2", type=int, default=16*2,
                        help="second stage of iterations for calculating the alpha regulariser")
    parser.add_argument("--drop-rate", type=int, default=0.3,
                        help="drop out rate for wrn")
    parser.add_argument('--num-validation', type=int,
                        default=1000, help='Total number of validation samples')
    parser.add_argument("--modelpath", default="./model/",
                        type=str, help="Path to the persisted models")
    args = parser.parse_args()

    # train
    main(args)