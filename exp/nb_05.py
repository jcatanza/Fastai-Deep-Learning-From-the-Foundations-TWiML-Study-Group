
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/05_anneal_jcat.ipynb

from exp.nb_04 import *

def create_learner(model_func, loss_func, data):
    return Learner(*model_func(data), loss_func, data)

def get_model_func(learning_rate=0.5):
    return partial(get_model, learning_rate=learning_rate)

def annealer(f):
    def _inner(start, end):
        return partial(f, start, end)
    return _inner

@annealer
def sched_lin(start, end, pos):
    return start + pos*(end-start)

@annealer
# cosine schedule
def sched_cos(start, end, pos):
    return start + (1 + math.cos(math.pi*(1-pos))) * (end-start) / 2
# constant schedule
@annealer
def sched_no(start, end, pos):
    return start
# exponential schedule
@annealer
def sched_exp(start, end, pos):
    return start * (end/start) ** pos

#Add an ndim property to the Tensor class so that tensors can be plotted
torch.Tensor.ndim = property(lambda x: len(x.shape))

def combine_scheds(fracs, scheds):

    # check that all fracs are positive and that they sum to 1
    assert sum(fracs) == 1.
    fracs = tensor([0] + listify(fracs))
    assert torch.all(fracs >= 0)

    # relative position (between 0 and 1) at the boundary of each piecewise section of the schedule
    cum_fracs = torch.cumsum(fracs, 0)

    def _inner(pos):
        # given a relative position pos (between 0 and 1) along the schedule interval
        #    if pos doesn't correspond to a section boundary point,
        #        compute the index of the nearest section boundary point to its left in cum_fracs;
        #    otherwise return the index corresponding to pos in cum_fracs
        idx = (pos >= cum_fracs).nonzero().max()
        # print('index = ',idx)
        # compute the relative position of pos within its piecewise section interval; ranges from 0 to 1
        actual_pos = (pos-cum_fracs[idx]) / (cum_fracs[idx+1]-cum_fracs[idx])
        return scheds[idx](actual_pos)
    # return the scheduler function
    return _inner

class Recorder(Callback):
    def begin_fit(self):
        self.lrs,self.losses = [],[]

    def after_batch(self):
        if not self.in_train: return
        self.lrs.append(self.opt.param_groups[-1]['learning_rate'])
        self.losses.append(self.loss.detach().cpu())

    def plot_lr  (self):
        plt.plot(self.lrs)
    def plot_loss(self):
        plt.plot(self.losses)

class ParamScheduler(Callback):
    # ????? what is the function of the _order parameter ?????
    _order=1
    def __init__(self, pname, sched_func):
        self.pname,self.sched_func = pname,sched_func

    def set_param(self):
        for param_group in self.opt.param_groups:
            print(self.epoch, self.n_epochs_float)
            # param_group[self.pname] = self.sched_func((self.epoch+self.n_epochs_float)/(self.epoch+1))
            param_group[self.pname] = self.sched_func((self.n_epochs_float+sel.epoch)/self.n_epochs)

    def begin_batch(self):
        if self.in_train:
            self.set_param()