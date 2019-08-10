
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/04_callbacks_jcat.ipynb

from exp.nb_03 import *

class DataBunch():
    def __init__(self, train_dl, valid_dl, batch_size=None):
        self.train_dl,self.valid_dl,self.batch_size = train_dl,valid_dl,batch_size

    # add train_ds() as an attribute
    @property
    def train_ds(self): return self.train_dl.dataset


    # add valid_ds() as an attribute
    @property
    def valid_ds(self): return self.valid_dl.dataset


# get_model() instantiates the model and the optimizer
def get_model(data, learning_rate = 0.5, n_hidden = 50):
    n_columns = data.train_ds.x.shape[1]
    model = nn.Sequential(nn.Linear(n_columns,n_hidden), nn.ReLU(), nn.Linear(n_hidden,data.batch_size))
    return model, optim.SGD(model.parameters(), lr=learning_rate)

# the Learner() class is a container for the model, optimization, loss function and data
class Learner():
    def __init__(self, model, opt, loss_func, data):
        self.model,self.opt,self.loss_func,self.data = model,opt,loss_func,data

import re

# use regular expressions to construct a 'snake case' callback name for each 'camel case' callback name
_camel_re1 = re.compile('(.)([A-Z][a-z]+)')
_camel_re2 = re.compile('([a-z0-9])([A-Z])')
def camel2snake(name):
    s1 = re.sub(_camel_re1, r'\1_\2', name)
    return re.sub(_camel_re2, r'\1_\2', s1).lower()

# create a Callback() class
class Callback():
    # initialize _order to zero
    _order=0
    def set_runner(self, run):
        self.run=run
    def __getattr__(self, callback_name):
        return getattr(self.run, callback_name)
    @property
    def name(self):
        name = re.sub(r'Callback$', '', self.__class__.__name__)
        # if name does not exist, set the name to 'callback'
        return camel2snake(name or 'callback')

class TrainEvalCallback(Callback):

    # initialize the epoch and interation counters
    def begin_fit(self):
        self.run.n_epochs=0.
        self.run.n_iter=0

    # if we are in the training phase, increment the epoch and iteration counters
    def after_batch(self):
        if not self.in_train:
            return
        # each training iteration represents a fraction of an epoch
        self.run.frac_epoch += 1./self.n_iters
        self.run.n_iter   += 1

    # execute the training phase
    def begin_epoch(self):
        self.run.n_epochs=self.n_epochs
        self.model.train()
        self.run.in_train=True

    # execute prediction phase
    def begin_validate(self):
        self.model.eval()
        self.run.in_train=False

from typing import *

# function to convert any input into a list
def listify(o):
    if o is None: return []
    if isinstance(o, list): return o
    if isinstance(o, str): return [o]
    if isinstance(o, Iterable): return list(o)
    return [o]

class Runner():
    def __init__(self, callbacks=None, callback_funcs=None):
        # create a list of callbacks from the input callbacks
        callbacks = listify(callbacks)
        # append to the callbacks list from the input list of callback_funcs
        for callback_func in listify(callback_funcs):
            callback = callback_func()
            setattr(self, callback.name, callback)
            callbacks.append(callback)
        # set the stopping flag to `False` and append TrainEvalCallback() to the callbacks list
        self.stop,self.callbacks = False,[TrainEvalCallback()]+callbacks

    @property
    def opt(self):       return self.learn.opt
    @property
    def model(self):     return self.learn.model
    @property
    def loss_func(self): return self.learn.loss_func
    @property
    def data(self):      return self.learn.data

    def one_batch(self, xb, yb):
        self.xb,self.yb = xb,yb
        if self('begin_batch'):
            return
        # run the model
        self.pred = self.model(self.xb)
        # ????? no `after_pred` callback has been defined ?????
        if self('after_pred'):
            return
        # compute the loss function
        self.loss = self.loss_func(self.pred, self.yb)
        # should `self('after_loss')` be `not self('after_loss')`, for consistency with previous version?
        if self('after_loss') or not self.in_train:
            return
        # do backpropagation
        self.loss.backward()
        if self('after_backward'):
            return
        # update parameters
        self.opt.step()
        if self('after_step'):
            return
        # zero the gradients to prepare for the next batch
        self.opt.zero_grad()

    def all_batches(self, dataloader):
        self.n_iters = len(dataloader)
        self.frac_epoch = 0.
        for xb,yb in dataloader:
            # break if stopping flag has been set
            if self.stop:
                break
            # process the next batch and set the `after_batch` flag
            self.one_batch(xb, yb)
            self('after_batch')
        # set the stopping flag to `False`
        self.stop=False

    def fit(self, learn, n_epochs):
        self.n_epochs,self.learn = n_epochs,learn

        try:
            for callback in self.callbacks:
                callback.set_runner(self)
            if self('begin_fit'):
                return
            for epoch in range(n_epochs):
                self.epoch = epoch

                # training phase
                if not self('begin_epoch'):
                    self.all_batches(self.data.train_dl)

                # validation phase
                with torch.no_grad():
                    if not self('begin_validate'):
                        self.all_batches(self.data.valid_dl)
                # break if `after_epoch` state is `True`
                if self('after_epoch'):
                    break

        finally:
            # set the `after_fit` state to `True`
            self('after_fit')
            # erase the learner object
            self.learn = None

    def __call__(self, callback_name):
        for callback in sorted(self.callbacks, key=lambda x: x._order):
            # getattr returns the callback name
            f = getattr(callback, callback_name, None)
            # return `True` if this callback has a name, otherwise return `False`
            if f and f():
                return True
        return False

class AvgStats():
    def __init__(self, metrics, in_train):
        self.metrics,self.in_train = listify(metrics),in_train

    # initialize total_loss, count, and total_metrics
    def reset(self):
        self.total_loss,self.count = 0.,0
        self.total_metrics = [0.] * len(self.metrics)

    # combine loss and metrics
    @property
    def all_stats(self):
        return [self.total_loss.item()] + self.total_metrics

    # compute avg loss and metrics
    @property
    def avg_stats(self):
        return [o/self.count for o in self.all_stats]

    # compute and display stats
    def __repr__(self):
        if not self.count:
            return ""
        return f"{'train' if self.in_train else 'valid'}: {self.avg_stats}"

    def accumulate(self, run):
        # get the number of samples in this batch
        n_samples_in_batch = run.xb.shape[0]
        # weight the loss function for the batch by the number of samples in the batch
        self.total_loss += run.loss * n_samples_in_batch
        # accumulate count of samples processed
        self.count += n_samples_in_batch
        # accumulate the metrics
        for i,metric in enumerate(self.metrics):
            self.total_metrics[i] += metric(run.pred, run.yb) * n_samples_in_batch

class AvgStatsCallback(Callback):
    def __init__(self, metrics):
        self.train_stats,self.valid_stats = AvgStats(metrics,in_train=True),AvgStats(metrics,in_train=False)

    # initialize train_stats and valid_stats
    def begin_epoch(self):
        self.train_stats.reset()
        self.valid_stats.reset()
    # compute and accumulate stats
    def after_loss(self):
        stats = self.train_stats if self.in_train else self.valid_stats
        with torch.no_grad():
            stats.accumulate(self.run)
    # print stats
    def after_epoch(self):
        print(self.train_stats)
        print(self.valid_stats)

from functools import partial