import pickle
import numpy as np
import plots.grid
import matplotlib
import matplotlib.pyplot as plt
from q_learning.q_learning import ActionValueFunction, MarkovQState
from value_iteration.value_iteration import ValueFunction, MarkovState
from cycler import cycler
from util.runs import epoch

model_path = '../files/models/'
plots_path = '../files/models/'

# ============================= SETTINGS
# plt.rc('text', usetex=True)
# plt.rc('font', family='serif')
matplotlib.rcParams.update({'font.size': 8})
# plt.rc('axes', prop_cycle=(cycler('color', ['#1f77b4', '#d62728'])))


def optimal_paths_grids(file_name):
    world, Q = pickle.load(open(model_path+file_name, 'rb'))
    alphas = [0.1, 0.25, 0.5, 1.]
    fig, axs = plt.subplots(2, 2, figsize=(8.5, 5))

    for ax, alpha in zip(axs.flatten(), alphas):
        img = np.max(np.array([Q.Q[ix].yc_alpha(alpha)/alpha for ix in np.ndindex(Q.Q.shape)]).reshape(Q.Q.shape), axis=-1)
        plots.grid.grid_plot(world, img=img, figax=(fig, ax), sg_size=10)

        path = Q.optimal_path(alpha)
        print(path)
        ax.plot([s[1] for s in path], [s[0] for s in path], '--', color='white')

        ax.set_title("$\\alpha={}$".format(alpha))
        ax.axis('off')

    plt.savefig(plots_path+'q_optimal_paths.pdf', bbox_inches='tight')
    plt.show()


# ============================= RUNS -> stats
def generate_samples(world, policy, nb_episodes=1000):
    scores = []
    for i in range(nb_episodes):
        S, A, R = epoch(world, policy)
        policy.reset()
        scores.append(np.sum(R))
        if i % 10 == 0:
            print('e:', i)
    return scores


def sample_histograms(alpha, suffix):
    from util.cvar_computation import var_cvar_from_samples
    from policy_improvement.policies import GreedyPolicy, VarBasedQPolicy, XiBasedPolicy

    # exp VI
    world, Q = pickle.load(open(model_path+'exp_'+suffix+'.pkl', 'rb'))
    scores_exp = generate_samples(world, GreedyPolicy(Q))
    v_exp, c_exp = var_cvar_from_samples(scores_exp, alpha)
    print('CVaR_{}(exp)={}'.format(alpha, c_exp))

    # CVaR VI
    # world, Q = pickle.load(open('../files/models/vi_10_15.pkl', 'rb'))
    # scores_vi = generate_samples(world, XiBasedPolicy(Q, alpha))

    # Q-learned
    world, Q = pickle.load(open('../files/models/q_'+suffix+'.pkl', 'rb'))
    scores_q = generate_samples(world, VarBasedQPolicy(Q, alpha))
    v_q, c_q = var_cvar_from_samples(scores_q, alpha)
    print('CVaR_{}(q)={}'.format(alpha, c_q))


    plt.hist(scores_exp, density=True, bins=20, edgecolor='black')
    plt.hist(scores_q, density=True, bins=20, edgecolor='black')
    plt.legend(['exp', 'q'])

    plt.savefig(plots_path + 'sample_hist.pdf', bbox_inches='tight')
    # plt.show()


if __name__ == '__main__':

    sample_histograms(0.05, suffix='10_15')



